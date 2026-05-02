import signal
import cv2
import json
import logging
import numpy as np

from config import (
    DB_CONF, MINIO_CONF, KAFKA_CONF_CONSUMER, KAFKA_CONF_PRODUCER,
    BUCKET_RAW, BUCKET_PROCESSED, TOPICS_CONSUME
)
from services.db import DatabaseService
from services.storage import StorageService
from services.kafka_service import KafkaConsumerService, KafkaProducerService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db_service       = DatabaseService(DB_CONF)
storage_service  = StorageService(MINIO_CONF, BUCKET_RAW, BUCKET_PROCESSED)
consumer_service = KafkaConsumerService(KAFKA_CONF_CONSUMER, TOPICS_CONSUME)
producer_service = KafkaProducerService(KAFKA_CONF_PRODUCER)

running = True

def _shutdown(sig, frame):
    global running
    logger.info("Señal de parada recibida, cerrando...")
    running = False

signal.signal(signal.SIGTERM, _shutdown)
signal.signal(signal.SIGINT, _shutdown)

logger.info("--- [PIXELATION SERVICE] INICIADO ---")


def generar_imagen_marcos(img: np.ndarray, faces: list) -> np.ndarray:
    resultado = img.copy()
    font      = cv2.FONT_HERSHEY_SIMPLEX

    for face in faces:
        x, y, w, h = face["bbox"]["x"], face["bbox"]["y"], face["bbox"]["w"], face["bbox"]["h"]
        es_menor   = face.get("es_menor", False)
        score      = face.get("score", None)

        color    = (0, 0, 255) if es_menor else (0, 255, 0)
        label    = "Menor" if es_menor else "Adulto"
        etiqueta = f"{label}:{score:.3f}" if score is not None else label

        # Marco fino fijo
        cv2.rectangle(resultado, (x, y), (x + w, y + h), color, 1)

        # Escala proporcional al bbox, acotada entre 0.2 y 0.5
        scale = max(0.2, min(0.5, w / 200.0))

        # Texto: 3 decimales; si no cabe en el ancho, reducir a 1 decimal (mínimo)
        etiqueta_corta = f"{'Menor' if es_menor else 'Adulto'}:{score:.1f}" if score is not None else ('Menor' if es_menor else 'Adulto')
        (tw, _), _ = cv2.getTextSize(etiqueta, font, scale, 1)
        texto = etiqueta if tw <= w - 4 else etiqueta_corta

        (tw, th), baseline = cv2.getTextSize(texto, font, scale, 1)
        band_h = th + baseline + 4
        cv2.rectangle(resultado, (x, y), (x + w, y + band_h), color, cv2.FILLED)
        cv2.putText(resultado, texto, (x + 2, y + th + 2),
                    font, scale, (255, 255, 255), 1, cv2.LINE_AA)

    return resultado


def generar_imagen_terminada(img: np.ndarray, faces: list) -> np.ndarray:
    """Pixela las caras de menores."""
    resultado = img.copy()
    for face in faces:
        if not face.get("es_menor", False):
            continue
        x, y, w, h = face["bbox"]["x"], face["bbox"]["y"], face["bbox"]["w"], face["bbox"]["h"]
        roi = resultado[y:y + h, x:x + w]
        if roi.size == 0:
            continue
        temp = cv2.resize(roi, (12, 12), interpolation=cv2.INTER_LINEAR)
        resultado[y:y + h, x:x + w] = cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    return resultado


while running:
    msg = consumer_service.poll(1.0)
    if msg is None:
        continue

    if msg.error():
        logger.error(f"Kafka error: {msg.error()}")
        continue

    guid = None
    try:
        topic = msg.topic()
        data  = json.loads(msg.value().decode("utf-8"))

        guid      = data["GUID_Solicitud"]
        id_imagen = data["Id_Imagen"]
        s3_key    = data["s3_key"]
        faces     = data.get("faces", [])

        logger.info(f"[PIXELATION] {guid} — topic={topic} — {len(faces)} caras")

        if topic == "cmd.storage" and not faces:
            # Sin caras (viene de O2): Kafka primero, luego BD
            producer_service.publish_pixelation_completed(guid, id_imagen, s3_key, [])
            db_service.update_fin_solicitud_sin_caras(guid)
            logger.info(f"[PIXELATION] {guid} → completado sin caras")
            consumer_service.commit()
            continue

        if topic == "cmd.storage" and faces:
            # Sin menores (viene de O3): solo generar imagen de marcos
            img_original = storage_service.download_image(s3_key)
            img_marcos   = generar_imagen_marcos(img_original, faces)
            key_marcos   = f"{guid}/marcos.jpg"
            storage_service.upload_image(img_marcos, key_marcos)
            producer_service.publish_pixelation_completed(guid, id_imagen, s3_key, faces)
            db_service.update_fin_solo_marcos(guid, key_marcos)
            logger.info(f"[PIXELATION] {guid} → completado sin menores — marcos={key_marcos}")
            consumer_service.commit()
            continue

        # cmd.pixelation — hay menores: generar marcos + terminada
        img_original  = storage_service.download_image(s3_key)
        img_marcos    = generar_imagen_marcos(img_original, faces)
        img_terminada = generar_imagen_terminada(img_original, faces)
        key_marcos    = f"{guid}/marcos.jpg"
        key_terminada = f"{guid}/terminada.jpg"

        storage_service.upload_image(img_marcos,    key_marcos)
        storage_service.upload_image(img_terminada, key_terminada)

        # Kafka primero, luego BD
        producer_service.publish_pixelation_completed(guid, id_imagen, s3_key, faces)
        db_service.update_fin_solicitud(guid, key_terminada, key_marcos)
        logger.info(f"[PIXELATION] {guid} → completado — marcos={key_marcos} terminada={key_terminada}")
        consumer_service.commit()

    except Exception as e:
        logger.error(f"[ERROR PIXELATION] procesando {guid}: {e}")
        if guid:
            db_service.update_estado_error(guid)
        consumer_service.commit()

consumer_service.close()
