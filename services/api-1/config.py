import os
from typing import Dict, Any

# Database
DB_CONF: Dict[str, Any] = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

# MinIO
MINIO_CONF = {
    "endpoint_url": os.getenv("MINIO_ENDPOINT", "http://localhost:9000"),
    "aws_access_key_id": os.getenv("MINIO_USER"),
    "aws_secret_access_key": os.getenv("MINIO_PASSWORD")
}

BUCKET_RAW = "images-raw"
BUCKET_PROCESSED = "images-processed"

# Kafka
KAFKA_CONF = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "localhost:9092"),
    "client.id": "api-1-producer"
}

# Upload
ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "bmp", "gif"}
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 50 * 1024 * 1024))  # 50MB default