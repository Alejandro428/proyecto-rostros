import json
from datetime import datetime
from confluent_kafka import Producer
import logging

logger = logging.getLogger(__name__)

KAFKA_FLUSH_TIMEOUT = 10

class KafkaProducerService:
    def __init__(self, kafka_conf: dict):
        self.producer = Producer(kafka_conf)

    def _delivery_report(self, err, msg):
        if err:
            logger.error(f"Kafka delivery error ({msg.topic()}): {err}")
        else:
            logger.debug(f"Kafka: mensaje confirmado en {msg.topic()}")

    def publish_batch(self, topic_raw: str, topic_detect: str, guid_solicitud: str, id_imagen: int, s3_key: str):
        event = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "GUID_Solicitud": guid_solicitud,
            "Id_Imagen": id_imagen,
            "s3_key": s3_key,
        }
        payload = json.dumps(event).encode("utf-8")
        self.producer.produce(topic_raw, value=payload, callback=self._delivery_report)
        self.producer.produce(topic_detect, value=payload, callback=self._delivery_report)
        pending = self.producer.flush(timeout=KAFKA_FLUSH_TIMEOUT)
        if pending > 0:
            raise RuntimeError(f"Kafka: {pending} mensajes sin confirmar tras {KAFKA_FLUSH_TIMEOUT}s")

    def close(self):
        self.producer.flush(timeout=KAFKA_FLUSH_TIMEOUT)