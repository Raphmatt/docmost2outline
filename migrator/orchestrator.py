"""Main migration orchestrator."""

from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from migrator.attachment_handler import AttachmentHandler
from migrator.docmost_parser import DocmostParser
from migrator.markdown_transformer import MarkdownTransformer
from migrator.outline_client import OutlineClient
from utils.validators import (
    format_bytes,
    validate_all_attachments,
)


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.documents_created = 0
        self.attachments_uploaded = 0
        self.total_attachment_size = 0

    def __str__(self):
        return (
            f"Documents created: {self.documents_created}\n"
            f"Attachments uploaded: {self.attachments_uploaded}\n"
            f"Total attachment size: {format_bytes(self.total_attachment_size)}"
        )


class MigrationOrchestrator:
    """Orchestrate the migration from Docmost to Outline."""

    def __init__(
        self,
        outline_client: OutlineClient,
        max_file_size: int,
        console: Optional[Console] = None,
    ):
        """Initialize orchestrator.

        Args:
            outline_client: Outline API client
            max_file_size: Maximum file size in bytes
            console: Rich console for output (optional)
        """
        self.client = outline_client
        self.max_file_size = max_file_size
        self.console = console or Console()
        self.attachment_handler = AttachmentHandler(outline_client)
        self.stats = MigrationStats()

    def migrate(
        self, zip_path: str, collection_id: Optional[str] = None
    ) -> tuple[str, MigrationStats]:
        """Perform the complete migration.

        Args:
            zip_path: Path to Docmost export ZIP
            collection_id: Optional existing collection ID

        Returns:
            Tuple of (collection_id, stats)

        Raises:
            ValidationError: If validation fails
            Exception: If migration fails
        """
        self.console.print(
            f"[bold blue]Starting migration from {zip_path}[/bold blue]"
        )

        # Step 1: Parse Docmost export
        self.console.print(
            "\n[yellow]Step 1:[/yellow] Parsing Docmost export..."
        )
        parser = DocmostParser(zip_path)
        export = parser.parse()
        self.console.print(f"  ✓ Found {len(export.all_pages)} documents")

        try:
            # Step 2: Pre-flight validation
            self.console.print(
                "\n[yellow]Step 2:[/yellow] Validating attachments..."
            )
            attachment_files = parser.find_attachments(export)
            if attachment_files:
                total_files, total_size = validate_all_attachments(
                    [str(f) for f in attachment_files], self.max_file_size
                )
                self.console.print(
                    f"  ✓ Validated {total_files} attachments "
                    f"({format_bytes(total_size)} total)"
                )
            else:
                self.console.print("  ✓ No attachments found")

            # Step 3: Create or verify collection
            self.console.print(
                "\n[yellow]Step 3:[/yellow] Setting up collection..."
            )
            if collection_id:
                collection = self.client.get_collection(collection_id)
                self.console.print(
                    f"  ✓ Using existing collection: {collection.name}"
                )
            else:
                collection = self.client.create_collection(
                    name=export.space_name,
                    description="Migrated from Docmost export",
                    color="#4E5C6E",
                )
                collection_id = collection.id
                self.console.print(f"  ✓ Created collection: {collection.name}")

            # Step 4: Process documents breadth-first
            self.console.print(
                "\n[yellow]Step 4:[/yellow] Migrating documents..."
            )

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                console=self.console,
            ) as progress:
                task = progress.add_task(
                    "Processing documents...", total=len(export.all_pages)
                )

                # Map to track parent document IDs
                parent_id_map = {}  # file_path -> outline_document_id

                # Process documents in level order (breadth-first)
                for page in export.all_pages:
                    progress.update(
                        task, description=f"Processing: {page.title}"
                    )

                    # Determine parent document ID
                    parent_doc_id = None
                    if page.parent_path:
                        # Find parent .md file
                        parent_md = page.parent_path.with_suffix(".md")
                        parent_doc_id = parent_id_map.get(str(parent_md))

                    # Process attachments for this page
                    url_mapping = {}
                    if export.attachments_dir:
                        attachment_refs = (
                            MarkdownTransformer.extract_attachment_references(
                                page.content
                            )
                        )
                        if attachment_refs:
                            url_mapping = self.attachment_handler.upload_attachments_for_references(
                                attachment_refs, export.attachments_dir
                            )
                            self.stats.attachments_uploaded += len(
                                attachment_refs
                            )

                    # Transform markdown content
                    transformed_content = MarkdownTransformer.transform_content(
                        page.content, url_mapping
                    )

                    # Create document in Outline
                    document = self.client.create_document(
                        title=page.title,
                        text=transformed_content,
                        collection_id=collection_id,
                        parent_document_id=parent_doc_id,
                        publish=True,
                    )

                    # Store mapping for children
                    parent_id_map[str(page.file_path)] = document.id
                    page.outline_id = document.id

                    self.stats.documents_created += 1
                    progress.advance(task)

            # Success!
            self.console.print(
                "\n[bold green]✓ Migration completed successfully![/bold green]"
            )
            self.console.print(f"\nCollection ID: {collection_id}")
            self.console.print(
                f"Collection URL: {self.client.base_url.replace('/api', '')}/collection/{collection.id}"
            )
            self.console.print(f"\n{self.stats}")

            return collection_id, self.stats

        finally:
            # Cleanup temporary directory
            DocmostParser.cleanup(export)
