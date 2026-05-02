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

    def insert_cara(self, guid: str, x: int, y: int, w: int, h: int) -> int:
        """Inserta fila de cara en Imagenes. Retorna Id_Imagen."""
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO Imagenes (GUID_Solicitud, URL_Imagen, Mayor_18, Escore, Imagen_X, Imagen_Y, Imagen_Ancho, Imagen_Alto)
                VALUES (%s, NULL, NULL, NULL, %s, %s, %s, %s)
                RETURNING Id_Imagen
            """, (guid, x, y, w, h))
            id_cara = cur.fetchone()[0]
            conn.commit()
            return id_cara
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error insert_cara: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_url_cara(self, guid: str, id_cara: int, url: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Imagenes SET URL_Imagen = %s WHERE GUID_Solicitud = %s AND Id_Imagen = %s",
                (url, guid, id_cara)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_url_cara: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_caras_detectadas(self, guid: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Estado = 'CARAS_DETECTADAS' WHERE GUID_Solicitud = %s",
                (guid,)
            )
            conn.commit()
            logger.info(f"BD: Estado=CARAS_DETECTADAS - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_caras_detectadas: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_inicio_edad(self, guid: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Inicio_Edad = %s, Estado = 'CARAS_DETECTADAS' WHERE GUID_Solicitud = %s",
                (datetime.utcnow(), guid)
            )
            conn.commit()
            logger.info(f"BD: Inicio_Edad + CARAS_DETECTADAS - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_inicio_edad: {e}")
            raise
        finally:
            cur.close()
            conn.close()
