import os
import hashlib
import mimetypes
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Optional
from app.connectors.base import BaseConnector, DocumentMetadata, DocumentItem, SyncDelta
from app.config import settings


class DummySharePointConnector(BaseConnector):
    """
    Local filesystem dummy connector mapping folders to knowledgeBaseIds and generating fake SharePoint metadata.
    """

    def __init__(self, root_dir: Optional[str] = None, base_url: Optional[str] = None, auto_seed: bool = True):
        self.root_dir = Path(root_dir or settings.LOCAL_DATA_DIR).resolve()
        self.base_url = (base_url or settings.MOCK_SHAREPOINT_BASE_URL).rstrip("/")
        if auto_seed:
            self._ensure_sample_data()

    def _ensure_sample_data(self):
        """Creates sample directories and mock files if root_dir is empty or missing."""
        if not self.root_dir.exists():
            self.root_dir.mkdir(parents=True, exist_ok=True)

        # Create ~3 test folders (logical knowledge bases) if none exist
        kb_folders = ["HR_Policies", "Engineering_Docs", "Sales_Playbooks"]
        for kb_folder in kb_folders:
            folder_path = self.root_dir / kb_folder
            if not folder_path.exists():
                folder_path.mkdir(parents=True, exist_ok=True)
                sample_file = folder_path / "overview.txt"
                if not sample_file.exists():
                    sample_file.write_text(
                        f"Sample knowledge base document for {kb_folder}.\n"
                        f"This document contains important details about {kb_folder.replace('_', ' ')}."
                    )

    def _generate_doc_id(self, relative_path: Path) -> str:
        """Deterministically generates a document ID from its relative path."""
        return hashlib.sha256(str(relative_path).encode("utf-8")).hexdigest()[:16]

    def _file_to_metadata(self, file_path: Path) -> DocumentMetadata:
        rel_path = file_path.relative_to(self.root_dir)
        parts = rel_path.parts
        folder_name = parts[0] if len(parts) > 1 else "Root"
        kb_id = folder_name.lower().replace(" ", "_")

        stat = file_path.stat()
        mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
        doc_id = self._generate_doc_id(rel_path)

        mime_type, _ = mimetypes.guess_type(file_path)
        content_type = mime_type or "application/octet-stream"

        source_url = f"{self.base_url}/{folder_name}/{file_path.name}"

        return DocumentMetadata(
            document_id=doc_id,
            filename=file_path.name,
            folder=folder_name,
            knowledge_base_id=kb_id,
            source_url=source_url,
            modified_at=mtime,
            content_type=content_type,
            file_size=stat.st_size,
            extra={"local_path": str(file_path), "rel_path": str(rel_path)},
        )

    def get_knowledge_bases(self) -> List[str]:
        if not self.root_dir.exists():
            return []
        kb_set = set()
        for item in self.root_dir.iterdir():
            if item.is_dir():
                kb_set.add(item.name.lower().replace(" ", "_"))
        return sorted(list(kb_set))

    def fetch_documents(self, knowledge_base_id: Optional[str] = None) -> List[DocumentMetadata]:
        docs = []
        if not self.root_dir.exists():
            return docs

        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file():
                meta = self._file_to_metadata(file_path)
                if knowledge_base_id is None or meta.knowledge_base_id == knowledge_base_id.lower():
                    docs.append(meta)
        return docs

    def download_document(self, document_id: str) -> Optional[DocumentItem]:
        for file_path in self.root_dir.rglob("*"):
            if file_path.is_file():
                meta = self._file_to_metadata(file_path)
                if meta.document_id == document_id:
                    content = file_path.read_bytes()
                    return DocumentItem(metadata=meta, content=content)
        return None

    def get_deltas(self, last_sync_token: Optional[str] = None, last_sync_time: Optional[datetime] = None) -> SyncDelta:
        all_docs = self.fetch_documents()
        added_or_updated = []

        for doc in all_docs:
            if last_sync_time is None or doc.modified_at > last_sync_time:
                added_or_updated.append(doc)

        new_sync_time = datetime.now(timezone.utc).isoformat()
        return SyncDelta(
            added_or_updated=added_or_updated,
            deleted_ids=[],  # Dummy connector simple mode assumes filesystem scan
            delta_token=new_sync_time,
        )
