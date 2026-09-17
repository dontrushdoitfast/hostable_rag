import pytest
from pathlib import Path
from app.ingestion.processor import DocumentProcessor
from app.ingestion.sync_engine import SyncEngine
from app.connectors.dummy_connector import DummySharePointConnector


def test_document_processor_text():
    text = DocumentProcessor.extract_text(b"Hello world!", "test.txt", "text/plain")
    assert text == "Hello world!"


def test_document_processor_html():
    html_content = b"<html><body><h1>Title</h1><p>Body content here.</p></body></html>"
    text = DocumentProcessor.extract_text(html_content, "index.html", "text/html")
    assert "Title" in text
    assert "Body content here." in text


def test_document_processor_csv():
    csv_content = b"header1,header2\nval1,val2"
    text = DocumentProcessor.extract_text(csv_content, "data.csv", "text/csv")
    assert "header1 | header2" in text
    assert "val1 | val2" in text


@pytest.mark.asyncio
async def test_sync_engine_run(tmp_path: Path):
    folder = tmp_path / "Docs"
    folder.mkdir()
    (folder / "doc1.txt").write_text("Text content for document 1.")

    connector = DummySharePointConnector(root_dir=str(tmp_path), auto_seed=False)
    engine = SyncEngine(connector=connector)

    stats = await engine.run_sync()
    assert stats["status"] == "success"
    assert stats["documents_added_or_updated"] == 1
    assert stats["documents_deleted"] == 0
