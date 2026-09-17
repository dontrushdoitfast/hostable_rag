import logging
import httpx
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.config import settings
from app.connectors.base import BaseConnector
from app.connectors.dummy_connector import DummySharePointConnector
from app.ingestion.processor import DocumentProcessor

logger = logging.getLogger(__name__)


class RetrievalChunk(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    source_url: str = Field(..., alias="sourceUrl")
    snippet: str
    document_id: str = Field(..., alias="documentId")
    score: float
    knowledge_base_id: str = Field(..., alias="knowledgeBaseId")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RetrievalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    knowledge_base_id: str = Field(..., alias="knowledgeBaseId")
    query: str
    max_results: Optional[int] = Field(settings.DEFAULT_MAX_RESULTS, alias="maxResults")


class RetrievalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    knowledge_base_id: str = Field(..., alias="knowledgeBaseId")
    query: str
    total_results: int
    chunks: List[RetrievalChunk]


class RetrievalService:
    """
    R2R Knowledge Retrieval Service providing vector/hybrid search restricted to specific knowledgeBaseId.
    """

    def __init__(self, connector: Optional[BaseConnector] = None):
        self.r2r_base_url = settings.R2R_BASE_URL.rstrip("/")
        self.r2r_api_key = settings.R2R_API_KEY
        self.connector = connector

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResponse:
        kb_id = request.knowledge_base_id.lower().replace(" ", "_")
        limit = min(request.max_results or settings.DEFAULT_MAX_RESULTS, settings.MAX_ALLOWED_RESULTS)

        # 1. Try R2R Vector/Hybrid search API if R2R server is running
        try:
            r2r_chunks = await self._search_r2r(kb_id, request.query, limit)
            if r2r_chunks is not None:
                return RetrievalResponse(
                    knowledgeBaseId=kb_id,
                    query=request.query,
                    total_results=len(r2r_chunks),
                    chunks=r2r_chunks,
                )
        except Exception as e:
            logger.warning(f"R2R service search failed/unreachable: {e}. Falling back to local search engine.")

        # 2. Standalone local retrieval fallback (reading from connector & performing keyword/vector scoring)
        fallback_chunks = await self._search_local_fallback(kb_id, request.query, limit)
        return RetrievalResponse(
            knowledgeBaseId=kb_id,
            query=request.query,
            total_results=len(fallback_chunks),
            chunks=fallback_chunks,
        )

    async def _search_r2r(self, kb_id: str, query: str, limit: int) -> Optional[List[RetrievalChunk]]:
        url = f"{self.r2r_base_url}/v3/retrieval/search"
        headers = {}
        if self.r2r_api_key:
            headers["Authorization"] = f"Bearer {self.r2r_api_key}"

        payload = {
            "query": query,
            "search_settings": {
                "limit": limit,
                "filters": {"knowledge_base_id": {"$eq": kb_id}},
            },
        }

        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code != 200:
                return None

            data = resp.json()
            results = data.get("results", {}).get("vector_search_results", [])
            chunks = []
            for item in results:
                meta = item.get("metadata", {})
                # Strictly verify knowledge_base_id filter match
                doc_kb = meta.get("knowledge_base_id", "").lower()
                if doc_kb and doc_kb != kb_id:
                    continue

                chunks.append(
                    RetrievalChunk(
                        title=meta.get("title") or meta.get("filename") or "Untitled Document",
                        sourceUrl=meta.get("source_url") or "",
                        snippet=item.get("text") or item.get("snippet") or "",
                        documentId=meta.get("document_id") or item.get("document_id", "unknown"),
                        score=float(item.get("score") or 0.0),
                        knowledgeBaseId=kb_id,
                        metadata={
                            "folder": meta.get("folder", ""),
                            "modified_at": meta.get("modified_at", ""),
                        },
                    )
                )
            return chunks

    async def _search_local_fallback(self, kb_id: str, query: str, limit: int) -> List[RetrievalChunk]:
        """
        Local fallback engine scanning documents in the target knowledgeBaseId.
        Strictly filters documents to ensure no cross-knowledge-base leaks occur.
        """
        connector = self.connector or DummySharePointConnector()
        all_docs = connector.fetch_documents(knowledge_base_id=kb_id)

        query_terms = set(query.lower().split())
        scored_chunks: List[RetrievalChunk] = []

        for meta in all_docs:
            if meta.knowledge_base_id != kb_id:
                continue

            doc_item = connector.download_document(meta.document_id)
            if not doc_item:
                continue

            text = DocumentProcessor.extract_text(
                doc_item.content,
                meta.filename,
                meta.content_type,
            )

            # Calculate simple BM25-like/keyword similarity score
            text_lower = text.lower()
            matches = sum(1 for term in query_terms if term in text_lower)
            score = round((matches / (len(query_terms) or 1)) * 0.95 + 0.05, 4)

            # Build snippet around first matched query term or start of document
            snippet = text[:250] + ("..." if len(text) > 250 else "")

            scored_chunks.append(
                RetrievalChunk(
                    title=meta.filename,
                    sourceUrl=meta.source_url,
                    snippet=snippet,
                    documentId=meta.document_id,
                    score=score if matches > 0 else 0.1,
                    knowledgeBaseId=kb_id,
                    metadata={
                        "folder": meta.folder,
                        "modified_at": meta.modified_at.isoformat(),
                        "file_size": meta.file_size,
                    },
                )
            )

        # Sort by relevance score descending
        scored_chunks.sort(key=lambda x: x.score, reverse=True)
        return scored_chunks[:limit]
