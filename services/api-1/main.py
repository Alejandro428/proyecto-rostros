import uuid
import logging
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, UploadFile, File, HTTPException, status
import psycopg2
import boto3
from confluent_kafka import Producer, KafkaError

from config import DB_CONF, MINIO_CONF, KAFKA_CONF, BUCKET_RAW, ALLOWED_EXTENSIONS, MAX_FILE_SIZE
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

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "api-1"}

@app.post("/upload", status_code=status.HTTP_202_ACCEPTED)
async def upload_image(file: UploadFile = File(...)):
    """Recibe imagen, la almacena en MinIO y publica eventos en Kafka."""
    
    # Validar
    if not file.filename:
        raise HTTPException(status_code=400, detail="Nombre de archivo requerido")
    
    ext = file.filename.split('.')[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Solo permitido: {', '.join(ALLOWED_EXTENSIONS)}")
    
    if file.size and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"Máximo {MAX_FILE_SIZE // (1024*1024)}MB")
    
    guid_solicitud = str(uuid.uuid4())
    unique_file = str(uuid.uuid4())
    s3_key = f"{guid_solicitud}/{unique_file}.{ext}"
    
    try:
        # 1. BD (primero, para atomicidad)
        id_imagen = db_service.insert_request(guid_solicitud, s3_key)
        
        # 2. MinIO
        await storage_service.upload(file.file, s3_key, file.content_type)
        
        # 3. Kafka
        await kafka_service.publish_images_raw(guid_solicitud, id_imagen, s3_key)
        await kafka_service.publish_cmd_face_detection(guid_solicitud, id_imagen, s3_key)
        db_service.update_inicio_deteccion_caras(guid_solicitud)

        logger.info(f"✅ Upload completado: {guid_solicitud}")
        return {"GUID_Solicitud": guid_solicitud, "Id_Imagen": id_imagen, "status": "INICIADO"}
    
    except Exception as e:
        logger.error(f"Error en upload: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))