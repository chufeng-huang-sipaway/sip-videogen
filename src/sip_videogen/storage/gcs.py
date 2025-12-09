"""Google Cloud Storage integration for sip-videogen.

This module provides GCS upload and download functionality for
reference images and video clips.
"""

import logging
from pathlib import Path

from google.cloud import storage
from google.cloud.exceptions import GoogleCloudError
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


class GCSStorageError(Exception):
    """Exception raised for GCS storage errors."""


class GCSStorage:
    """Google Cloud Storage client for uploading and downloading assets.

    Handles authentication via Application Default Credentials (ADC).
    Run `gcloud auth application-default login` to set up credentials.
    """

    def __init__(self, bucket_name: str):
        """Initialize GCS storage client.

        Args:
            bucket_name: Name of the GCS bucket to use.
        """
        self.client = storage.Client()
        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name
        logger.debug("Initialized GCS storage with bucket: %s", bucket_name)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def upload_file(self, local_path: Path, remote_path: str) -> str:
        """Upload a local file to GCS.

        Args:
            local_path: Path to the local file to upload.
            remote_path: Destination path in the bucket (e.g., "images/char_001.png").

        Returns:
            GCS URI of the uploaded file (gs://bucket/path).

        Raises:
            GCSStorageError: If the upload fails.
        """
        if not local_path.exists():
            raise GCSStorageError(f"Local file not found: {local_path}")

        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
            gcs_uri = f"gs://{self.bucket_name}/{remote_path}"
            logger.info("Uploaded %s to %s", local_path, gcs_uri)
            return gcs_uri
        except GoogleCloudError as e:
            raise GCSStorageError(f"Failed to upload {local_path} to GCS: {e}") from e

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def download_file(self, gcs_uri: str, local_path: Path) -> Path:
        """Download a file from GCS to local filesystem.

        Args:
            gcs_uri: GCS URI of the file (gs://bucket/path/file.ext).
            local_path: Local path to save the downloaded file.

        Returns:
            Path to the downloaded file.

        Raises:
            GCSStorageError: If the download fails or URI is invalid.
        """
        # Parse gs://bucket/path format
        if not gcs_uri.startswith("gs://"):
            raise GCSStorageError(f"Invalid GCS URI format: {gcs_uri}")

        try:
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                raise GCSStorageError(f"Invalid GCS URI format: {gcs_uri}")
            bucket_name, blob_path = parts[0], parts[1]

            # Create parent directory if needed
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download from the appropriate bucket
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_path)
            blob.download_to_filename(str(local_path))

            logger.info("Downloaded %s to %s", gcs_uri, local_path)
            return local_path
        except GoogleCloudError as e:
            raise GCSStorageError(f"Failed to download {gcs_uri}: {e}") from e

    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists in GCS.

        Args:
            remote_path: Path in the bucket to check.

        Returns:
            True if the file exists, False otherwise.
        """
        blob = self.bucket.blob(remote_path)
        return blob.exists()

    def delete_file(self, remote_path: str) -> bool:
        """Delete a file from GCS.

        Args:
            remote_path: Path in the bucket to delete.

        Returns:
            True if deleted, False if file didn't exist.
        """
        blob = self.bucket.blob(remote_path)
        if blob.exists():
            blob.delete()
            logger.info("Deleted gs://%s/%s", self.bucket_name, remote_path)
            return True
        return False

    def generate_remote_path(self, prefix: str, filename: str) -> str:
        """Generate a remote path with the given prefix.

        Args:
            prefix: Directory prefix (e.g., "reference_images", "video_clips").
            filename: Name of the file.

        Returns:
            Full remote path.
        """
        return f"{prefix}/{filename}"
