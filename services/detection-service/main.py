import cv2
import json
import logging

from config import DB_CONF, MINIO_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER, BUCKET_RAW, TOPIC_CONSUME
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_service = DatabaseService(DB_CONF)
storage_service = StorageService(MINIO_CONF, BUCKET_RAW)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

logger.info("--- [FACE DETECTION SERVICE] INICIADO ---")

while True:
    msg = consumer_service.poll(1.0)
    if msg is None:
        continue

    if msg.error():
        logger.error(f"Kafka error: {msg.error()}")
        continue

    try:
        data = json.loads(msg.value().decode("utf-8"))

        guid = data.get("GUID_Solicitud")
        id_imagen = data.get("Id_Imagen")
        s3_key = data.get("s3_key")

        if not guid or not s3_key or not id_imagen:
            logger.warning(f"Mensaje incompleto, ignorando: {data}")
            continue

        # 1. Descargar imagen
        img = storage_service.download_image(s3_key)

        # 2. Detección de caras
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(30, 30)
        )

        face_list = [
            {
                "face_id": face_id,
                "bbox": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            }
            for face_id, (x, y, w, h) in enumerate(faces)
        ]

        logger.info(f"[DETECTION] {guid} -> {len(face_list)} caras detectadas")

        # 3. Métrica BD
        db_service.update_fin_deteccion_caras(guid)

        # 4. Publicar evento
        producer_service.publish_face_detection_completed(guid, id_imagen, s3_key, face_list)

    except Exception as e:
        logger.error(f"[ERROR] {str(e)}")
