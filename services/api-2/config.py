import os

DB_CONF = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}
MINIO_CONF = {
    "endpoint_url":          os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "aws_access_key_id":     os.getenv("MINIO_USER"),
    "aws_secret_access_key": os.getenv("MINIO_PASSWORD")
}

# URL pública de MinIO para generar presigned URLs accesibles desde el navegador
MINIO_PUBLIC_URL = os.getenv("MINIO_PUBLIC_URL", "http://localhost:9000")

BUCKET_RAW       = "images-raw"
BUCKET_PROCESSED = "images-processed"
PRESIGNED_EXPIRY = 3600  # segundos
