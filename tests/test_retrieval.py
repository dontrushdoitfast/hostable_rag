import pytest
from unittest.mock import MagicMock, AsyncMock, patch
import httpx
from app.retrieval.service import RetrievalService, RetrievalRequest, RetrievalResponse
from app.connectors.dummy_connector import DummySharePointConnector
from app.config import settings


@pytest.mark.asyncio
async def test_retrieval_service_isolation(tmp_path):
    # Setup mock knowledge base
    folder_a = tmp_path / "KB_Alpha"
    folder_a.mkdir()
    (folder_a / "alpha.txt").write_text("Alpha secret strategy document.")

    folder_b = tmp_path / "KB_Beta"
    folder_b.mkdir()
    (folder_b / "beta.txt").write_text("Beta confidential project roadmap.")

    dummy_conn = DummySharePointConnector(root_dir=str(tmp_path), auto_seed=False)
    service = RetrievalService(connector=dummy_conn)

    # Query KB Alpha
    req_a = RetrievalRequest(knowledgeBaseId="kb_alpha", query="strategy", maxResults=5)
    res_a = await service.retrieve(req_a)

    assert res_a.total_results == 1
    assert res_a.chunks[0].knowledge_base_id == "kb_alpha"
    assert "alpha" in res_a.chunks[0].title.lower()

    # Query KB Beta
    req_b = RetrievalRequest(knowledgeBaseId="kb_beta", query="roadmap", maxResults=5)
    res_b = await service.retrieve(req_b)

    assert res_b.total_results == 1
    assert res_b.chunks[0].knowledge_base_id == "kb_beta"

    # Verify cross-knowledge-base isolation: query Alpha for Beta terms returns Alpha chunks only
    req_cross = RetrievalRequest(knowledgeBaseId="kb_alpha", query="roadmap", maxResults=5)
    res_cross = await service.retrieve(req_cross)
    for chunk in res_cross.chunks:
        assert chunk.knowledge_base_id == "kb_alpha"


@pytest.mark.asyncio
async def test_retrieval_max_results_clamping(tmp_path):
    folder = tmp_path / "Bulk_Docs"
    folder.mkdir()
    # Create 20 documents
    for i in range(20):
        (folder / f"doc_{i}.txt").write_text(f"Common keyword content for doc {i}")

    dummy_conn = DummySharePointConnector(root_dir=str(tmp_path), auto_seed=False)
    service = RetrievalService(connector=dummy_conn)

    # Request 50 results (exceeds MAX_ALLOWED_RESULTS = 15)
    req = RetrievalRequest(knowledgeBaseId="bulk_docs", query="keyword", maxResults=50)
    res = await service.retrieve(req)

    assert res.total_results == settings.MAX_ALLOWED_RESULTS
    assert len(res.chunks) == settings.MAX_ALLOWED_RESULTS


@pytest.mark.asyncio
async def test_r2r_search_parsing():
    service = RetrievalService()

    fake_response = {
        "results": {
            "vector_search_results": [
                {
                    "text": "Chunk text snippet from R2R vector search",
                    "score": 0.88,
                    "metadata": {
                        "title": "Strategy Doc",
                        "source_url": "https://sharepoint.example.com/doc1",
                        "document_id": "doc-123",
                        "knowledge_base_id": "engineering",
                        "folder": "Engineering",
                    },
                },
                # Mismatched knowledge base chunk should be filtered out
                {
                    "text": "Leaked chunk",
                    "score": 0.99,
                    "metadata": {
                        "title": "Wrong KB Doc",
                        "source_url": "https://sharepoint.example.com/leak",
                        "document_id": "doc-leak",
                        "knowledge_base_id": "other_kb",
                    },
                },
            ]
        }
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = fake_response

    with patch("httpx.AsyncClient.post", return_value=mock_resp):
        chunks = await service._search_r2r("engineering", "strategy", 10)
        assert chunks is not None
        assert len(chunks) == 1
        assert chunks[0].title == "Strategy Doc"
        assert chunks[0].knowledge_base_id == "engineering"
        assert chunks[0].score == 0.88
