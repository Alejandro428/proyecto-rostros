import cv2
import json
import logging

from config import DB_CONF, MINIO_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER, BUCKET_RAW, TOPIC_CONSUME
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_service       = DatabaseService(DB_CONF)
storage_service  = StorageService(MINIO_CONF, BUCKET_RAW)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

logger.info("--- [ORQUESTADOR 2] INICIADO ---")

while True:
    msg = consumer_service.poll(1.0)
    if msg is None:
        continue

    if msg.error():
        logger.error(f"Kafka error: {msg.error()}")
        continue

    try:
        data = json.loads(msg.value().decode("utf-8"))

        guid            = data["GUID_Solicitud"]
        id_imagen       = data["Id_Imagen"]
        s3_key_original = data["s3_key"]
        faces           = data["faces"]

        logger.info(f"[ORCH-2] {guid} — {len(faces)} caras recibidas")

        # 1. Descargar imagen original
        img = storage_service.download_image(s3_key_original)

        faces_payload = []

        # 2. Cropear cada cara, insertar en BD y subir a MinIO
        for face in faces:
            bbox = face["bbox"]
            x, y, w, h = bbox["x"], bbox["y"], bbox["w"], bbox["h"]

            crop = img[y:y+h, x:x+w]
            if crop.size == 0:
                logger.warning(f"Crop vacío para face {face['face_id']}, ignorando")
                continue

            id_cara     = db_service.insert_cara(guid, x, y, w, h)
            s3_key_cara = f"{guid}/faces/{id_cara}.jpg"

            storage_service.upload_crop(crop, s3_key_cara)
            db_service.update_url_cara(guid, id_cara, s3_key_cara)

            faces_payload.append({
                "face_id":     id_cara,
                "bbox":        bbox,
                "s3_key_cara": s3_key_cara
            })

        # 3. Decidir siguiente paso
        if faces_payload:
            db_service.update_inicio_edad(guid)
            producer_service.publish_cmd_age_detection(guid, id_imagen, s3_key_original, faces_payload)
            logger.info(f"[ORCH-2] {len(faces_payload)} caras → cmd.age_detection — {guid}")
        else:
            producer_service.publish_cmd_storage(guid, id_imagen, s3_key_original, [])
            logger.info(f"[ORCH-2] Sin caras → cmd.storage — {guid}")

    except Exception as e:
        logger.error(f"[ERROR ORCH-2] {e}")
