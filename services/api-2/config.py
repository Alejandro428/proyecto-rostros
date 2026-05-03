import os
import sys

def _require(name: str) -> str:
    val = os.getenv(name)
    if not val:
        print(f"ERROR: variable de entorno requerida no configurada: {name}", file=sys.stderr)
        sys.exit(1)
    return val

DB_CONF = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user":     _require("DB_USER"),
    "password": _require("DB_PASSWORD"),
}

# api-2 sólo genera presigned URLs: usa el endpoint público directamente.
MINIO_PUBLIC_ENDPOINT = os.getenv("MINIO_PUBLIC_ENDPOINT", "http://localhost:9000")
MINIO_ACCESS_KEY      = _require("MINIO_USER")
MINIO_SECRET_KEY      = _require("MINIO_PASSWORD")

BUCKET_RAW       = "images-raw"
BUCKET_PROCESSED = "images-processed"
PRESIGNED_EXPIRY = 3600
