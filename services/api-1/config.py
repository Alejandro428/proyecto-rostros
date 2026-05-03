import os
import sys
from typing import Dict, Any

def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"ERROR: variable de entorno requerida no configurada: {name}", file=sys.stderr)
        sys.exit(1)
    return val

# Database
DB_CONF: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "db"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user": _require("DB_USER"),
    "password": _require("DB_PASSWORD"),
}

# MinIO
MINIO_CONF = {
    "endpoint_url": os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "aws_access_key_id": _require("MINIO_USER"),
    "aws_secret_access_key": _require("MINIO_PASSWORD"),
}

BUCKET_RAW = "images-raw"

# Kafka
KAFKA_CONF = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
    "client.id": "api-1-producer",
}

TOPIC_RAW    = "images.raw"
TOPIC_DETECT = "cmd.face_detection"

# Upload
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png"}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB default