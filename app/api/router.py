from fastapi import APIRouter, Depends, status
from app.auth import verify_api_key
from app.retrieval.service import RetrievalService, RetrievalRequest, RetrievalResponse
from app.ingestion.sync_engine import SyncEngine

router = APIRouter()
retrieval_service = RetrievalService()
sync_engine = SyncEngine()


@router.post(
    "/retrieve",
    response_model=RetrievalResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(verify_api_key)],
    summary="Retrieve knowledge base chunks for Microsoft Copilot",
)
async def retrieve_knowledge(request: RetrievalRequest) -> RetrievalResponse:
    """
    Authenticated knowledge retrieval endpoint. Guarantees retrieval is restricted
    to the requested knowledgeBaseId and returns ranked chunks.
    """
    return await retrieval_service.retrieve(request)


@router.post(
    "/sync/trigger",
    dependencies=[Depends(verify_api_key)],
    summary="Trigger manual incremental sync",
)
async def trigger_sync():
    """
    Triggers an immediate incremental synchronization pass across SharePoint/local data source.
    """
    result = await sync_engine.run_sync()
    return result


@router.get(
    "/sync/status",
    dependencies=[Depends(verify_api_key)],
    summary="Get synchronization status and diagnostics",
)
async def get_sync_status():
    """
    Returns latest sync statistics, status, last run timestamps, and diagnostic errors.
    """
    return sync_engine.sync_stats


@router.post(
    "/test/copilot",
    summary="Dummy Copilot test endpoint for local prototyping",
)
async def test_copilot_client(request: RetrievalRequest, authenticated: str = Depends(verify_api_key)):
    """
    Dummy Copilot test endpoint that submits a retrieval request and displays
    the raw retrieval response formatted for testing.
    """
    response = await retrieval_service.retrieve(request)
    return {
        "status": "success",
        "copilot_grounding_payload": {
            "query": response.query,
            "knowledgeBaseId": response.knowledge_base_id,
            "returned_chunk_count": response.total_results,
            "chunks": [chunk.model_dump(by_alias=True) for chunk in response.chunks],
        },
    }
