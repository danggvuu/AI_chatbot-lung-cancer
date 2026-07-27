import json
import httpx
import os
import requests
from typing import AsyncGenerator

class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5:3b"):
        self.model = model
        self.backend = "ollama"
        self.backend_url = base_url
        
        self._detect_backend()

    def _detect_backend(self):
        # 1. Check if llama.cpp is running on port 8080
        try:
            r = requests.get("http://localhost:8080/health", timeout=0.5)
            if r.status_code == 200:
                self.backend = "llamacpp"
                self.backend_url = "http://localhost:8080"
                return
        except Exception:
            pass
            
        # 2. Check if llama.cpp is running on the provided base_url
        try:
            r = requests.get(f"{self.backend_url}/health", timeout=0.5)
            if r.status_code == 200:
                self.backend = "llamacpp"
                return
        except Exception:
            pass
            
        # 3. Check env override
        env_backend = os.environ.get("LLM_BACKEND")
        if env_backend in ["ollama", "llamacpp"]:
            self.backend = env_backend
            if self.backend == "llamacpp":
                self.backend_url = os.environ.get("LLAMACPP_API_URL", "http://localhost:8080").rstrip('/')

    def _build_payload(self, messages: list[dict], temperature: float, stream: bool, **kwargs):
        if self.backend == "llamacpp":
            return {
                "messages": messages,
                "temperature": temperature,
                "num_predict": kwargs.get("num_predict", 500),
                "max_tokens": kwargs.get("max_tokens", 500),
                "stream": stream,
                "top_k": kwargs.get("top_k", 20),
                "top_p": kwargs.get("top_p", 0.85)
            }
        else:
            return {
                "model": self.model,
                "messages": messages,
                "stream": stream,
                "options": {
                    "temperature": temperature,
                    "num_predict": kwargs.get("num_predict", 500),
                    "num_ctx": kwargs.get("num_ctx", 4096),
                    "top_k": kwargs.get("top_k", 20),
                    "top_p": kwargs.get("top_p", 0.85)
                }
            }

    async def generate_stream(self, messages: list[dict], temperature: float = 0.1, **kwargs) -> AsyncGenerator[str, None]:
        url = f"{self.backend_url}/v1/chat/completions" if self.backend == "llamacpp" else f"{self.backend_url}/api/chat"
        payload = self._build_payload(messages, temperature, stream=True, **kwargs)
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code != 200:
                    yield json.dumps({"error": f"{self.backend} error: {response.status_code}"})
                    return
                    
                async for line in response.aiter_lines():
                    if line:
                        decoded_line = line.strip()
                        if self.backend == "llamacpp":
                            if decoded_line.startswith("data: "):
                                data_content = decoded_line[len("data: "):]
                                if data_content == "[DONE]":
                                    break
                                try:
                                    json_line = json.loads(data_content)
                                    delta = json_line.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                    if delta:
                                        yield delta
                                except json.JSONDecodeError:
                                    pass
                        else:
                            try:
                                data = json.loads(decoded_line)
                                if "message" in data and "content" in data["message"]:
                                    yield data["message"]["content"]
                                if data.get("done", False):
                                    break
                            except json.JSONDecodeError:
                                pass
                            
    async def generate(self, messages: list[dict], temperature: float = 0.1, **kwargs) -> str:
        url = f"{self.backend_url}/v1/chat/completions" if self.backend == "llamacpp" else f"{self.backend_url}/api/chat"
        payload = self._build_payload(messages, temperature, stream=False, **kwargs)
        
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                data = response.json()
                if self.backend == "llamacpp":
                    return data.get("choices", [{}])[0].get("message", {}).get("content", "")
                else:
                    return data.get("message", {}).get("content", "")
            else:
                raise Exception(f"{self.backend} error: {response.status_code} - {response.text}")
