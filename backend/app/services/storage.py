"""
Storage service for file management.
Provides abstraction for local filesystem storage with hooks for S3/Minio.
"""

import os
import shutil
import hashlib
from pathlib import Path
from typing import BinaryIO, Optional
from abc import ABC, abstractmethod

from app.core.config import settings
import structlog

logger = structlog.get_logger()


class StorageBackend(ABC):
    """Abstract base class for storage backends."""

    @abstractmethod
    def save(self, file_data: BinaryIO, file_path: str) -> str:
        """Save a file and return the storage path."""
        pass

    @abstractmethod
    def load(self, file_path: str) -> BinaryIO:
        """Load a file and return file object."""
        pass

    @abstractmethod
    def delete(self, file_path: str) -> bool:
        """Delete a file."""
        pass

    @abstractmethod
    def exists(self, file_path: str) -> bool:
        """Check if file exists."""
        pass

    @abstractmethod
    def get_full_path(self, file_path: str) -> str:
        """Get full filesystem path."""
        pass


class LocalFileSystemStorage(StorageBackend):
    """Local filesystem storage backend."""

    def __init__(self, base_path: str = None):
        """
        Initialize local storage.

        Args:
            base_path: Base directory for file storage
        """
        self.base_path = Path(base_path or settings.STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_full_path(self, file_path: str) -> Path:
        """Get full path for a file."""
        return self.base_path / file_path

    def save(self, file_data: BinaryIO, file_path: str) -> str:
        """
        Save a file to local filesystem.

        Args:
            file_data: File data as binary stream
            file_path: Relative path where file should be saved

        Returns:
            Stored file path

        Raises:
            IOError: If file save fails
        """
        full_path = self._get_full_path(file_path)
        full_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(full_path, 'wb') as f:
                shutil.copyfileobj(file_data, f)

            logger.info("file_saved", path=file_path, full_path=str(full_path))
            return file_path

        except Exception as e:
            logger.error("file_save_failed", path=file_path, error=str(e))
            raise IOError(f"Failed to save file: {e}")

    def load(self, file_path: str) -> BinaryIO:
        """
        Load a file from local filesystem.

        Args:
            file_path: Relative path to file

        Returns:
            File object

        Raises:
            FileNotFoundError: If file doesn't exist
        """
        full_path = self._get_full_path(file_path)

        if not full_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        return open(full_path, 'rb')

    def delete(self, file_path: str) -> bool:
        """
        Delete a file from local filesystem.

        Args:
            file_path: Relative path to file

        Returns:
            True if deleted successfully
        """
        full_path = self._get_full_path(file_path)

        try:
            if full_path.exists():
                full_path.unlink()
                logger.info("file_deleted", path=file_path)
                return True
            return False

        except Exception as e:
            logger.error("file_delete_failed", path=file_path, error=str(e))
            return False

    def exists(self, file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Relative path to file

        Returns:
            True if file exists
        """
        return self._get_full_path(file_path).exists()

    def get_full_path(self, file_path: str) -> str:
        """
        Get full filesystem path.

        Args:
            file_path: Relative path to file

        Returns:
            Full filesystem path
        """
        return str(self._get_full_path(file_path))


class S3Storage(StorageBackend):
    """S3/Minio storage backend (placeholder for future implementation)."""

    def __init__(self, bucket: str, endpoint: str = None):
        """
        Initialize S3 storage.

        Args:
            bucket: S3 bucket name
            endpoint: Optional S3 endpoint (for Minio)
        """
        self.bucket = bucket
        self.endpoint = endpoint
        # TODO: Initialize boto3 client

    def save(self, file_data: BinaryIO, file_path: str) -> str:
        """Save file to S3."""
        raise NotImplementedError("S3 storage not yet implemented")

    def load(self, file_path: str) -> BinaryIO:
        """Load file from S3."""
        raise NotImplementedError("S3 storage not yet implemented")

    def delete(self, file_path: str) -> bool:
        """Delete file from S3."""
        raise NotImplementedError("S3 storage not yet implemented")

    def exists(self, file_path: str) -> bool:
        """Check if file exists in S3."""
        raise NotImplementedError("S3 storage not yet implemented")

    def get_full_path(self, file_path: str) -> str:
        """Get S3 URI."""
        return f"s3://{self.bucket}/{file_path}"


class StorageService:
    """
    High-level storage service with file management utilities.
    """

    def __init__(self, backend: StorageBackend = None):
        """
        Initialize storage service.

        Args:
            backend: Storage backend to use (defaults to local filesystem)
        """
        self.backend = backend or LocalFileSystemStorage()

    @property
    def storage_root(self) -> Path:
        """
        Get storage root path (backward compatibility).

        Returns:
            Base storage path from backend
        """
        if hasattr(self.backend, 'base_path'):
            return self.backend.base_path
        raise AttributeError("Backend does not have a base_path attribute")

    def save_upload(
        self,
        file_data: BinaryIO,
        tenant_id: int,
        document_id: int,
        filename: str,
        category: str = "documents"
    ) -> tuple[str, str]:
        """
        Save an uploaded file with organized directory structure.

        Args:
            file_data: File data as binary stream
            tenant_id: Tenant ID
            document_id: Document ID
            filename: Original filename
            category: File category (documents, images, exports)

        Returns:
            Tuple of (file_path, checksum)
        """
        # Generate organized path: tenants/{tenant_id}/{category}/{document_id}/filename
        file_path = f"tenants/{tenant_id}/{category}/{document_id}/{filename}"

        # Calculate checksum
        file_data.seek(0)
        checksum = self._calculate_checksum(file_data)
        file_data.seek(0)

        # Save file
        self.backend.save(file_data, file_path)

        return file_path, checksum

    def save_processed(
        self,
        file_data: BinaryIO,
        tenant_id: int,
        document_id: int,
        filename: str,
        kind: str
    ) -> tuple[str, str]:
        """
        Save a processed file (OCR result, searchable PDF, etc.).

        Args:
            file_data: File data as binary stream
            tenant_id: Tenant ID
            document_id: Document ID
            filename: Filename
            kind: File kind (ocr_json, searchable_pdf, etc.)

        Returns:
            Tuple of (file_path, checksum)
        """
        # Generate path: tenants/{tenant_id}/processed/{kind}/{document_id}/filename
        file_path = f"tenants/{tenant_id}/processed/{kind}/{document_id}/{filename}"

        # Calculate checksum
        file_data.seek(0)
        checksum = self._calculate_checksum(file_data)
        file_data.seek(0)

        # Save file
        self.backend.save(file_data, file_path)

        return file_path, checksum

    def load(self, file_path: str) -> BinaryIO:
        """
        Load a file.

        Args:
            file_path: Path to file

        Returns:
            File object
        """
        return self.backend.load(file_path)

    def delete(self, file_path: str) -> bool:
        """
        Delete a file.

        Args:
            file_path: Path to file

        Returns:
            True if deleted successfully
        """
        return self.backend.delete(file_path)

    def exists(self, file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to file

        Returns:
            True if file exists
        """
        return self.backend.exists(file_path)

    def get_full_path(self, file_path: str) -> str:
        """
        Get full path to file.

        Args:
            file_path: Relative path to file

        Returns:
            Full path
        """
        return self.backend.get_full_path(file_path)

    @staticmethod
    def _calculate_checksum(file_data: BinaryIO) -> str:
        """
        Calculate SHA-256 checksum of file.

        Args:
            file_data: File data as binary stream

        Returns:
            Hexadecimal checksum
        """
        sha256 = hashlib.sha256()
        for chunk in iter(lambda: file_data.read(8192), b''):
            sha256.update(chunk)
        return sha256.hexdigest()


# Global storage service instance
storage_service = StorageService()
