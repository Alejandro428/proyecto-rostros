import boto3
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, minio_conf: dict, public_url: str, bucket_raw: str, bucket_processed: str):
        self.public_url       = public_url.rstrip("/")
        self.bucket_raw       = bucket_raw
        self.bucket_processed = bucket_processed
        self.client = boto3.client("s3", **minio_conf)

    def presigned_url(self, bucket: str, key: str, expiry: int) -> str | None:
        if not key:
            return None
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry
            )
            # Reemplaza la URL interna de Docker por la pública
            internal = self.client.meta.endpoint_url
            return url.replace(internal, self.public_url)
        except Exception as e:
            logger.error(f"Error generando presigned URL para {key}: {e}")
            return None
