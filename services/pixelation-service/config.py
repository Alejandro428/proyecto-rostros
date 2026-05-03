import os
import sys

def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"ERROR: variable de entorno requerida no configurada: {name}", file=sys.stderr)
        sys.exit(1)
    return val

KAFKA_CONF_CONSUMER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
    "group.id": "pixelation-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}
KAFKA_CONF_PRODUCER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
}
MINIO_CONF = {
    "endpoint_url":          os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "aws_access_key_id":     _require("MINIO_USER"),
    "aws_secret_access_key": _require("MINIO_PASSWORD"),
}
DB_CONF = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user":     _require("DB_USER"),
    "password": _require("DB_PASSWORD"),
}

BUCKET_RAW       = "images-raw"
BUCKET_PROCESSED = "images-processed"

TOPICS_CONSUME = ["cmd.pixelation", "cmd.storage"]
TOPIC_PRODUCE  = "evt.pixelation.completed"
