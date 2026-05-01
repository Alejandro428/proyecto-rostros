import json
from datetime import datetime
from confluent_kafka import Producer, KafkaError
import logging

logger = logging.getLogger(__name__)

class KafkaProducerService:
    def __init__(self, kafka_conf: dict):
        self.producer = Producer(kafka_conf)
    
    def _delivery_report(self, err, msg):
        if err:
            logger.error(f"Kafka error: {err}")
        else:
            logger.debug(f"Kafka: Evento enviado a {msg.topic()}")
    
    async def publish_images_raw(self, guid_solicitud: str, id_imagen: int, s3_key: str):
        """Publica evento images.raw."""
        event = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "GUID_Solicitud": guid_solicitud,
            "Id_Imagen": id_imagen,
            "s3_key": s3_key
        }
        self.producer.produce(
            "images.raw",
            value=json.dumps(event).encode("utf-8"),
            callback=self._delivery_report
        )
    
    async def publish_cmd_face_detection(self, guid_solicitud: str, id_imagen: int, s3_key: str):
        """Publica comando cmd.face_detection."""
        event = {
            "version": "1.0",
            "timestamp": datetime.utcnow().isoformat(),
            "GUID_Solicitud": guid_solicitud,
            "Id_Imagen": id_imagen,
            "s3_key": s3_key
        }
        self.producer.produce(
            "cmd.face_detection",
            value=json.dumps(event).encode("utf-8"),
            callback=self._delivery_report
        )
        self.producer.flush(timeout=5)
    
    def close(self):
        self.producer.flush(timeout=5)