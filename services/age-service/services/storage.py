import boto3
import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, minio_conf: dict, bucket: str):
        self.bucket = bucket
        self.client = boto3.client("s3", **minio_conf)

    def download_image(self, s3_key: str) -> np.ndarray:
        obj = self.client.get_object(Bucket=self.bucket, Key=s3_key)
        data = np.frombuffer(obj["Body"].read(), np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"No se pudo decodificar la imagen: {s3_key}")
        return img
