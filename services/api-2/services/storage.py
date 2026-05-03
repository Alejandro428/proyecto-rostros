import boto3
import logging

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self, minio_conf: dict, bucket_raw: str, bucket_processed: str):
        self.bucket_raw       = bucket_raw
        self.bucket_processed = bucket_processed
        self.client = boto3.client("s3", **minio_conf)

    def presigned_url(self, bucket: str, key: str, expiry: int, public_url: str) -> str | None:
        if not key:
            return None
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expiry
            )
            internal = self.client.meta.endpoint_url
            return url.replace(internal, public_url.rstrip("/"))
        except Exception as e:
            logger.error(f"Error generando presigned URL para {key}: {e}")
            return None
