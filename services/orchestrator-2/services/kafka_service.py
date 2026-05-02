import json
from datetime import datetime
from confluent_kafka import Consumer, Producer
import logging

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    def __init__(self, conf: dict, topic: str):
        self.consumer = Consumer(conf)
        self.consumer.subscribe([topic])

    def poll(self, timeout: float = 1.0):
        return self.consumer.poll(timeout)

    def commit(self):
        self.consumer.commit(asynchronous=False)

    def close(self):
        self.consumer.close()


class KafkaProducerService:
    def __init__(self, conf: dict):
        self.producer = Producer(conf)

    def _delivery_report(self, err, msg):
        if err:
            logger.error(f"Kafka error: {err}")
        else:
            logger.debug(f"Kafka: evento enviado a {msg.topic()}")

    def publish_cmd_age_detection(self, guid: str, id_imagen: int, s3_key: str, faces: list):
        event = {
            "version":        "1.0",
            "timestamp":      datetime.utcnow().isoformat() + "Z",
            "GUID_Solicitud": guid,
            "Id_Imagen":      id_imagen,
            "s3_key":         s3_key,
            "faces":          faces
        }
        self.producer.produce(
            "cmd.age_detection",
            value=json.dumps(event).encode("utf-8"),
            callback=self._delivery_report
        )
        self.producer.flush(timeout=5)

    def publish_cmd_storage(self, guid: str, id_imagen: int, s3_key: str, faces: list):
        event = {
            "version":        "1.0",
            "timestamp":      datetime.utcnow().isoformat() + "Z",
            "GUID_Solicitud": guid,
            "Id_Imagen":      id_imagen,
            "s3_key":         s3_key,
            "faces":          faces
        }
        self.producer.produce(
            "cmd.storage",
            value=json.dumps(event).encode("utf-8"),
            callback=self._delivery_report
        )
        self.producer.flush(timeout=5)

    def close(self):
        self.producer.flush(timeout=5)
