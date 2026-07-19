from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from data_pipeline.firecrawl_ingester import FirecrawlIngester
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

def get_chat_service(request: Request):
    return getattr(request.app.state, "chat_service", None)


# Let's write Pydantic schema for cleaner validation
from pydantic import BaseModel, HttpUrl
from typing import Optional

class IngestRequest(BaseModel):
    url: str
    mode: Optional[str] = "scrape"
    api_key: Optional[str] = None
    api_url: Optional[str] = None

@router.post("/ingest")
async def ingest_url(payload: IngestRequest, request: Request, chat_service=Depends(get_chat_service)):
    """
    API endpoint to trigger Firecrawl ingestion.
    """
    url = str(payload.url)
    mode = payload.mode
    api_key = payload.api_key
    api_url = payload.api_url

    if not url:
        raise HTTPException(status_code=400, detail="URL is required.")

    if mode not in ["scrape", "crawl"]:
        raise HTTPException(status_code=400, detail="Mode must be either 'scrape' or 'crawl'.")

    # If api_key is not passed, let's try to get it from settings.yaml or env
    settings_key = None
    settings_url = None
    if chat_service and hasattr(chat_service, "settings"):
        settings_key = chat_service.settings.get("firecrawl", {}).get("api_key")
        settings_url = chat_service.settings.get("firecrawl", {}).get("api_url")

    effective_key = api_key or settings_key
    effective_url = api_url or settings_url

    # Perform ingestion in a separate threadpool since it makes external HTTP requests
    loop = asyncio.get_event_loop()
    
    def run_ingestion():
        ingester = FirecrawlIngester(api_key=effective_key, api_url=effective_url)
        return ingester.ingest_url(url, mode=mode)

    try:
        result = await loop.run_in_executor(None, run_ingestion)
    except Exception as e:
        logger.error(f"Error during ingestion: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "chunks_added": 0,
                "log": f"❌ Lỗi máy chủ: {str(e)}",
                "chunks": []
            }
        )

    # Rebuild database index if chunks were successfully added
    if result.get("success") and result.get("chunks_added", 0) > 0:
        if chat_service and hasattr(chat_service, "retriever"):
            try:
                logger.info("Rebuilding Qdrant and BM25 index with new documents...")
                # Run index rebuild in executor to prevent blocking
                await loop.run_in_executor(None, chat_service.retriever.load_or_build_index)
                logger.info("Successfully rebuilt index.")
            except Exception as index_err:
                logger.error(f"Error rebuilding index: {str(index_err)}")
                result["log"] += f"\n⚠️ Cảnh báo: Lỗi khi cập nhật chỉ mục tìm kiếm: {str(index_err)}"

    return result
