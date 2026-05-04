"""
Configuración global de pytest.

- Inyecta las variables de entorno requeridas por los servicios antes de
  que cualquier módulo de servicio sea importado.
- Registra stubs (MagicMock) para las librerías que requieren
  infraestructura real (Kafka, PostgreSQL, modelos ML) de modo que los
  tests unitarios puedan importar código de servicio sin conexiones reales.
"""

import os
import sys
from unittest.mock import MagicMock


def pytest_configure(config):
    # ── Variables de entorno ──────────────────────────────────────────────────
    defaults = {
        "DB_USER":         "testuser",
        "DB_PASSWORD":     "testpass",
        "DB_HOST":         "localhost",
        "DB_NAME":         "testdb",
        "MINIO_USER":      "minioadmin",
        "MINIO_PASSWORD":  "minioadmin",
        "MINIO_ENDPOINT":  "http://localhost:9000",
        "KAFKA_SERVER":    "localhost:9092",
        "MAX_FILE_SIZE":   str(10 * 1024 * 1024),
        "PYTHONUNBUFFERED": "1",
    }
    for k, v in defaults.items():
        os.environ.setdefault(k, v)

    # ── Stubs de infraestructura ──────────────────────────────────────────────
    # Se inyectan en sys.modules antes de que cualquier import de servicio
    # los solicite, para que el código cargue sin conexiones reales.
    stubs = [
        "psycopg2",
        "confluent_kafka",
        "insightface",
        "insightface.app",
        "tensorflow",
        "tensorflow.keras",
        "tensorflow.keras.models",
        "tensorflow.keras.applications",
        "tensorflow.keras.applications.resnet50",
    ]
    for mod in stubs:
        sys.modules.setdefault(mod, MagicMock())
