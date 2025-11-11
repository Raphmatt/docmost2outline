"""Docmost ZIP export parser."""

import shutil
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class DocmostPage:
    """Represents a Docmost page/document."""

    title: str
    file_path: Path  # Path to .md file in extracted ZIP
    content: str
    parent_path: Optional[Path] = None  # Parent directory path
    children: List["DocmostPage"] = field(default_factory=list)
    level: int = 0  # Hierarchy level (0 = root)
    outline_id: Optional[str] = None  # Set after creation in Outline


@dataclass
class DocmostExport:
    """Represents parsed Docmost export."""

    space_name: str
    root_pages: List[DocmostPage]
    all_pages: List[DocmostPage]
    attachments_dir: Optional[Path]
    temp_dir: Path


class DocmostParser:
    """Parser for Docmost ZIP exports."""

    def __init__(self, zip_path: str):
        """Initialize parser.

        Args:
            zip_path: Path to Docmost export ZIP file
        """
        self.zip_path = Path(zip_path)
        if not self.zip_path.exists():
            raise FileNotFoundError(f"ZIP file not found: {zip_path}")

    def parse(self) -> DocmostExport:
        """Parse the Docmost export ZIP.

        Returns:
            DocmostExport with all parsed data

        Raises:
            zipfile.BadZipFile: If ZIP is invalid
        """
        # Create temporary directory for extraction
        temp_dir = Path(tempfile.mkdtemp(prefix="docmost_export_"))

        try:
            # Extract ZIP
            with zipfile.ZipFile(self.zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            # Determine root directory and space name
            # Check if ZIP has a single top-level directory (old Docmost format)
            # or multiple items at root (new format)
            items = list(temp_dir.iterdir())
            dirs = [d for d in items if d.is_dir()]
            files = [f for f in items if f.is_file()]

            if len(dirs) == 1 and len(files) == 0:
                # Single top-level directory - use that as root
                root_dir = dirs[0]
                space_name = root_dir.name
            else:
                # Multiple items at root - use temp_dir as root
                root_dir = temp_dir
                # Use ZIP filename (without extension) as space name
                space_name = self.zip_path.stem

            # Find attachments directory (could be at root or in subdirectories)
            # For now, just check if there's a files directory at root
            # Individual attachment resolution will search subdirectories as needed
            attachments_dir = root_dir
            # We'll search for files/uuid/filename pattern during attachment resolution

            # Parse all markdown files
            all_pages = []
            md_files = list(root_dir.rglob("*.md"))

            # Build page objects
            page_by_path: Dict[Path, DocmostPage] = {}

            for md_file in md_files:
                # Skip files in attachments directory (any "files" folder)
                if any(parent.name == "files" for parent in md_file.parents):
                    continue

                # Read content
                content = md_file.read_text(encoding="utf-8")

                # Determine title from filename
                title = md_file.stem

                # Determine parent path
                parent_path = (
                    md_file.parent if md_file.parent != root_dir else None
                )

                # Calculate hierarchy level
                relative_path = md_file.relative_to(root_dir)
                level = len(relative_path.parents) - 1

                page = DocmostPage(
                    title=title,
                    file_path=md_file,
                    content=content,
                    parent_path=parent_path,
                    level=level,
                )

                all_pages.append(page)
                page_by_path[md_file] = page

            # Build hierarchy tree
            root_pages = []
            for page in all_pages:
                if page.level == 0:
                    # Root level page
                    root_pages.append(page)
                else:
                    # Find parent (page in parent directory with same name)
                    parent_dir = page.file_path.parent
                    parent_md = parent_dir.with_suffix(".md")

                    if parent_md in page_by_path:
                        parent_page = page_by_path[parent_md]
                        parent_page.children.append(page)

            # Sort pages by level for breadth-first processing
            all_pages.sort(key=lambda p: (p.level, p.title))

            return DocmostExport(
                space_name=space_name,
                root_pages=root_pages,
                all_pages=all_pages,
                attachments_dir=attachments_dir,
                temp_dir=temp_dir,
            )

        except Exception:
            # Cleanup on error
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise

    @staticmethod
    def cleanup(export: DocmostExport) -> None:
        """Clean up temporary directory.

        Args:
            export: DocmostExport to clean up
        """
        if export.temp_dir.exists():
            shutil.rmtree(export.temp_dir, ignore_errors=True)

    @staticmethod
    def find_attachments(export: DocmostExport) -> List[Path]:
        """Find all attachment files in export.

        Args:
            export: Parsed export

        Returns:
            List of attachment file paths
        """
        if not export.attachments_dir or not export.attachments_dir.exists():
            return []

        attachments = []
        # Search for all files inside "files" directories
        for files_dir in export.attachments_dir.rglob("files"):
            if files_dir.is_dir():
                for file_path in files_dir.rglob("*"):
                    if file_path.is_file():
                        attachments.append(file_path)

        return attachments
