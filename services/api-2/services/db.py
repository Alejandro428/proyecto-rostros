import psycopg2
import logging

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, db_conf: dict):
        self.db_conf = db_conf

    def get_solicitud(self, guid: str) -> dict | None:
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT
                    Estado,
                    URL_Imagen_Original,
                    URL_Imagen_Terminada,
                    URL_Imagen_Marcos,
                    Inicio_Solicitud,
                    Fin_Solicitud,
                    Inicio_Deteccion_Caras,
                    Fin_Deteccion_Caras,
                    Inicio_Edad,
                    Fin_edad,
                    Inicio_Pixelado,
                    Fin_Pixelado,
                    Inicio_Almacenamiento_Solicitud,
                    Fin_Almacenamiento_Solicitud
                FROM Solicitud
                WHERE GUID_Solicitud = %s
            """, (guid,))
            row = cur.fetchone()
            if not row:
                return None
            cols = [
                "estado", "url_original", "url_terminada", "url_marcos",
                "inicio_solicitud", "fin_solicitud",
                "inicio_deteccion_caras", "fin_deteccion_caras",
                "inicio_edad", "fin_edad",
                "inicio_pixelado", "fin_pixelado",
                "inicio_almacenamiento", "fin_almacenamiento"
            ]
            return dict(zip(cols, row))
        finally:
            cur.close()
            conn.close()

    def get_caras(self, guid: str) -> list:
        conn = psycopg2.connect(**self.db_conf)
        cur = conn.cursor()
        try:
            cur.execute("""
                SELECT Id_Imagen, Mayor_18, Escore, Imagen_X, Imagen_Y, Imagen_Ancho, Imagen_Alto
                FROM Imagenes
                WHERE GUID_Solicitud = %s
                  AND Imagen_X IS NOT NULL
                ORDER BY Id_Imagen
            """, (guid,))
            rows = cur.fetchall()
            return [
                {
                    "id_imagen": r[0],
                    "es_menor":  not r[1] if r[1] is not None else None,
                    "score":     float(r[2]) if r[2] is not None else None,
                    "bbox":      {"x": r[3], "y": r[4], "w": r[5], "h": r[6]}
                }
                for r in rows
            ]
        finally:
            cur.close()
            conn.close()
