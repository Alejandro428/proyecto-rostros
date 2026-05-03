import signal
import json
import logging

from config import DB_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER, TOPIC_CONSUME, TOPIC_PRODUCE_PIX, TOPIC_PRODUCE_STORAGE
from services.db import DatabaseService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_service       = DatabaseService(DB_CONF)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

running = True

def _shutdown(sig, frame):
    global running
    logger.info("Señal de parada recibida, cerrando...")
    running = False

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

logger.info("--- [ORQUESTADOR 3] INICIADO ---")

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
        faces     = data["faces"]

        logger.info(f"[ORCH-3] {guid} — {len(faces)} caras recibidas")

        hay_menores = any(f.get("es_menor") for f in faces)

        if hay_menores:
            producer_service.publish_cmd_pixelation(TOPIC_PRODUCE_PIX, guid, id_imagen, s3_key, faces)
            consumer_service.commit()
            logger.info(f"[ORCH-3] {guid} → hay menores → {TOPIC_PRODUCE_PIX}")
            try:
                db_service.update_inicio_pixelado(guid)
            except Exception as e:
                logger.warning(f"No se pudo registrar inicio_pixelado (GUID={guid}): {e}")
        else:
            producer_service.publish_cmd_storage(TOPIC_PRODUCE_STORAGE, guid, id_imagen, s3_key, faces)
            consumer_service.commit()
            logger.info(f"[ORCH-3] {guid} → sin menores → {TOPIC_PRODUCE_STORAGE}")

    except Exception as e:
        logger.error(f"[ERROR ORCH-3] procesando {guid}: {e}")
        if guid:
            db_service.update_estado_error(guid)
        consumer_service.commit()

consumer_service.close()
