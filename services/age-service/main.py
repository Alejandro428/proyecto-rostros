import cv2
import json
import logging
import numpy as np
import tensorflow as tf

from config import (
    DB_CONF, MINIO_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER,
    BUCKET_RAW, TOPIC_CONSUME, MODEL_PATH, IMG_SIZE_CV2, THRESHOLD
)
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model            = tf.keras.models.load_model(MODEL_PATH)
db_service       = DatabaseService(DB_CONF)
storage_service  = StorageService(MINIO_CONF, BUCKET_RAW)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

logger.info("--- [AGE SERVICE] INICIADO ---")

while True:
    msg = consumer_service.poll(1.0)
    if msg is None:
        continue

    if msg.error():
        logger.error(f"Kafka error: {msg.error()}")
        continue

    try:
        data = json.loads(msg.value().decode("utf-8"))

        guid      = data["GUID_Solicitud"]
        id_imagen = data["Id_Imagen"]
        s3_key    = data["s3_key"]
        faces     = data.get("faces", [])

        if not guid or not faces:
            logger.warning(f"Mensaje vacío o sin caras: {data}")
            continue

        processed_faces = []

        for face in faces:
            try:
                face_id     = face["face_id"]
                bbox        = face["bbox"]
                s3_key_cara = face["s3_key_cara"]

                # Descargar crop de la cara
                img = storage_service.download_image(s3_key_cara)

                # Preprocesado: mismo que entrenamiento — resize (ancho=320, alto=256) + /255
                img_resized  = cv2.resize(img, IMG_SIZE_CV2)
                img_norm     = img_resized.astype("float32") / 255.0
                img_input    = np.expand_dims(img_norm, axis=0)  # (1, 256, 320, 3)

                # Predicción — salida sigmoid: float en [0, 1]
                # Clases ordenadas alfabéticamente: 0=mayor, 1=menor → score >= 0.5 = MENOR
                score    = float(model.predict(img_input, verbose=0)[0][0])
                es_menor = score >= THRESHOLD

                logger.info(f"[AGE] face_id={face_id} → score={score:.4f} → {'MENOR' if es_menor else 'MAYOR'}")

                db_service.update_imagen_clasificacion(guid, face_id, not es_menor, score)

                processed_faces.append({
                    "face_id":  face_id,
                    "bbox":     bbox,
                    "es_menor": es_menor,
                    "score":    round(score, 4)
                })

            except Exception as e:
                logger.error(f"[ERROR face_id={face.get('face_id')}] {e}")

        db_service.update_fin_edad(guid)

        logger.info(f"[AGE] {guid} → {len(processed_faces)} caras procesadas")

        producer_service.publish_age_detection_completed(guid, id_imagen, s3_key, processed_faces)

    except Exception as e:
        logger.error(f"[ERROR AGE SERVICE] {e}")
