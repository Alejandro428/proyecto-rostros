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
    "group.id": "orch-3-group",
    "auto.offset.reset": "earliest",
    "enable.auto.commit": False,
}
KAFKA_CONF_PRODUCER = {
    "bootstrap.servers": os.getenv("KAFKA_SERVER", "kafka:9092"),
}
DB_CONF = {
    "host":     os.getenv("DB_HOST", "db"),
    "database": os.getenv("DB_NAME", "db_rostros"),
    "user":     _require("DB_USER"),
    "password": _require("DB_PASSWORD"),
}

TOPIC_CONSUME = "evt.age_detection.completed"
