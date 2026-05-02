import psycopg2
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, db_conf: dict):
        self.db_conf = db_conf

    def update_fin_deteccion_caras(self, guid_solicitud: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Fin_Deteccion_Caras = %s WHERE GUID_Solicitud = %s",
                (datetime.utcnow(), guid_solicitud)
            )
            conn.commit()
            logger.info(f"BD: Fin_Deteccion_Caras actualizado - GUID={guid_solicitud}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_estado_error(self, guid_solicitud: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Estado = 'ERROR' WHERE GUID_Solicitud = %s",
                (guid_solicitud,)
            )
            conn.commit()
            logger.info(f"BD: Estado=ERROR - GUID={guid_solicitud}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error al marcar error: {e}")
        finally:
            cur.close()
            conn.close()
