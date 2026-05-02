import psycopg2
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, db_conf: dict):
        self.db_conf = db_conf

    def update_estado_error(self, guid: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute("UPDATE Solicitud SET Estado = 'ERROR' WHERE GUID_Solicitud = %s", (guid,))
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error al marcar error: {e}")
        finally:
            cur.close()
            conn.close()

    def update_imagen_clasificacion(self, guid: str, face_id: int, mayor_18: bool, score: float):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Imagenes SET Mayor_18 = %s, Escore = %s WHERE GUID_Solicitud = %s AND Id_Imagen = %s",
                (mayor_18, score, guid, face_id)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_imagen_clasificacion: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_fin_edad(self, guid: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Fin_edad = %s, Estado = 'EDAD_CALCULADA' WHERE GUID_Solicitud = %s",
                (datetime.utcnow(), guid)
            )
            conn.commit()
            logger.info(f"BD: Fin_edad actualizado - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_fin_edad: {e}")
            raise
        finally:
            cur.close()
            conn.close()
