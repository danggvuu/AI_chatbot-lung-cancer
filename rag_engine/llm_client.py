import json
import httpx
from typing import AsyncGenerator

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:3b"):
        self.base_url = base_url
        self.model = model
        
    async def generate_stream(self, messages: list[dict], temperature: float = 0.1, **kwargs) -> AsyncGenerator[str, None]:
        """Gửi request tới Ollama API theo dạng stream."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "options": {
                "temperature": temperature,
                "num_predict": kwargs.get("num_predict", 500),
                "num_ctx": kwargs.get("num_ctx", 4096)
            }
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield json.dumps({"error": f"Ollama error: {response.status_code}"})
                    return
                    
                async for line in response.aiter_lines():
                    if line:
                        try:
                            data = json.loads(line)
                            if "message" in data and "content" in data["message"]:
                                content = data["message"]["content"]
                                yield content
                        except json.JSONDecodeError:
                            pass
                            
    async def generate(self, messages: list[dict], temperature: float = 0.1, **kwargs) -> str:
        """Gửi request đồng bộ tới Ollama API (không stream)."""
        url = f"{self.base_url}/api/chat"
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": kwargs.get("num_predict", 500),
                "num_ctx": kwargs.get("num_ctx", 4096)
            }
        }
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data.get("message", {}).get("content", "")
            else:
                raise Exception(f"Ollama error: {response.status_code} - {response.text}")
