from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse
import requests
import os
import yaml

router = APIRouter()

config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "config", "settings.yaml")
try:
    with open(config_path, "r", encoding="utf-8") as f:
        settings = yaml.safe_load(f)
        OLLAMA_API_URL = settings.get("llm", {}).get("ollama_url", "http://localhost:11434")
        OLLAMA_MODEL = settings.get("llm", {}).get("default_model", "qwen2.5:3b")
except Exception:
    OLLAMA_API_URL = "http://localhost:11434"
    OLLAMA_MODEL = "qwen2.5:3b"

def get_chat_service(request: Request):
    return getattr(request.app.state, "chat_service", None)

@router.get("/health")
async def health(chat_service=Depends(get_chat_service)):
    """Verify backend health and check connections."""
    backend_status = "offline"
    backend_type = "ollama"
    available_models = []
    
    # 1. Check Llama.cpp first
    try:
        r = requests.get("http://localhost:8080/health", timeout=1)
        if r.status_code == 200:
            backend_status = "online"
            backend_type = "llamacpp"
    except Exception:
        pass
        
    # 2. Check Ollama if Llama.cpp is offline
    if backend_status == "offline":
        try:
            r = requests.get(f"{OLLAMA_API_URL}/api/tags", timeout=1)
            if r.status_code == 200:
                backend_type = "ollama"
                backend_status = "online"
                models_data = r.json()
                available_models = [m["name"] for m in models_data.get("models", [])]
        except Exception:
            try:
                r = requests.get(f"{OLLAMA_API_URL}/health", timeout=1)
                if r.status_code == 200:
                    backend_type = "llamacpp"
                    backend_status = "online"
            except Exception:
                pass
                
    kb_loaded = False
    kb_records = 0
    if chat_service and hasattr(chat_service.retriever, "documents"):
        kb_loaded = len(chat_service.retriever.documents) > 0
        kb_records = len(chat_service.retriever.documents)
    
    return {
        "status": "healthy",
        "database_loaded": kb_loaded,
        "database_records": kb_records,
        "backend_type": backend_type,
        "backend_connection": backend_status,
        # Legacy keys for frontend compatibility
        "ollama_connection": backend_status,
        "ollama_url": OLLAMA_API_URL,
        "ollama_model": "Qwen 2.5 3B (Llama.cpp GPU)" if backend_type == "llamacpp" else OLLAMA_MODEL,
        "ollama_model_available": OLLAMA_MODEL in available_models or f"{OLLAMA_MODEL}:latest" in available_models,
        "available_models": available_models
    }
