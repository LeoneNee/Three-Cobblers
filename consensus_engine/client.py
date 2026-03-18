"""异步模型客户端：统一 OpenAI Chat Completions 兼容接口。"""

import sys
import httpx
from consensus_engine.config import ModelConfig


class ModelClient:
    """单个模型的异步 HTTP 客户端。"""

    def __init__(self, config: ModelConfig, timeout: float = 60.0):
        self.config = config
        self.timeout = timeout

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发送 chat completion 请求，返回模型回复文本。"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as http:
            print(
                f"[consensus-engine] 请求 {self.config.name}...",
                file=sys.stderr,
            )
            resp = await http.post(
                self.config.endpoint, json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(
                f"[consensus-engine] {self.config.name} 响应完成",
                file=sys.stderr,
            )
            return content
