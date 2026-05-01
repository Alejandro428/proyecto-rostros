import os
from typing import Dict, Any

KAFKA_CONF_CONSUMER: Dict[str, Any] = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
    "group.id": "orch-2-group",
    "auto.offset.reset": "earliest"
}

KAFKA_CONF_PRODUCER: Dict[str, Any] = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092")
}

MINIO_CONF = {
    "endpoint_url":          os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "aws_access_key_id":     os.getenv("MINIO_USER"),
    "aws_secret_access_key": os.getenv("MINIO_PASSWORD")
}

DB_CONF: Dict[str, Any] = {
    "host":     os.getenv("DB_HOST",     "db"),
    "database": os.getenv("DB_NAME",     "db_rostros"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

BUCKET_RAW     = "images-raw"
TOPIC_CONSUME  = "evt.face_detection.completed"
TOPIC_PRODUCE  = "cmd.age_detection"
