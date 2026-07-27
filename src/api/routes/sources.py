from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
import os
import json
import asyncio
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

def get_chat_service(request: Request):
    return getattr(request.app.state, "chat_service", None)

@router.get("/sources")
async def get_sources(chat_service=Depends(get_chat_service)):
    """Returns a list of all documents indexed in the database."""
    if not chat_service or not hasattr(chat_service.retriever, "documents"):
        return []
    
    # Chỉ trả về một số trường cần thiết để hiển thị trên UI, giới hạn dung lượng
    docs = []
    for doc in chat_service.retriever.documents:
        docs.append({
            "id": doc.get("id"),
            "source": doc.get("source"),
            "url": doc.get("url"),
            "title": doc.get("title"),
            "section_title": doc.get("section_title")
        })
    return docs

@router.post("/retrieve")
async def retrieve_only(request: Request, chat_service=Depends(get_chat_service)):
    """Retrieve chunks only without calling LLM."""
    data = await request.json()
    query = data.get("question", "")
    if not query:
        return JSONResponse(content={"error": "No question provided"}, status_code=400)
        
    if not chat_service:
        return {"question": query, "chunks": []}
        
    results = chat_service.retriever.retrieve(query, top_k=5)
    
    chunks = []
    for r in results:
        doc = chat_service.retriever.doc_map.get(r["id"], {})
        chunks.append({
            "id": r["id"],
            "score": r["score"],
            "content": doc.get("content", ""),
            "source": doc.get("source", ""),
            "url": doc.get("url", ""),
            "section_title": doc.get("section_title", "")
        })
        
    return {"question": query, "chunks": chunks}

@router.delete("/sources/{doc_id}")
async def delete_source(doc_id: int, request: Request, chat_service=Depends(get_chat_service)):
    """Deletes a document from the knowledge base by ID and triggers re-indexing."""
    # Read knowledge_base.json
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    kb_path = os.path.join(project_root, "data", "knowledge_base.json")
    
    if not os.path.exists(kb_path):
        return JSONResponse(status_code=404, content={"error": "Knowledge base not found"})
        
    try:
        with open(kb_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        initial_len = len(data)
        data = [doc for doc in data if doc.get("id") != doc_id]
        
        if len(data) == initial_len:
            return JSONResponse(status_code=404, content={"error": "Document not found"})
            
        # Write back
        with open(kb_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
        # Trigger re-index in background
        if chat_service and hasattr(chat_service, "retriever"):
            loop = asyncio.get_event_loop()
            logger.info(f"Deleted doc {doc_id}, rebuilding index...")
            await loop.run_in_executor(None, chat_service.retriever.load_or_build_index)
            
        return {"success": True, "message": f"Deleted document {doc_id}"}
    except Exception as e:
        logger.error(f"Error deleting source {doc_id}: {str(e)}")
        return JSONResponse(status_code=500, content={"error": str(e)})
