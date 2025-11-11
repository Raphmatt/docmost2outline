"""Outline API client using httpx."""

import time
from typing import Any, Optional

import httpx
from pydantic import BaseModel


class OutlineCollection(BaseModel):
    """Outline collection model."""

    id: str
    name: str
    description: Optional[str] = None
    color: Optional[str] = None


class OutlineDocument(BaseModel):
    """Outline document model."""

    id: str
    title: str
    collectionId: str
    parentDocumentId: Optional[str] = None
    url: str


class OutlineAttachment(BaseModel):
    """Outline attachment model."""

    id: str
    url: str
    name: str
    size: int


class OutlineClient:
    """Client for interacting with Outline API."""

    def __init__(self, base_url: str, api_key: str):
        """Initialize the Outline client.

        Args:
            base_url: Base URL of Outline instance (e.g., https://outline.example.com)
            api_key: API key for authentication
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.client = httpx.Client(
            base_url=f"{self.base_url}/api",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=30.0,
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, *args):
        """Context manager exit."""
        self.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def test_connection(self) -> dict[str, Any]:
        """Test API connectivity.

        Returns:
            Auth info response

        Raises:
            httpx.HTTPError: If connection fails
        """
        response = self.client.post("/auth.info")
        response.raise_for_status()
        return response.json()

    def create_collection(
        self,
        name: str,
        description: Optional[str] = None,
        color: Optional[str] = None,
    ) -> OutlineCollection:
        """Create a new collection.

        Args:
            name: Collection name
            description: Optional description
            color: Optional hex color (e.g., "#4E5C6E")

        Returns:
            Created collection
        """
        payload: dict[str, Any] = {"name": name}
        if description:
            payload["description"] = description
        if color:
            payload["color"] = color

        response = self.client.post("/collections.create", json=payload)
        response.raise_for_status()
        data = response.json()
        return OutlineCollection(**data["data"])

    def get_collection(self, collection_id: str) -> OutlineCollection:
        """Get collection by ID.

        Args:
            collection_id: Collection ID

        Returns:
            Collection info
        """
        response = self.client.post(
            "/collections.info", json={"id": collection_id}
        )
        response.raise_for_status()
        data = response.json()
        return OutlineCollection(**data["data"])

    def create_document(
        self,
        title: str,
        text: str,
        collection_id: str,
        parent_document_id: Optional[str] = None,
        publish: bool = True,
    ) -> OutlineDocument:
        """Create a new document with automatic retry on rate limits.

        Args:
            title: Document title
            text: Markdown content
            collection_id: Parent collection ID
            parent_document_id: Optional parent document ID for nesting
            publish: Whether to publish immediately (default True)

        Returns:
            Created document
        """
        payload: dict[str, Any] = {
            "title": title,
            "text": text,
            "collectionId": collection_id,
            "publish": publish,
        }
        if parent_document_id:
            payload["parentDocumentId"] = parent_document_id

        max_retries = 3
        for attempt in range(max_retries):
            response = self.client.post("/documents.create", json=payload)

            # If we get 429 (rate limit), wait and retry
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    # Check Retry-After header (can be float or int)
                    retry_after = response.headers.get("Retry-After", "60")
                    wait_seconds = float(retry_after)
                    print(
                        f"  ⚠ Rate limited, waiting {wait_seconds:.1f} seconds..."
                    )
                    time.sleep(wait_seconds)
                    continue
                else:
                    # Last attempt, raise the error
                    response.raise_for_status()

            # Any other error or success
            response.raise_for_status()
            data = response.json()
            return OutlineDocument(**data["data"])

        # Should not reach here
        raise Exception("Max retries exceeded")

    def delete_document(
        self, document_id: str, permanent: bool = False
    ) -> None:
        """Delete a document.

        Args:
            document_id: Document ID to delete
            permanent: If True, permanently delete; otherwise move to trash
        """
        payload: dict[str, Any] = {"id": document_id}
        if permanent:
            payload["permanent"] = True

        response = self.client.post("/documents.delete", json=payload)
        response.raise_for_status()

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection (and all its documents).

        Args:
            collection_id: Collection ID to delete
        """
        response = self.client.post(
            "/collections.delete", json={"id": collection_id}
        )
        response.raise_for_status()

    def create_attachment(
        self,
        name: str,
        content_type: str,
        size: int,
        document_id: Optional[str] = None,
    ) -> tuple[str, dict[str, Any], OutlineAttachment]:
        """Create an attachment and get presigned upload URL with rate limit handling.

        Args:
            name: File name
            content_type: MIME type
            size: File size in bytes
            document_id: Optional document ID to attach to

        Returns:
            Tuple of (upload_url, form_data, attachment_info)
        """
        payload: dict[str, Any] = {
            "name": name,
            "contentType": content_type,
            "size": size,
            "preset": "documentAttachment",
        }
        if document_id:
            payload["documentId"] = document_id

        max_retries = 3
        for attempt in range(max_retries):
            response = self.client.post("/attachments.create", json=payload)

            # If we get 429 (rate limit), wait and retry
            if response.status_code == 429:
                if attempt < max_retries - 1:
                    retry_after = response.headers.get("Retry-After", "60")
                    wait_seconds = float(retry_after)
                    print(
                        f"  ⚠ Rate limited (attachments), waiting {wait_seconds:.1f} seconds..."
                    )
                    time.sleep(wait_seconds)
                    continue
                else:
                    response.raise_for_status()

            response.raise_for_status()
            data = response.json()["data"]

            upload_url = data["uploadUrl"]
            form_data = data.get("form", {})
            attachment = OutlineAttachment(**data["attachment"])

            return upload_url, form_data, attachment

        raise Exception("Max retries exceeded")

    def upload_file_to_storage(
        self,
        upload_url: str,
        form_data: dict[str, Any],
        file_path: str,
        content_type: str,
    ) -> None:
        """Upload file to presigned URL.

        Args:
            upload_url: Presigned upload URL
            form_data: Form fields for multipart upload
            file_path: Path to file to upload
            content_type: MIME type
        """
        with open(file_path, "rb") as f:
            file_content = f.read()

        # Create multipart form data
        files = {"file": (file_path.split("/")[-1], file_content, content_type)}

        # Use a separate client without auth headers for S3 upload
        with httpx.Client(timeout=60.0) as upload_client:
            response = upload_client.post(
                upload_url,
                data=form_data,
                files=files,
            )
            response.raise_for_status()
