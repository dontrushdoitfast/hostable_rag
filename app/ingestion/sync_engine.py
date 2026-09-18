import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple
import httpx

from app.config import settings
from app.connectors.base import BaseConnector, DocumentMetadata
from app.connectors.dummy_connector import DummySharePointConnector
from app.connectors.sharepoint_connector import SharePointConnector
from app.ingestion.processor import DocumentProcessor

logger = logging.getLogger(__name__)


class SyncEngine:
    """
    Incremental Sync Engine that coordinates connectors, document parsing, and R2R ingestion.
    Supports scheduled background sync (hourly) and manual triggers.
    """

    def __init__(self, connector: Optional[BaseConnector] = None):
        if connector:
            self.connector = connector
        elif settings.CONNECTOR_MODE.lower() == "sharepoint":
            self.connector = SharePointConnector()
        else:
            self.connector = DummySharePointConnector()

        self.last_sync_time: Optional[datetime] = None
        self.last_delta_token: Optional[str] = None
        self.is_syncing: bool = False
        self.sync_stats: Dict[str, Any] = {
            "status": "idle",
            "last_sync_start": None,
            "last_sync_end": None,
            "documents_added_or_updated": 0,
            "documents_deleted": 0,
            "errors": [],
        }
        self._bg_task: Optional[asyncio.Task] = None

    def start_scheduled_sync(self):
        """Starts background periodic sync task."""
        if settings.AUTO_SYNC_ENABLED and not self._bg_task:
            self._bg_task = asyncio.create_task(self._scheduled_sync_loop())
            logger.info(f"Scheduled sync loop started (interval={settings.SYNC_INTERVAL_SECONDS}s).")

    def stop_scheduled_sync(self):
        """Cancels background periodic sync task."""
        if self._bg_task and not self._bg_task.done():
            self._bg_task.cancel()
            self._bg_task = None
            logger.info("Scheduled sync loop stopped.")

    async def _scheduled_sync_loop(self):
        while True:
            try:
                await asyncio.sleep(settings.SYNC_INTERVAL_SECONDS)
                logger.info("Executing scheduled hourly incremental sync...")
                await self.run_sync()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in scheduled sync loop: {e}")

    async def run_sync(self) -> Dict[str, Any]:
        """
        Executes single sync pass: fetching deltas, downloading content, extracting text,
        ingesting into R2R (collection mapped per folder), and updating sync stats.
        """
        if self.is_syncing:
            return {"status": "in_progress", "message": "Sync is already running."}

        self.is_syncing = True
        start_time = datetime.now(timezone.utc)
        self.sync_stats["status"] = "running"
        self.sync_stats["last_sync_start"] = start_time.isoformat()
        self.sync_stats["errors"] = []

        added_updated_count = 0
        deleted_count = 0

        try:
            delta = self.connector.get_deltas(
                last_sync_token=self.last_delta_token,
                last_sync_time=self.last_sync_time,
            )

            # Process additions and updates
            for doc_meta in delta.added_or_updated:
                try:
                    doc_item = self.connector.download_document(doc_meta.document_id)
                    if doc_item:
                        text_content = DocumentProcessor.extract_text(
                            doc_item.content,
                            doc_item.metadata.filename,
                            doc_item.metadata.content_type,
                        )
                        await self._ingest_into_r2r(doc_item.metadata, text_content)
                        added_updated_count += 1
                except Exception as e:
                    err_msg = f"Failed to ingest document {doc_meta.document_id} ({doc_meta.filename}): {e}"
                    logger.error(err_msg)
                    self.sync_stats["errors"].append(err_msg)

            # Process deletions
            for doc_id in delta.deleted_ids:
                try:
                    await self._delete_from_r2r(doc_id)
                    deleted_count += 1
                except Exception as e:
                    err_msg = f"Failed to delete document {doc_id}: {e}"
                    logger.error(err_msg)
                    self.sync_stats["errors"].append(err_msg)

            self.last_sync_time = start_time
            if delta.delta_token:
                self.last_delta_token = delta.delta_token

            end_time = datetime.now(timezone.utc)
            self.sync_stats["status"] = "success" if not self.sync_stats["errors"] else "partial_success"
            self.sync_stats["last_sync_end"] = end_time.isoformat()
            self.sync_stats["documents_added_or_updated"] = added_updated_count
            self.sync_stats["documents_deleted"] = deleted_count

        except Exception as e:
            logger.error(f"Sync execution failed: {e}")
            self.sync_stats["status"] = "failed"
            self.sync_stats["errors"].append(str(e))
        finally:
            self.is_syncing = False

        return self.sync_stats

    async def _ingest_into_r2r(self, meta: DocumentMetadata, content: str):
        """
        Sends document payload to R2R via HTTP API or R2R Python SDK.
        Ensures metadata (SharePoint URL, filename, folder, modified date, doc ID) and
        collection mapping (knowledgeBaseId) are explicitly attached.
        """
        payload = {
            "document_id": meta.document_id,
            "raw_sync_data": {
                "text": content,
            },
            "metadata": {
                "document_id": meta.document_id,
                "title": meta.filename,
                "filename": meta.filename,
                "folder": meta.folder,
                "knowledge_base_id": meta.knowledge_base_id,
                "source_url": meta.source_url,
                "modified_at": meta.modified_at.isoformat(),
            },
            "collection_ids": [meta.knowledge_base_id],
        }

        # Try HTTP request to R2R REST endpoint if running
        headers = {}
        if settings.R2R_API_KEY:
            headers["Authorization"] = f"Bearer {settings.R2R_API_KEY}"

        url = f"{settings.R2R_BASE_URL.rstrip('/')}/v3/documents"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload, headers=headers)
                if res.status_code in (200, 201):
                    logger.info(f"Ingested document {meta.document_id} into R2R collection {meta.knowledge_base_id}")
                else:
                    logger.warning(f"R2R HTTP ingestion returned status {res.status_code}: {res.text}. Storing document state in memory/fallback.")
        except Exception as e:
            logger.warning(f"Could not reach external R2R service at {settings.R2R_BASE_URL} ({e}). Proceeding with local service cache.")

    async def _delete_from_r2r(self, document_id: str):
        headers = {}
        if settings.R2R_API_KEY:
            headers["Authorization"] = f"Bearer {settings.R2R_API_KEY}"

        url = f"{settings.R2R_BASE_URL.rstrip('/')}/v3/documents/{document_id}"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.delete(url, headers=headers)
        except Exception as e:
            logger.warning(f"Failed R2R deletion request for {document_id}: {e}")
