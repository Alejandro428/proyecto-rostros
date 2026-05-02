import signal
import cv2
import json
import logging
import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.resnet50 import preprocess_input

from config import (
    DB_CONF, MINIO_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER,
    BUCKET_RAW, TOPIC_CONSUME, MODEL_PATH, IMG_SIZE_CV2, THRESHOLD
)
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

model = tf.keras.models.load_model(MODEL_PATH)
logger.info(f"Modelo cargado desde {MODEL_PATH}")
db_service       = DatabaseService(DB_CONF)
storage_service  = StorageService(MINIO_CONF, BUCKET_RAW)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

running = True

def _shutdown(sig, frame):
    global running
    logger.info("Señal de parada recibida, cerrando...")
    running = False

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

logger.info("--- [AGE SERVICE] INICIADO ---")

while running:
    msg = consumer_service.poll(1.0)
    if msg is None:
        continue

    if msg.error():
        logger.error(f"Kafka error: {msg.error()}")
        continue

    guid = None
    try:
        data = json.loads(msg.value().decode("utf-8"))

        guid      = data["GUID_Solicitud"]
        id_imagen = data["Id_Imagen"]
        s3_key    = data["s3_key"]
        faces     = data.get("faces", [])

        if not guid or not faces:
            logger.warning(f"Mensaje vacío o sin caras: {data}")
            consumer_service.commit()
            continue

        processed_faces = []

        for face in faces:
            try:
                face_id     = face["face_id"]
                bbox        = face["bbox"]
                s3_key_cara = face["s3_key_cara"]

                img = storage_service.download_image(s3_key_cara)

                # OpenCV carga en BGR; el modelo se entrenó con RGB → convertir antes de preprocesar
                img_resized = cv2.resize(img, IMG_SIZE_CV2)
                img_rgb     = cv2.cvtColor(img_resized, cv2.COLOR_BGR2RGB)
                img_input   = np.expand_dims(preprocess_input(img_rgb.astype("float32")), axis=0)

                # Clases ordenadas alfabéticamente: 0=mayor, 1=menor → score >= threshold = MENOR
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

        logger.info(f"[AGE] {guid} → {len(processed_faces)} caras procesadas")

        # Kafka primero, luego BD
        producer_service.publish_age_detection_completed(guid, id_imagen, s3_key, processed_faces)
        db_service.update_fin_edad(guid)
        consumer_service.commit()

    except Exception as e:
        logger.error(f"[ERROR AGE SERVICE] procesando {guid}: {e}")
        if guid:
            db_service.update_estado_error(guid)
        consumer_service.commit()

consumer_service.close()
