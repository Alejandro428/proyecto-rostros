import json
import logging

from config import DB_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER, TOPIC_CONSUME
from services.db import DatabaseService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_service       = DatabaseService(DB_CONF)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPIC_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

logger.info("--- [ORQUESTADOR 3] INICIADO ---")

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
        faces     = data["faces"]

        logger.info(f"[ORCH-3] {guid} — {len(faces)} caras recibidas")

        hay_menores = any(f.get("es_menor") for f in faces)

        if hay_menores:
            db_service.update_inicio_pixelado(guid)
            producer_service.publish_cmd_pixelation(guid, id_imagen, s3_key, faces)
            logger.info(f"[ORCH-3] {guid} → hay menores → cmd.pixelation")
        else:
            producer_service.publish_cmd_storage(guid, id_imagen, s3_key, faces)
            logger.info(f"[ORCH-3] {guid} → sin menores → cmd.storage")

    except Exception as e:
        logger.error(f"[ERROR ORCH-3] {e}")
