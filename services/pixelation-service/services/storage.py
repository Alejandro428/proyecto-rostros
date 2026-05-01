import boto3
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, minio_conf: dict, bucket_raw: str, bucket_processed: str):
        self.bucket_raw       = bucket_raw
        self.bucket_processed = bucket_processed
        self.client = boto3.client("s3", **minio_conf)
        self._ensure_bucket(bucket_processed)

    def _ensure_bucket(self, bucket: str):
        try:
            self.client.head_bucket(Bucket=bucket)
        except Exception:
            self.client.create_bucket(Bucket=bucket)
            logger.info(f"MinIO: bucket '{bucket}' creado")

    def download_image(self, s3_key: str) -> np.ndarray:
        obj = self.client.get_object(Bucket=self.bucket_raw, Key=s3_key)
        data = np.frombuffer(obj["Body"].read(), np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"No se pudo decodificar la imagen: {s3_key}")
        return img

    def upload_image(self, img: np.ndarray, s3_key: str) -> str:
        _, buf = cv2.imencode(".jpg", img)
        self.client.put_object(
            Bucket=self.bucket_processed,
            Key=s3_key,
            Body=buf.tobytes(),
            ContentType="image/jpeg"
        )
        logger.info(f"MinIO: imagen subida - {s3_key}")
        return s3_key
