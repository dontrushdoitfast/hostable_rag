import pytest
from app.retrieval.service import RetrievalService, RetrievalRequest
from app.connectors.dummy_connector import DummySharePointConnector


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
    res_a = await service._search_local_fallback("kb_alpha", req_a.query, 5)

    assert len(res_a) == 1
    assert res_a[0].knowledge_base_id == "kb_alpha"
    assert "alpha" in res_a[0].title.lower()

    # Query KB Beta
    req_b = RetrievalRequest(knowledgeBaseId="kb_beta", query="roadmap", maxResults=5)
    res_b = await service._search_local_fallback("kb_beta", req_b.query, 5)

    assert len(res_b) == 1
    assert res_b[0].knowledge_base_id == "kb_beta"

    # Verify cross-knowledge-base isolation: query Alpha for Beta terms
    res_cross = await service._search_local_fallback("kb_alpha", "roadmap", 5)
    for chunk in res_cross:
        assert chunk.knowledge_base_id == "kb_alpha"
