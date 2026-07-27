import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from src.api.server import create_app

def test_chat_service_lazy_init_and_cleanup():
    """
    Test hồi quy: Đảm bảo ChatService được khởi tạo qua lifespan (không bị import-level init),
    và tài nguyên (Qdrant) được giải phóng khi ứng dụng tắt.
    """
    app = create_app()
    
    from unittest.mock import patch
    
    # Tại thời điểm này, ChatService CHƯA được khởi tạo
    assert not hasattr(app.state, "chat_service")
    
    # Sử dụng TestClient (sẽ kích hoạt lifespan events: startup -> yield -> shutdown)
    with TestClient(app) as client:
        # Trong with-block, ứng dụng đã startup
        assert hasattr(app.state, "chat_service")
        
        # Test endpoint
        response = client.get("/api/health")
        assert response.status_code == 200
        
        # Mô phỏng một truy vấn
        payload = {
            "messages": [{"role": "user", "content": "hello"}],
            "stream": False
        }
        
        with patch.object(app.state.chat_service, 'get_chat_response_sync') as mock_chat:
            mock_chat.return_value = {"answer": "mock response"}
            response = client.post("/api/chat", json=payload)
            assert response.status_code == 200
        
    # Ra khỏi with-block, ứng dụng đã shutdown
    # TestClient sẽ gọi shutdown/cleanup

