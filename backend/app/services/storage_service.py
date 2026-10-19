"""
S3 storage service for audio files and Kinnser screenshots.
All uploads use SSE-KMS server-side encryption.
"""

import logging
from typing import Optional

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3StorageService:
    """
    Manages S3 uploads and presigned URL generation for NoteFlow assets.

    All objects are stored with SSE-KMS encryption.
    """

    def __init__(self) -> None:
        self._client = None

    def _get_client(self):
        if self._client is None:
            self._client = boto3.client(
                "s3",
                region_name=settings.S3_REGION,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            )
        return self._client

    async def upload_audio(self, file_bytes: bytes, note_id: str) -> str:
        """
        Upload audio bytes to S3 under the audio/ prefix.

        Returns the S3 object URL (not presigned – use get_presigned_url for access).
        """
        import asyncio

        s3_key = f"audio/{note_id}/recording.bin"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._get_client().put_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key,
                Body=file_bytes,
                ServerSideEncryption="aws:kms",
                ContentType="application/octet-stream",
                Metadata={"note_id": note_id},
            ),
        )
        url = f"s3://{settings.S3_BUCKET}/{s3_key}"
        logger.info("Audio uploaded: %s", url)
        return url

    async def upload_screenshot(self, file_bytes: bytes, note_id: str) -> str:
        """
        Upload a Kinnser screenshot to S3 under the screenshots/ prefix.

        Returns the S3 object URL.
        """
        import asyncio

        s3_key = f"screenshots/{note_id}/submission.png"
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(
            None,
            lambda: self._get_client().put_object(
                Bucket=settings.S3_BUCKET,
                Key=s3_key,
                Body=file_bytes,
                ServerSideEncryption="aws:kms",
                ContentType="image/png",
                Metadata={"note_id": note_id},
            ),
        )
        url = f"s3://{settings.S3_BUCKET}/{s3_key}"
        logger.info("Screenshot uploaded: %s", url)
        return url

    async def get_presigned_url(self, s3_key: str, expires_in: int = 3600) -> str:
        """
        Generate a presigned GET URL for the given S3 key.

        Strips the s3://bucket/ prefix if a full S3 URL is passed.
        Expires in *expires_in* seconds (default 1 hour).
        """
        import asyncio

        # Normalize: strip s3://bucket/ prefix if present
        prefix = f"s3://{settings.S3_BUCKET}/"
        if s3_key.startswith(prefix):
            s3_key = s3_key[len(prefix):]

        loop = asyncio.get_running_loop()
        url = await loop.run_in_executor(
            None,
            lambda: self._get_client().generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET, "Key": s3_key},
                ExpiresIn=expires_in,
            ),
        )
        return url

    async def get_object(self, s3_key: str) -> bytes:
        """
        Download and return the bytes for an S3 object.
        Accepts both raw keys and full s3:// URLs.
        """
        import asyncio

        prefix = f"s3://{settings.S3_BUCKET}/"
        if s3_key.startswith(prefix):
            s3_key = s3_key[len(prefix):]

        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None,
            lambda: self._get_client().get_object(Bucket=settings.S3_BUCKET, Key=s3_key),
        )
        body = response["Body"].read()
        return body
