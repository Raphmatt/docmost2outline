"""MIME type detection utilities."""

import mimetypes
from pathlib import Path
from typing import Any

# Try to import python-magic, fall back to mimetypes if not available
try:
    import magic

    MAGIC_AVAILABLE = True
except (ImportError, OSError):
    magic: Any = None  # type: ignore
    MAGIC_AVAILABLE = False


# Image MIME types that should be uploaded as images
# (From https://github.com/outline/outline/blob/main/shared/validations.ts)
IMAGE_MIME_TYPES = {
    "image/jpg",
    "image/jpeg",
    "image/pjpeg",
    "image/png",
    "image/apng",
    "image/avif",
    "image/gif",
    "image/webp",
    "image/svg",
    "image/svg+xml",
    "image/bmp",
    "image/tiff",
    "image/heic",
}


def get_mime_type(file_path: str) -> str:
    """Get MIME type for a file.

    Args:
        file_path: Path to the file

    Returns:
        MIME type string (e.g., 'image/png', 'application/pdf')
    """
    if MAGIC_AVAILABLE:
        try:
            return magic.from_file(file_path, mime=True)
        except Exception:
            pass

    # Fallback to mimetypes
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        return mime_type

    # Default fallback
    return "application/octet-stream"


def is_image(file_path: str) -> bool:
    """Check if file is an image based on MIME type."""
    mime_type = get_mime_type(file_path)
    return mime_type in IMAGE_MIME_TYPES


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    return Path(file_path).stat().st_size
