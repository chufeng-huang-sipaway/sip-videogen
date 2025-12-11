"""Google Cloud Storage integration for sip-videogen.

This module provides GCS upload and download functionality for
reference images and video clips.
"""

import base64
import json
import logging
import os
from pathlib import Path

from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from google.cloud.exceptions import Forbidden, GoogleCloudError, NotFound
from google.oauth2 import service_account
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)


def _get_credentials_from_env():
    """Get GCS credentials from environment variable if available.

    Checks for GOOGLE_CLOUD_CREDENTIALS_JSON which should contain
    a base64-encoded service account JSON key.

    Returns:
        google.oauth2.service_account.Credentials or None
    """
    creds_b64 = os.environ.get("GOOGLE_CLOUD_CREDENTIALS_JSON")
    if not creds_b64:
        return None

    try:
        # Decode base64 to JSON string
        creds_json = base64.b64decode(creds_b64).decode("utf-8")
        # Parse JSON to dict
        creds_info = json.loads(creds_json)
        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        logger.debug("Using credentials from GOOGLE_CLOUD_CREDENTIALS_JSON")
        return credentials
    except (base64.binascii.Error, json.JSONDecodeError, ValueError) as e:
        logger.warning(f"Failed to parse GOOGLE_CLOUD_CREDENTIALS_JSON: {e}")
        return None


class GCSStorageError(Exception):
    """Exception raised for GCS storage errors."""


class GCSAuthenticationError(GCSStorageError):
    """Raised when GCS authentication fails."""


class GCSBucketNotFoundError(GCSStorageError):
    """Raised when the specified bucket does not exist."""


class GCSPermissionError(GCSStorageError):
    """Raised when permission is denied for a GCS operation."""


class GCSStorage:
    """Google Cloud Storage client for uploading and downloading assets.

    Supports multiple authentication methods (in order of priority):
    1. GOOGLE_CLOUD_CREDENTIALS_JSON env var (base64-encoded service account JSON)
    2. GOOGLE_APPLICATION_CREDENTIALS env var (path to service account JSON file)
    3. Application Default Credentials (ADC) from 'gcloud auth application-default login'
    """

    def __init__(self, bucket_name: str, verify_bucket: bool = True):
        """Initialize GCS storage client.

        Args:
            bucket_name: Name of the GCS bucket to use.
            verify_bucket: Whether to verify bucket exists on initialization.

        Raises:
            GCSAuthenticationError: If Google Cloud credentials are not configured.
            GCSBucketNotFoundError: If the specified bucket does not exist.
            GCSPermissionError: If access to the bucket is denied.
        """
        try:
            # First, try to get credentials from inline env var
            credentials = _get_credentials_from_env()

            if credentials:
                # Use inline credentials
                self.client = storage.Client(credentials=credentials)
                logger.debug("Using inline credentials from GOOGLE_CLOUD_CREDENTIALS_JSON")
            else:
                # Fall back to default credentials (ADC or GOOGLE_APPLICATION_CREDENTIALS)
                self.client = storage.Client()
                logger.debug("Using default credentials (ADC)")

        except DefaultCredentialsError as e:
            raise GCSAuthenticationError(
                "Google Cloud credentials not configured.\n\n"
                "Choose one of these options:\n"
                "  1. Add GOOGLE_CLOUD_CREDENTIALS_JSON to your .env file (recommended)\n"
                "     - Get this from: Google Cloud Console > IAM > Service Accounts\n"
                "     - Create a key, then run: base64 -i your-key.json\n"
                "     - Paste the result as GOOGLE_CLOUD_CREDENTIALS_JSON=...\n\n"
                "  2. Run: gcloud auth application-default login"
            ) from e

        self.bucket = self.client.bucket(bucket_name)
        self.bucket_name = bucket_name

        if verify_bucket:
            self._verify_bucket_access()

        logger.debug("Initialized GCS storage with bucket: %s", bucket_name)

    def _verify_bucket_access(self) -> None:
        """Verify that the bucket exists and is accessible.

        Raises:
            GCSBucketNotFoundError: If the bucket does not exist.
            GCSPermissionError: If access to the bucket is denied.
        """
        try:
            # Try to get bucket metadata to verify access
            self.bucket.reload()
        except NotFound:
            raise GCSBucketNotFoundError(
                f"Bucket '{self.bucket_name}' not found.\n"
                f"Create it with: gsutil mb -l us-central1 gs://{self.bucket_name}"
            )
        except Forbidden:
            raise GCSPermissionError(
                f"Permission denied for bucket '{self.bucket_name}'.\n"
                "Ensure your account has 'Storage Object Admin' role on the bucket."
            )
        except GoogleCloudError as e:
            raise GCSStorageError(f"Failed to access bucket: {e}") from e

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
            GCSStorageError: If the local file is not found.
            GCSPermissionError: If permission is denied.
            GCSStorageError: If the upload fails for other reasons.
        """
        if not local_path.exists():
            raise GCSStorageError(f"Local file not found: {local_path}")

        try:
            blob = self.bucket.blob(remote_path)
            blob.upload_from_filename(str(local_path))
            gcs_uri = f"gs://{self.bucket_name}/{remote_path}"
            logger.info("Uploaded %s to %s", local_path, gcs_uri)
            return gcs_uri
        except Forbidden as e:
            raise GCSPermissionError(
                f"Permission denied uploading to gs://{self.bucket_name}/{remote_path}.\n"
                "Ensure your account has 'Storage Object Admin' role."
            ) from e
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
            GCSStorageError: If the URI format is invalid.
            GCSBucketNotFoundError: If the file does not exist.
            GCSPermissionError: If permission is denied.
            GCSStorageError: If the download fails for other reasons.
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
        except NotFound as e:
            raise GCSBucketNotFoundError(
                f"File not found: {gcs_uri}. It may have been deleted or not generated."
            ) from e
        except Forbidden as e:
            raise GCSPermissionError(
                f"Permission denied downloading {gcs_uri}.\n"
                "Ensure your account has 'Storage Object Viewer' role."
            ) from e
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

    def generate_signed_url(
        self,
        gcs_uri: str,
        expiration_minutes: int = 60,
    ) -> str:
        """Generate a signed HTTPS URL for a GCS object.

        This allows external services (like Kling AI) to access GCS objects
        without authentication, using a time-limited signed URL.

        Args:
            gcs_uri: GCS URI of the file (gs://bucket/path/file.ext).
            expiration_minutes: URL expiration time in minutes (default: 60).

        Returns:
            Signed HTTPS URL that can be accessed without authentication.

        Raises:
            GCSStorageError: If the URI format is invalid.
            GCSPermissionError: If signing fails due to permissions.
        """
        from datetime import timedelta

        if not gcs_uri.startswith("gs://"):
            raise GCSStorageError(f"Invalid GCS URI format: {gcs_uri}")

        try:
            parts = gcs_uri.replace("gs://", "").split("/", 1)
            if len(parts) != 2:
                raise GCSStorageError(f"Invalid GCS URI format: {gcs_uri}")

            bucket_name, blob_path = parts[0], parts[1]

            # Get the bucket and blob
            bucket = self.client.bucket(bucket_name)
            blob = bucket.blob(blob_path)

            # Generate signed URL
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET",
            )

            logger.debug("Generated signed URL for %s (expires in %d min)", gcs_uri, expiration_minutes)
            return url

        except Forbidden as e:
            raise GCSPermissionError(
                f"Permission denied generating signed URL for {gcs_uri}.\n"
                "Ensure your service account has 'Service Account Token Creator' role."
            ) from e
        except GoogleCloudError as e:
            raise GCSStorageError(f"Failed to generate signed URL for {gcs_uri}: {e}") from e
