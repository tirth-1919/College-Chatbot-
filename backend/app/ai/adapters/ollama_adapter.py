import os
import time
from typing import Dict, Any, List, Optional
import httpx
from backend.app.ai.provider_base import BaseAIProvider, AIProviderResponse

class OllamaProvider(BaseAIProvider):
    def __init__(self, base_url: Optional[str] = None):
        super().__init__(provider_name="ollama", base_url=base_url or os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    async def generate_response(
        self,
        model_name: str,
        prompt: str,
        system_instruction: str,
        evidence: Optional[List[Dict[str, Any]]] = None,
        context_history: Optional[List[Dict[str, str]]] = None,
        images: Optional[List[str]] = None
    ) -> AIProviderResponse:
        start_time = time.time()
        user_content = prompt
        if evidence:
            context_str = "\n\nVERIFIED AIT EVIDENCE:\n" + "\n".join([
                f"- {e.get('name', '')}: {e.get('details', '')}" for e in evidence
            ])
            user_content += context_str

        async with httpx.AsyncClient(timeout=45.0) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model_name or "llama3",
                    "system": system_instruction,
                    "messages": [{"role": "user", "content": user_content}],
                    "stream": False
                }
            )
            resp.raise_for_status()
            data = resp.json()

        latency = (time.time() - start_time) * 1000
        text = data.get("message", {}).get("content", "")

        return AIProviderResponse(
            content=text,
            input_tokens=data.get("prompt_eval_count", len(user_content) // 4),
            output_tokens=data.get("eval_count", len(text) // 4),
            latency_ms=round(latency, 2),
            model_name=model_name,
            provider_name=self.provider_name
        )

    async def health_check(self, model_name: str) -> bool:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/version")
                return res.status_code == 200
        except Exception:
            return False
