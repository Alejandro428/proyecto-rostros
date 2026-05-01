import psycopg2
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, db_conf: dict):
        self.db_conf = db_conf

    def update_inicio_pixelado(self, guid: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Inicio_Pixelado = %s WHERE GUID_Solicitud = %s",
                (datetime.utcnow(), guid)
            )
            conn.commit()
            logger.info(f"BD: Inicio_Pixelado actualizado - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_inicio_pixelado: {e}")
            raise
        finally:
            cur.close()
            conn.close()
