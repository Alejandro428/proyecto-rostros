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

    def update_fin_solicitud(self, guid: str, url_terminada: str, url_marcos: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            now = datetime.utcnow()
            cur.execute("""
                UPDATE Solicitud
                SET Fin_Pixelado                  = %s,
                    Inicio_Almacenamiento_Solicitud = %s,
                    Fin_Almacenamiento_Solicitud   = %s,
                    Fin_Solicitud                  = %s,
                    URL_Imagen_Terminada           = %s,
                    URL_Imagen_Marcos              = %s,
                    Estado                         = 'COMPLETADA'
                WHERE GUID_Solicitud = %s
            """, (now, now, now, now, url_terminada, url_marcos, guid))
            conn.commit()
            logger.info(f"BD: solicitud completada - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_fin_solicitud: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_fin_solo_marcos(self, guid: str, url_marcos: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            now = datetime.utcnow()
            cur.execute("""
                UPDATE Solicitud
                SET Fin_Solicitud   = %s,
                    URL_Imagen_Marcos = %s,
                    Estado          = 'COMPLETADA'
                WHERE GUID_Solicitud = %s
            """, (now, url_marcos, guid))
            conn.commit()
            logger.info(f"BD: solicitud sin menores completada - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_fin_solo_marcos: {e}")
            raise
        finally:
            cur.close()
            conn.close()

    def update_fin_solicitud_sin_caras(self, guid: str):
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            now = datetime.utcnow()
            cur.execute("""
                UPDATE Solicitud
                SET Inicio_Almacenamiento_Solicitud = %s,
                    Fin_Almacenamiento_Solicitud    = %s,
                    Fin_Solicitud                   = %s,
                    Estado                          = 'COMPLETADA'
                WHERE GUID_Solicitud = %s
            """, (now, now, now, guid))
            conn.commit()
            logger.info(f"BD: solicitud sin caras completada - GUID={guid}")
        except Exception as e:
            conn.rollback()
            logger.error(f"BD error update_fin_solicitud_sin_caras: {e}")
            raise
        finally:
            cur.close()
            conn.close()
