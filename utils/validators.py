"""Validation utilities."""

from pathlib import Path
from typing import List, Tuple


class ValidationError(Exception):
    """Validation error exception."""

    pass


def validate_file_size(file_path: str, max_size: int) -> None:
    """Validate that file is under size limit.

    Args:
        file_path: Path to file
        max_size: Maximum size in bytes

    Raises:
        ValidationError: If file exceeds size limit
    """
    size = Path(file_path).stat().st_size
    if size > max_size:
        size_mb = size / (1024 * 1024)
        max_mb = max_size / (1024 * 1024)
        raise ValidationError(
            f"File {Path(file_path).name} ({size_mb:.2f}MB) exceeds "
            f"maximum upload size ({max_mb:.2f}MB)"
        )


def validate_all_attachments(
    attachment_paths: List[str], max_size: int
) -> Tuple[int, int]:
    """Validate all attachment file sizes.

    Args:
        attachment_paths: List of attachment file paths
        max_size: Maximum size in bytes per file

    Returns:
        Tuple of (total_files, total_size_bytes)

    Raises:
        ValidationError: If any file exceeds size limit
    """
    total_size = 0
    total_files = 0

    for path in attachment_paths:
        if not Path(path).exists():
            raise ValidationError(f"Attachment file not found: {path}")

        validate_file_size(path, max_size)
        total_size += Path(path).stat().st_size
        total_files += 1

    return total_files, total_size


def format_bytes(bytes: int) -> str:
    """Format bytes as human-readable string.

    Args:
        bytes: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    value = float(bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} TB"
