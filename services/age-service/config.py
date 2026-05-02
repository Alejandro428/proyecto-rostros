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
    "group.id": "age-group",
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

BUCKET_RAW  = "images-raw"
TOPIC_CONSUME = "cmd.age_detection"
TOPIC_PRODUCE = "evt.age_detection.completed"
MODEL_PATH  = "modelo_menores.h5"

# cv2.resize usa (ancho, alto) — CNN básica entrenada con IMG_SIZE=(256,320) → (ancho=320, alto=256)
IMG_SIZE_CV2 = (320, 256)

# Threshold bajo para priorizar no perderse ningún menor:
# falso positivo (adulto pixelado) es preferible a falso negativo (menor no pixelado)
THRESHOLD = 0.45
