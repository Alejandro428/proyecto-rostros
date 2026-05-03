import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from config import DB_CONF, MINIO_CONF, KAFKA_CONF, BUCKET_RAW, ALLOWED_EXTENSIONS, MAX_FILE_SIZE, TOPIC_RAW, TOPIC_DETECT
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_producer import KafkaProducerService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Inicialización de servicios
db_service = DatabaseService(DB_CONF)
storage_service = StorageService(MINIO_CONF, BUCKET_RAW)
kafka_service = KafkaProducerService(KAFKA_CONF)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await storage_service.init_buckets()
    yield
    kafka_service.close()

app = FastAPI(title="API-1", version="1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAGIC_SIGNATURES = [
    (b'\xff\xd8\xff',  'image/jpeg'),
    (b'\x89PNG',       'image/png'),
]

def detectar_content_type(header: bytes) -> str | None:
    for sig, ct in MAGIC_SIGNATURES:
        if header.startswith(sig):
            return ct
    return None


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-1"}

@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_image(file: UploadFile = File(...)):
    """Recibe imagen, la almacena en MinIO y publica eventos en Kafka."""

    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")

    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Máximo {MAX_FILE_SIZE // (1024*1024)}MB")

    header = await file.read(8)
    await file.seek(0)
    content_type = detectar_content_type(header)
    if not content_type:
        raise HTTPException(status_code=400, detail="El archivo no es una imagen válida")

    ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Solo permitido: {', '.join(ALLOWED_EXTENSIONS)}")

    guid_solicitud = str(uuid.uuid4())
    s3_key = f"{guid_solicitud}/{uuid.uuid4()}.{ext}"

    # 1. MinIO primero: si falla, nada queda registrado en BD
    try:
        await storage_service.upload(file.file, s3_key, content_type)
    except Exception as e:
        logger.error(f"MinIO upload error: {e}")
        raise HTTPException(status_code=500, detail="Error al almacenar la imagen")

    # 2. BD
    try:
        id_imagen = db_service.insert_request(guid_solicitud, s3_key)
    except Exception as e:
        logger.error(f"DB insert error (s3_key={s3_key}): {e}")
        raise HTTPException(status_code=500, detail="Error al registrar la solicitud")

    # 3. Kafka — si falla, revertimos BD (MinIO queda huérfano pero no hay registro)
    try:
        kafka_service.publish_batch(TOPIC_RAW, TOPIC_DETECT, guid_solicitud, id_imagen, s3_key)
        db_service.update_inicio_deteccion_caras(guid_solicitud)
    except Exception as e:
        logger.error(f"Kafka error, revirtiendo BD (GUID={guid_solicitud}): {e}")
        db_service.delete_request(guid_solicitud)
        raise HTTPException(status_code=500, detail="Error al encolar el procesamiento")

    logger.info(f"Upload completado: {guid_solicitud}")
    return {"GUID_Solicitud": guid_solicitud, "Id_Imagen": id_imagen, "status": "CREADA"}