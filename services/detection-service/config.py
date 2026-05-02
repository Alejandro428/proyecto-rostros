import os
import sys
from typing import Dict, Any

def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"ERROR: variable de entorno requerida no configurada: {name}", file=sys.stderr)
        sys.exit(1)
    return val

KAFKA_CONF_CONSUMER: Dict[str, Any] = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
    "group.id": "detect-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}

KAFKA_CONF_PRODUCER: Dict[str, Any] = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
}

MINIO_CONF = {
    "endpoint_url": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "aws_access_key_id": _require("MINIO_USER"),
    "aws_secret_access_key": _require("MINIO_PASSWORD"),
}

DB_CONF: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user": _require("DB_USER"),
    "password": _require("DB_PASSWORD"),
}

BUCKET_RAW = "images-raw"
TOPIC_CONSUME = "cmd.face_detection"
TOPIC_PRODUCE = "evt.face_detection.completed"
