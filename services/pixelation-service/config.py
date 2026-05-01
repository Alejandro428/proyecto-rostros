import os

KAFKA_CONF_CONSUMER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
    "group.id": "pixelation-group",
    "auto.offset.reset": "earliest"
}
KAFKA_CONF_PRODUCER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092")
}
MINIO_CONF = {
    "endpoint_url":          os.getenv("MINIO_ENDPOINT", "http://minio:9000"),
    "aws_access_key_id":     os.getenv("MINIO_USER"),
    "aws_secret_access_key": os.getenv("MINIO_PASSWORD")
}
DB_CONF = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

BUCKET_RAW       = "images-raw"
BUCKET_PROCESSED = "images-processed"

TOPICS_CONSUME = ["cmd.pixelation", "cmd.storage"]
