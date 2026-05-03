import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from config import DB_CONF, MINIO_CONF, BUCKET_RAW, BUCKET_PROCESSED, PRESIGNED_EXPIRY
from services.db import DatabaseService
from services.storage import StorageService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="API Resultados Rostros")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-2"}

db_service      = DatabaseService(DB_CONF)
storage_service = StorageService(MINIO_CONF, BUCKET_RAW, BUCKET_PROCESSED)


def _minio_public_url(request: Request) -> str:
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", "localhost:3000")
    scheme = request.headers.get("x-forwarded-proto", "http")
    return f"{scheme}://{host}/storage"


@app.get("/solicitudes")
async def list_solicitudes(request: Request, limite: int = 100):
    pub = _minio_public_url(request)
    solicitudes = db_service.get_all_solicitudes(limite)
    for s in solicitudes:
        s["url_thumbnail"] = storage_service.presigned_url(BUCKET_RAW, s.pop("url_original"), PRESIGNED_EXPIRY, pub)
    return {"solicitudes": solicitudes}


@app.get("/resultado/{guid}")
async def get_resultado(guid: str, request: Request):
    solicitud = db_service.get_solicitud(guid)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    pub   = _minio_public_url(request)
    caras = db_service.get_caras(guid)

    imagenes = {
        "original":  storage_service.presigned_url(BUCKET_RAW,      solicitud["url_original"],  PRESIGNED_EXPIRY, pub),
        "marcos":    storage_service.presigned_url(BUCKET_PROCESSED, solicitud["url_marcos"],    PRESIGNED_EXPIRY, pub),
        "terminada": storage_service.presigned_url(BUCKET_PROCESSED, solicitud["url_terminada"], PRESIGNED_EXPIRY, pub),
    }

    return {
        "guid":   guid,
        "estado": solicitud["estado"],
        "tiempos": {
            "inicio_solicitud":       solicitud["inicio_solicitud"],
            "fin_solicitud":          solicitud["fin_solicitud"],
            "inicio_deteccion_caras": solicitud["inicio_deteccion_caras"],
            "fin_deteccion_caras":    solicitud["fin_deteccion_caras"],
            "inicio_edad":            solicitud["inicio_edad"],
            "fin_edad":               solicitud["fin_edad"],
            "inicio_pixelado":        solicitud["inicio_pixelado"],
            "fin_pixelado":           solicitud["fin_pixelado"],
        },
        "imagenes": imagenes,
        "caras_detectadas": len(caras),
        "caras": caras,
    }


@app.get("/resultado/{guid}/thumbnail")
async def get_thumbnail(guid: str, request: Request):
    solicitud = db_service.get_solicitud(guid)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    pub = _minio_public_url(request)
    url = storage_service.presigned_url(BUCKET_RAW, solicitud["url_original"], PRESIGNED_EXPIRY, pub)
    return {"url": url, "estado": solicitud["estado"]}


@app.get("/resultado/{guid}/cara/{id_cara}")
async def get_cara(guid: str, id_cara: int, request: Request):
    solicitud = db_service.get_solicitud(guid)
    if not solicitud:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    cara = db_service.get_cara(guid, id_cara)
    if not cara:
        raise HTTPException(status_code=404, detail="Cara no encontrada")

    pub = _minio_public_url(request)
    return {
        "guid":      guid,
        "id_imagen": cara["id_imagen"],
        "es_menor":  cara["es_menor"],
        "score":     cara["score"],
        "bbox":      cara["bbox"],
        "imagen":    storage_service.presigned_url(BUCKET_RAW, cara["url_imagen"], PRESIGNED_EXPIRY, pub),
    }
