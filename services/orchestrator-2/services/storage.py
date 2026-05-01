import boto3
import numpy as np
import cv2
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, minio_conf: dict, bucket_raw: str):
        self.s3 = boto3.client("s3", **minio_conf)
        self.bucket_raw = bucket_raw

    def download_image(self, s3_key: str):
        """Descarga imagen de MinIO y la decodifica. Retorna np.ndarray."""
        obj = self.s3.get_object(Bucket=self.bucket_raw, Key=s3_key)
        img_bytes = obj["Body"].read()
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"No se pudo decodificar la imagen: {s3_key}")
        logger.info(f"MinIO: imagen descargada - {s3_key}")
        return img

    def upload_crop(self, crop: np.ndarray, s3_key: str):
        """Codifica crop como JPEG y lo sube a MinIO."""
        _, buffer = cv2.imencode(".jpg", crop)
        self.s3.put_object(
            Bucket=self.bucket_raw,
            Key=s3_key,
            Body=buffer.tobytes(),
            ContentType="image/jpeg"
        )
        logger.info(f"MinIO: crop subido - {s3_key}")
