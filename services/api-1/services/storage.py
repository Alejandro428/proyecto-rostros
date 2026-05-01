import boto3
import logging
from io import BytesIO

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self, minio_conf: dict, bucket_raw: str):
        self.s3 = boto3.client("s3", **minio_conf)
        self.bucket_raw = bucket_raw
    
    async def init_buckets(self):
        """Crea buckets si no existen."""
        try:
            existing = [b["Name"] for b in self.s3.list_buckets()["Buckets"]]
            if self.bucket_raw not in existing:
                self.s3.create_bucket(Bucket=self.bucket_raw)
                logger.info(f"✅ Bucket creado: {self.bucket_raw}")
        except Exception as e:
            logger.error(f"Error inicializando buckets: {e}")
            raise
    
    async def upload(self, file_obj: BytesIO, s3_key: str, content_type: str):
        """Sube archivo a MinIO."""
        try:
            self.s3.upload_fileobj(
                file_obj,
                self.bucket_raw,
                s3_key,
                ExtraArgs={"ContentType": content_type}
            )
            logger.info(f"MinIO: Upload OK - {s3_key}")
        except Exception as e:
            logger.error(f"MinIO error: {e}")
            raise