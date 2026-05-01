import json
from confluent_kafka import Consumer, Producer
import logging

logger = logging.getLogger(__name__)


class KafkaConsumerService:
    def __init__(self, conf: dict, topics: list):
        self.consumer = Consumer(conf)
        self.consumer.subscribe(topics)

    def poll(self, timeout: float = 1.0):
        return self.consumer.poll(timeout)

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

    def close(self):
        self.producer.flush(timeout=5)
