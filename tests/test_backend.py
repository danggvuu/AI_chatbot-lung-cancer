import pytest
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.llm.chat_service import ChatService
from src.api.server import create_app
from fastapi.testclient import TestClient

def test_app_creation():
    app = create_app()
    assert app is not None
    
def test_health_endpoint():
    app = create_app()
    with TestClient(app) as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
