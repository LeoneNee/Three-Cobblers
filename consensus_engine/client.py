"""异步模型客户端：支持 OpenAI 和 Anthropic 两种协议。"""

import sys
import httpx
from consensus_engine.config import ModelConfig


class ModelClient:
    """单个模型的异步 HTTP 客户端。"""

    def __init__(self, config: ModelConfig, timeout: float = 120.0):
        self.config = config
        self.timeout = timeout

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发送 chat completion 请求，返回模型回复文本。"""
        if self.config.protocol == "anthropic":
            return await self._chat_anthropic(system_prompt, user_prompt)
        return await self._chat_openai(system_prompt, user_prompt)

    async def _chat_openai(self, system_prompt: str, user_prompt: str) -> str:
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
                f"[consensus-engine] 请求 {self.config.name} (openai)...",
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

    async def _chat_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as http:
            print(
                f"[consensus-engine] 请求 {self.config.name} (anthropic)...",
                file=sys.stderr,
            )
            url = self.config.endpoint.rstrip("/")
            if not url.endswith("/messages"):
                url += "/messages"
            resp = await http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            print(
                f"[consensus-engine] {self.config.name} 响应完成",
                file=sys.stderr,
            )
            return content
