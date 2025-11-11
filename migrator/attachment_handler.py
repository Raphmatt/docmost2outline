"""Attachment upload handler for Outline."""

from pathlib import Path
from typing import Dict, Tuple

from migrator.outline_client import OutlineClient
from utils.mime_detector import get_file_size, get_mime_type


class AttachmentHandler:
    """Handle attachment uploads to Outline."""

    def __init__(self, client: OutlineClient):
        """Initialize handler.

        Args:
            client: Outline API client
        """
        self.client = client

    def upload_attachment(
        self, file_path: Path, intended_name: str | None = None
    ) -> Tuple[str, int]:
        """Upload an attachment and return its Outline URL and file size.

        Args:
            file_path: Path to attachment file
            intended_name: The intended filename (from markdown reference), overrides actual filename

        Returns:
            Tuple of (Outline URL, file size in bytes)

        Raises:
            Exception: If upload fails
        """
        # Get file metadata
        file_name = intended_name if intended_name else file_path.name
        content_type = get_mime_type(str(file_path))
        file_size = get_file_size(str(file_path))

        # Step 1: Create attachment in Outline
        upload_url, form_data, attachment_info = self.client.create_attachment(
            name=file_name,
            content_type=content_type,
            size=file_size,
        )

        # Step 2: Upload file to storage
        self.client.upload_file_to_storage(
            upload_url=upload_url,
            form_data=form_data,
            file_path=str(file_path),
            content_type=content_type,
        )

        # Return the URL and file size
        return attachment_info.url, file_size

    def upload_attachments_for_references(
        self, ref_paths: list[str], attachments_dir: Path
    ) -> Dict[str, Tuple[str, int]]:
        """Upload multiple attachments and build URL mapping.

        Args:
            ref_paths: List of attachment reference paths from markdown
            attachments_dir: Root directory containing attachment files

        Returns:
            Dictionary mapping docmost_path -> (outline_url, file_size_bytes)

        Raises:
            FileNotFoundError: If attachment file not found
            Exception: If upload fails
        """
        url_mapping: Dict[str, Tuple[str, int]] = {}

        for ref_path in ref_paths:
            # Resolve to actual file path
            # ref_path is like "files/uuid/filename"
            # attachments_dir is the root directory of the export
            clean_path = ref_path.lstrip("/")

            # Extract intended filename from the reference path
            intended_name = Path(clean_path).name

            # Try multiple search strategies
            full_path = None

            # Strategy 1: Direct path from attachments_dir
            candidate = attachments_dir / clean_path
            if candidate.exists():
                full_path = candidate

            # Strategy 2: Search in all subdirectories for the files/uuid pattern
            if not full_path:
                path_parts = Path(clean_path).parts
                if len(path_parts) >= 2:  # files/uuid or files/uuid/filename
                    uuid = path_parts[1] if len(path_parts) >= 2 else None
                    if uuid:
                        # Search for this UUID directory anywhere in the export
                        for files_dir in attachments_dir.rglob("files"):
                            uuid_dir = files_dir / uuid
                            if uuid_dir.exists() and uuid_dir.is_dir():
                                files_in_dir = list(uuid_dir.glob("*"))
                                if files_in_dir:
                                    full_path = files_in_dir[0]
                                    break

            if not full_path:
                raise FileNotFoundError(
                    f"Attachment not found: {ref_path} (searched in {attachments_dir})"
                )

            # Upload and get Outline URL and file size, using the intended filename from markdown
            outline_url, file_size = self.upload_attachment(
                full_path, intended_name=intended_name
            )

            # Store mapping with file size
            url_mapping[ref_path] = (outline_url, file_size)

        return url_mapping
