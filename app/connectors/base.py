from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class DocumentMetadata(BaseModel):
    document_id: str
    filename: str
    folder: str
    knowledge_base_id: str
    source_url: str
    modified_at: datetime
    content_type: str
    file_size: int
    extra: Dict[str, Any] = Field(default_factory=dict)


class DocumentItem(BaseModel):
    metadata: DocumentMetadata
    content: bytes


class SyncDelta(BaseModel):
    added_or_updated: List[DocumentMetadata] = Field(default_factory=list)
    deleted_ids: List[str] = Field(default_factory=list)
    delta_token: Optional[str] = None


class BaseConnector(ABC):
    """
    Abstract interface for document repository connectors (e.g., SharePoint, Dummy local directory).
    """

    @abstractmethod
    def get_knowledge_bases(self) -> List[str]:
        """
        Returns a list of knowledge base IDs (folder mappings).
        """
        pass

    @abstractmethod
    def fetch_documents(self, knowledge_base_id: Optional[str] = None) -> List[DocumentMetadata]:
        """
        Lists all document metadata across all knowledge base folders or a specific folder.
        """
        pass

    @abstractmethod
    def download_document(self, document_id: str) -> Optional[DocumentItem]:
        """
        Downloads content bytes and metadata for a single document ID.
        """
        pass

    @abstractmethod
    def get_deltas(self, last_sync_token: Optional[str] = None, last_sync_time: Optional[datetime] = None) -> SyncDelta:
        """
        Retrieves additions, updates, and deletions since the last sync checkpoint.
        """
        pass
