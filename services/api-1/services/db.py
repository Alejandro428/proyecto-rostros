import psycopg2
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class DatabaseService:
    def __init__(self, db_conf: dict):
        self.db_conf = db_conf
    
    def insert_request(self, guid_solicitud: str, s3_key: str) -> int:
        """Inserta solicitud e imagen en BD. Retorna Id_Imagen."""
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        
        try:
            cur.execute(
                "INSERT INTO Solicitud (GUID_Solicitud, URL_Imagen_Original, Inicio_Solicitud, Estado) "
                "VALUES (%s, %s, %s, %s)",
                (guid_solicitud, s3_key, datetime.utcnow(), "CREADA")
            )
            
            cur.execute(
                "INSERT INTO Imagenes (GUID_Solicitud, URL_Imagen, Mayor_18, Escore, Imagen_X, Imagen_Y, Imagen_Ancho, Imagen_Alto) "
                "VALUES (%s, %s, NULL, NULL, NULL, NULL, NULL, NULL) "
                "RETURNING Id_Imagen",
                (guid_solicitud, s3_key)
            )
            
            id_imagen = cur.fetchone()[0]
            conn.commit()
            logger.info(f"BD: INSERT OK - GUID={guid_solicitud}, Id_Imagen={id_imagen}")
            return id_imagen
        
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def delete_request(self, guid_solicitud: str):
        """Elimina solicitud e imágenes de BD (rollback tras fallo de Kafka)."""
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM Imagenes WHERE GUID_Solicitud = %s", (guid_solicitud,))
            cur.execute("DELETE FROM Solicitud WHERE GUID_Solicitud = %s", (guid_solicitud,))
            conn.commit()
            logger.info(f"BD: rollback OK - GUID={guid_solicitud}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error en rollback: {e}")
        finally:
            cur.close()
            conn.close()

    def update_inicio_deteccion_caras(self, guid_solicitud: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute(
                "UPDATE Solicitud SET Inicio_Deteccion_Caras = %s WHERE GUID_Solicitud = %s",
                (datetime.utcnow(), guid_solicitud)
            )
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update inicio deteccion: {e}")
            raise
        finally:
            cur.close()
            conn.close()