import pytest
from pathlib import Path
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
