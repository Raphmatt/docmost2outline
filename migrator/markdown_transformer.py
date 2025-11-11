"""Markdown content transformation utilities."""

import re
from pathlib import Path
from typing import Dict, List, Tuple


class MarkdownTransformer:
    """Transform Docmost markdown for Outline compatibility."""

    @staticmethod
    def extract_attachment_references(content: str) -> List[str]:
        """Extract all attachment references from markdown.

        Args:
            content: Markdown content

        Returns:
            List of attachment paths (e.g., ['files/uuid/image.png'])
        """
        # Match both image syntax ![...](path) and link syntax [...](...path)
        # Matches: files/uuid/filename or //files/uuid/filename
        pattern = r"!?\[[^\]]*\]\((/?/?files/[^)]+)\)"
        matches = re.findall(pattern, content)

        # Clean up paths (remove leading slashes)
        return [path.lstrip("/") for path in matches]

    @staticmethod
    def replace_attachment_urls(
        content: str, url_mapping: Dict[str, Tuple[str, int]]
    ) -> str:
        """Replace Docmost attachment paths with Outline URLs.

        Args:
            content: Original markdown content
            url_mapping: Map of docmost_path -> (outline_url, file_size_bytes)

        Returns:
            Transformed markdown
        """
        result = content

        for docmost_path, (outline_url, file_size) in url_mapping.items():
            # Handle both with and without leading slashes
            patterns = [
                docmost_path,
                f"/{docmost_path}",
                f"//{docmost_path}",
            ]

            for pattern in patterns:
                # Escape special regex characters in path
                escaped_pattern = re.escape(pattern)

                # For images, keep the alt text and just replace URL
                # Pattern: ![alt text](path)
                result = re.sub(
                    f"!\\[([^\\]]*)\\]\\({escaped_pattern}\\)",
                    f"![\\1]({outline_url})",
                    result,
                )

                # For file links, extract filename and add file size
                # Pattern: [filename](path) -> [filename filesize](url)
                def replace_link(match):
                    link_text = match.group(1).strip()  # Remove any spaces
                    # Extract just the filename from the link text if it contains path
                    filename = (
                        Path(link_text).name if "/" in link_text else link_text
                    )
                    return f"[{filename} {file_size}]({outline_url})"

                result = re.sub(
                    f"\\[([^\\]]*)\\]\\({escaped_pattern}\\)",
                    replace_link,
                    result,
                )

        return result

    @staticmethod
    def convert_details_to_headings(content: str) -> str:
        """Convert HTML <details> tags to headings.

        Converts:
            <details>
            <summary>Title</summary>
            Content here
            </details>

        To:
            ### Title

            Content here

        Args:
            content: Original markdown content

        Returns:
            Transformed markdown
        """
        # Pattern to match details blocks with nested content
        # This handles multiline content between tags
        pattern = r"<details>\s*<summary>([^<]+)</summary>\s*(.*?)</details>"

        def replace_details(match):
            title = match.group(1).strip()
            inner_content = match.group(2).strip()
            return f"### {title}\n\n{inner_content}"

        # Use DOTALL flag to match across newlines
        result = re.sub(
            pattern, replace_details, content, flags=re.DOTALL | re.IGNORECASE
        )

        return result

    @staticmethod
    def transform_content(
        content: str, url_mapping: Dict[str, Tuple[str, int]]
    ) -> str:
        """Apply all transformations to markdown content.

        Args:
            content: Original Docmost markdown
            url_mapping: Attachment URL mappings (path -> (url, size))

        Returns:
            Transformed markdown ready for Outline
        """
        # Step 1: Convert details tags to headings
        result = MarkdownTransformer.convert_details_to_headings(content)

        # Step 2: Replace attachment URLs
        result = MarkdownTransformer.replace_attachment_urls(
            result, url_mapping
        )

        return result

    @staticmethod
    def resolve_attachment_path(ref_path: str, attachments_dir: Path) -> Path:
        """Resolve attachment reference to actual file path.

        Args:
            ref_path: Reference path from markdown (e.g., 'files/uuid/image.png')
            attachments_dir: Root attachments directory

        Returns:
            Full path to attachment file
        """
        # Remove any leading slashes
        clean_path = ref_path.lstrip("/")

        # Construct full path
        full_path = attachments_dir.parent / clean_path

        return full_path
