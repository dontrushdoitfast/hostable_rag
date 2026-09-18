import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from app.connectors.dummy_connector import DummySharePointConnector
from app.connectors.sharepoint_connector import SharePointConnector


def test_dummy_connector_basic(tmp_path: Path):
    # Setup test directory structure
    folder1 = tmp_path / "HR_Policies"
    folder1.mkdir()
    file1 = folder1 / "handbook.txt"
    file1.write_text("Employee handbook content.")

    folder2 = tmp_path / "Engineering"
    folder2.mkdir()
    file2 = folder2 / "design.txt"
    file2.write_text("Architecture design spec.")

    connector = DummySharePointConnector(root_dir=str(tmp_path), base_url="https://test.sharepoint.com", auto_seed=False)

    kbs = connector.get_knowledge_bases()
    assert "hr_policies" in kbs
    assert "engineering" in kbs

    docs = connector.fetch_documents(knowledge_base_id="hr_policies")
    assert len(docs) == 1
    assert docs[0].filename == "handbook.txt"
    assert docs[0].knowledge_base_id == "hr_policies"

    item = connector.download_document(docs[0].document_id)
    assert item is not None
    assert b"Employee handbook content." in item.content


def test_dummy_connector_deltas(tmp_path: Path):
    folder = tmp_path / "Sales"
    folder.mkdir()
    file1 = folder / "pitch.txt"
    file1.write_text("Sales pitch presentation.")

    connector = DummySharePointConnector(root_dir=str(tmp_path), auto_seed=False)
    delta = connector.get_deltas()
    assert len(delta.added_or_updated) == 1
    assert delta.added_or_updated[0].filename == "pitch.txt"


def test_sharepoint_connector_unconfigured():
    connector = SharePointConnector(tenant_id=None, client_id=None, client_secret=None, site_id=None)
    assert connector.get_knowledge_bases() == []
    assert connector.fetch_documents() == []
    assert connector.download_document("doc-id") is None
    assert connector.get_deltas().added_or_updated == []

    # Missing credentials should raise ValueError on token acquisition
    with pytest.raises(ValueError, match="required for production SharePoint"):
        connector._get_access_token()


def test_sharepoint_connector_token_and_pagination():
    connector = SharePointConnector(
        tenant_id="test-tenant",
        client_id="test-client",
        client_secret="test-secret",
        site_id="test-site",
    )

    mock_app = MagicMock()
    mock_app.acquire_token_for_client.return_value = {"access_token": "mock-token-xyz"}

    with patch("app.connectors.sharepoint_connector.ConfidentialClientApplication", return_value=mock_app):
        token = connector._get_access_token()
        assert token == "mock-token-xyz"
        mock_app.acquire_token_for_client.assert_called_once_with(scopes=["https://graph.microsoft.com/.default"])

        # Test pagination in get_knowledge_bases
        page1 = {
            "value": [{"name": "Folder One", "folder": {}}],
            "@odata.nextLink": "https://graph.microsoft.com/v1.0/page2",
        }
        page2 = {
            "value": [{"name": "Folder Two", "folder": {}}],
        }

        mock_resp1 = MagicMock(status_code=200, json=lambda: page1)
        mock_resp2 = MagicMock(status_code=200, json=lambda: page2)

        with patch("httpx.Client.get", side_effect=[mock_resp1, mock_resp2]):
            kbs = connector.get_knowledge_bases()
            assert "folder_one" in kbs
            assert "folder_two" in kbs
