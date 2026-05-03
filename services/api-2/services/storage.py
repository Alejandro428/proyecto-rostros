import boto3
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, public_endpoint: str, access_key: str, secret_key: str, bucket_raw: str, bucket_processed: str):
        self.bucket_raw       = bucket_raw
        self.bucket_processed = bucket_processed
        # api-2 sólo genera presigned URLs: no sube ni descarga objetos directamente.
        # El cliente usa el endpoint público para que la firma lleve el host que verá el navegador.
        self.client = boto3.client(
            "s3",
            endpoint_url=public_endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def presigned_url(self, bucket: str, key: str, expiry: int) -> str | None:
        if not key:
            return None
        try:
            return self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry
            )
        except Exception as e:
            logger.error(f"Error generando presigned URL para {key}: {e}")
            return None
