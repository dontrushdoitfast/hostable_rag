import logging
import httpx
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from msal import ConfidentialClientApplication

from app.connectors.base import BaseConnector, DocumentMetadata, DocumentItem, SyncDelta
from app.config import settings

logger = logging.getLogger(__name__)


class SharePointConnector(BaseConnector):
    """
    Microsoft Graph API connector for SharePoint Online sites and drives.
    Provides site enumeration, folder-to-knowledge-base mapping, incremental delta tracking, and file retrieval.
    """

    def __init__(
        self,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        site_id: Optional[str] = None,
    ):
        self.tenant_id = tenant_id or settings.SHAREPOINT_TENANT_ID
        self.client_id = client_id or settings.SHAREPOINT_CLIENT_ID
        self.client_secret = client_secret or settings.SHAREPOINT_CLIENT_SECRET
        self.site_id = site_id or settings.SHAREPOINT_SITE_ID
        self.graph_base_url = "https://graph.microsoft.com/v1.0"
        self._app: Optional[ConfidentialClientApplication] = None

    def _get_access_token(self) -> str:
        if not (self.tenant_id and self.client_id and self.client_secret):
            raise ValueError("SharePoint tenant_id, client_id, and client_secret are required for production SharePoint integration.")

        if self._app is None:
            authority = f"https://login.microsoftonline.com/{self.tenant_id}"
            self._app = ConfidentialClientApplication(
                client_id=self.client_id,
                client_credential=self.client_secret,
                authority=authority,
            )

        scopes = ["https://graph.microsoft.com/.default"]
        result = self._app.acquire_token_for_client(scopes=scopes)

        if "access_token" in result:
            return result["access_token"]
        else:
            error_desc = result.get("error_description", "Unknown MSAL error")
            raise RuntimeError(f"Failed to acquire Microsoft Graph token: {error_desc}")

    def _get_headers(self) -> Dict[str, str]:
        token = self._get_access_token()
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    def get_knowledge_bases(self) -> List[str]:
        """
        Lists top-level folders in the main SharePoint drive as logical knowledge base IDs.
        """
        if not self.site_id:
            logger.warning("SHAREPOINT_SITE_ID is not configured.")
            return []

        url = f"{self.graph_base_url}/sites/{self.site_id}/drive/root/children"
        folders = []
        with httpx.Client() as client:
            while url:
                resp = client.get(url, headers=self._get_headers())
                if resp.status_code != 200:
                    logger.error(f"Error fetching SharePoint root children: {resp.status_code} {resp.text}")
                    break

                data = resp.json()
                for item in data.get("value", []):
                    if "folder" in item:
                        kb_id = item["name"].lower().replace(" ", "_")
                        folders.append(kb_id)
                url = data.get("@odata.nextLink")
        return folders

    def fetch_documents(self, knowledge_base_id: Optional[str] = None) -> List[DocumentMetadata]:
        """
        Recursively fetches metadata for documents in the specified knowledge base or all folders.
        """
        if not self.site_id:
            return []

        url = f"{self.graph_base_url}/sites/{self.site_id}/drive/root/children"
        docs: List[DocumentMetadata] = []

        with httpx.Client() as client:
            while url:
                resp = client.get(url, headers=self._get_headers())
                if resp.status_code != 200:
                    break

                data = resp.json()
                items = data.get("value", [])
                for item in items:
                    if "folder" in item:
                        folder_name = item["name"]
                        kb_id = folder_name.lower().replace(" ", "_")
                        if knowledge_base_id and knowledge_base_id.lower() != kb_id:
                            continue
                        folder_id = item["id"]
                        docs.extend(self._fetch_folder_docs(client, folder_id, folder_name, kb_id))
                url = data.get("@odata.nextLink")

        return docs

    def _fetch_folder_docs(self, client: httpx.Client, folder_id: str, folder_name: str, kb_id: str) -> List[DocumentMetadata]:
        docs: List[DocumentMetadata] = []
        url = f"{self.graph_base_url}/sites/{self.site_id}/drive/items/{folder_id}/children"

        while url:
            resp = client.get(url, headers=self._get_headers())
            if resp.status_code != 200:
                break
            data = resp.json()
            for item in data.get("value", []):
                if "folder" in item:
                    docs.extend(self._fetch_folder_docs(client, item["id"], f"{folder_name}/{item['name']}", kb_id))
                elif "file" in item:
                    mtime_str = item.get("lastModifiedDateTime")
                    mtime = (
                        datetime.fromisoformat(mtime_str.replace("Z", "+00:00"))
                        if mtime_str
                        else datetime.now(timezone.utc)
                    )
                    doc_meta = DocumentMetadata(
                        document_id=item["id"],
                        filename=item["name"],
                        folder=folder_name,
                        knowledge_base_id=kb_id,
                        source_url=item.get("webUrl", ""),
                        modified_at=mtime,
                        content_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                        file_size=item.get("size", 0),
                        extra={"download_url": item.get("@microsoft.graph.downloadUrl")},
                    )
                    docs.append(doc_meta)
            url = data.get("@odata.nextLink")

        return docs

    def download_document(self, document_id: str) -> Optional[DocumentItem]:
        """
        Downloads item content bytes and retrieves metadata for given item ID.
        """
        if not self.site_id:
            return None

        url = f"{self.graph_base_url}/sites/{self.site_id}/drive/items/{document_id}"
        with httpx.Client() as client:
            resp = client.get(url, headers=self._get_headers())
            if resp.status_code != 200:
                return None
            item = resp.json()

            download_url = item.get("@microsoft.graph.downloadUrl")
            if not download_url:
                content_resp = client.get(f"{url}/content", headers=self._get_headers(), follow_redirects=True)
                if content_resp.status_code != 200:
                    return None
                content_bytes = content_resp.content
            else:
                download_resp = client.get(download_url, follow_redirects=True)
                if download_resp.status_code != 200:
                    return None
                content_bytes = download_resp.content

            mtime_str = item.get("lastModifiedDateTime")
            mtime = datetime.fromisoformat(mtime_str.replace("Z", "+00:00")) if mtime_str else datetime.now(timezone.utc)
            folder_path = item.get("parentReference", {}).get("path", "").split("root:")[-1].lstrip("/")
            kb_id = folder_path.split("/")[0].lower().replace(" ", "_") if folder_path else "root"

            meta = DocumentMetadata(
                document_id=item["id"],
                filename=item["name"],
                folder=folder_path or "root",
                knowledge_base_id=kb_id,
                source_url=item.get("webUrl", ""),
                modified_at=mtime,
                content_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                file_size=item.get("size", 0),
            )
            return DocumentItem(metadata=meta, content=content_bytes)

    def get_deltas(self, last_sync_token: Optional[str] = None, last_sync_time: Optional[datetime] = None) -> SyncDelta:
        """
        Queries Microsoft Graph delta endpoint for incremental updates/deletions.
        """
        if not self.site_id:
            return SyncDelta()

        if last_sync_token and last_sync_token.startswith("http"):
            url = last_sync_token
        else:
            url = f"{self.graph_base_url}/sites/{self.site_id}/drive/root/delta"

        added_or_updated: List[DocumentMetadata] = []
        deleted_ids: List[str] = []
        next_delta_link = None

        with httpx.Client() as client:
            while url:
                resp = client.get(url, headers=self._get_headers())
                if resp.status_code != 200:
                    break
                data = resp.json()
                for item in data.get("value", []):
                    if "deleted" in item:
                        deleted_ids.append(item["id"])
                    elif "file" in item:
                        mtime_str = item.get("lastModifiedDateTime")
                        mtime = (
                            datetime.fromisoformat(mtime_str.replace("Z", "+00:00"))
                            if mtime_str
                            else datetime.now(timezone.utc)
                        )
                        parent_path = item.get("parentReference", {}).get("path", "").split("root:")[-1].lstrip("/")
                        kb_id = parent_path.split("/")[0].lower().replace(" ", "_") if parent_path else "root"

                        meta = DocumentMetadata(
                            document_id=item["id"],
                            filename=item["name"],
                            folder=parent_path or "root",
                            knowledge_base_id=kb_id,
                            source_url=item.get("webUrl", ""),
                            modified_at=mtime,
                            content_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                            file_size=item.get("size", 0),
                        )
                        added_or_updated.append(meta)

                url = data.get("@odata.nextLink")
                next_delta_link = data.get("@odata.deltaLink") or next_delta_link

        return SyncDelta(
            added_or_updated=added_or_updated,
            deleted_ids=deleted_ids,
            delta_token=next_delta_link,
        )
