import os

KAFKA_CONF_CONSUMER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
    "group.id": "orch-3-group",
    "auto.offset.reset": "earliest"
}
KAFKA_CONF_PRODUCER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092")
}
DB_CONF = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user":     os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

TOPIC_CONSUME = "evt.age_detection.completed"
