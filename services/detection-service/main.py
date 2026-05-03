import signal
import cv2
import json
import logging
from insightface.app import FaceAnalysis

from config import DB_CONF, MINIO_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER, BUCKET_RAW, TOPIC_CONSUME, TOPIC_PRODUCE
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_service       = DatabaseService(DB_CONF)
storage_service  = StorageService(MINIO_CONF, BUCKET_RAW)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

face_detector = FaceAnalysis(name="buffalo_l", allowed_modules=["detection"])
face_detector.prepare(ctx_id=-1, det_size=(640, 640))

running = True

def _shutdown(sig, frame):
    global running
    logger.info("Señal de parada recibida, cerrando...")
    running = False

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

logger.info("--- [FACE DETECTION SERVICE] INICIADO ---")

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

        guid      = data.get("GUID_Solicitud")
        id_imagen = data.get("Id_Imagen")
        s3_key    = data.get("s3_key")

        if not guid or not s3_key or not id_imagen:
            logger.warning(f"Mensaje incompleto, descartando: {data}")
            consumer_service.commit()
            continue

        # 1. Descargar imagen
        img = storage_service.download_image(s3_key)
        h, w = img.shape[:2]

        # 2. Detección de caras (insightface espera BGR)
        faces = face_detector.get(img)

        face_list = []
        for face_id, face in enumerate(faces):
            x1, y1, x2, y2 = [int(v) for v in face.bbox]
            x  = max(0, x1)
            y  = max(0, y1)
            bw = min(x2 - x1, w - x)
            bh = min(y2 - y1, h - y)
            if bw > 0 and bh > 0:
                face_list.append({
                    "face_id": face_id,
                    "bbox": {"x": x, "y": y, "w": bw, "h": bh}
                })

        logger.info(f"[DETECTION] {guid} -> {len(face_list)} caras detectadas")

        # 3. Publicar evento primero para garantizar consistencia
        producer_service.publish_face_detection_completed(TOPIC_PRODUCE, guid, id_imagen, s3_key, face_list)

        # 4. Confirmar offset: el flujo ya avanzó
        consumer_service.commit()

        # 5. Métrica BD — fallo no crítico (el flujo ya avanzó)
        try:
            db_service.update_fin_deteccion_caras(guid)
        except Exception as e:
            logger.warning(f"No se pudo registrar fin_deteccion_caras (GUID={guid}): {e}")

    except Exception as e:
        logger.error(f"[ERROR] procesando {guid}: {e}")
        if guid:
            db_service.update_estado_error(guid)
        consumer_service.commit()

consumer_service.close()
