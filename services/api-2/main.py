import logging
from fastapi import FastAPI, HTTPException

from config import DB_CONF, MINIO_CONF, MINIO_PUBLIC_URL, BUCKET_RAW, BUCKET_PROCESSED, PRESIGNED_EXPIRY
from services.db import DatabaseService
from services.storage import StorageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Resultados Rostros")

db_service      = DatabaseService(DB_CONF)
storage_service = StorageService(MINIO_CONF, MINIO_PUBLIC_URL, BUCKET_RAW, BUCKET_PROCESSED)


@app.get("/resultado/{guid}")
async def get_resultado(guid: str):
    solicitud = db_service.get_solicitud(guid)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    caras = db_service.get_caras(guid)

    imagenes = {
        "original":  storage_service.presigned_url(BUCKET_RAW,       solicitud["url_original"],  PRESIGNED_EXPIRY),
        "marcos":    storage_service.presigned_url(BUCKET_PROCESSED,  solicitud["url_marcos"],    PRESIGNED_EXPIRY),
        "terminada": storage_service.presigned_url(BUCKET_PROCESSED,  solicitud["url_terminada"], PRESIGNED_EXPIRY),
    }

    return {
        "guid":   guid,
        "estado": solicitud["estado"],
        "tiempos": {
            "inicio_solicitud":      solicitud["inicio_solicitud"],
            "fin_solicitud":         solicitud["fin_solicitud"],
            "inicio_deteccion_caras": solicitud["inicio_deteccion_caras"],
            "fin_deteccion_caras":   solicitud["fin_deteccion_caras"],
            "inicio_edad":           solicitud["inicio_edad"],
            "fin_edad":              solicitud["fin_edad"],
            "inicio_pixelado":       solicitud["inicio_pixelado"],
            "fin_pixelado":          solicitud["fin_pixelado"],
        },
        "imagenes": imagenes,
        "caras_detectadas": len(caras),
        "caras": caras,
    }
