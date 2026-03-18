# consensus_engine/client.py
import asyncio
from dataclasses import dataclass
from typing import Optional

import httpx

from consensus_engine.config import ModelConfig


@dataclass
class ModelResponse:
    """模型响应结果"""
    content: str
    model_name: str
    error: Optional[str] = None


class ModelClient:
    """模型客户端，支持重试机制"""

    def __init__(self, model: ModelConfig):
        self.model = model
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=self.model.timeout,
                headers={
                    "Authorization": f"Bearer {self.model.key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def call(self, prompt: str, system_prompt: str = "") -> ModelResponse:
        """调用模型 API，支持自动重试

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            ModelResponse: 包含响应内容、模型名称和错误信息
        """
        client = await self._get_client()
        last_error = None

        # 构建请求体
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self.model.name,
            "messages": messages,
        }

        # 重试逻辑
        for attempt in range(self.model.max_retries + 1):
            try:
                response = await client.post(
                    self.model.url,
                    json=payload,
                )
                response.raise_for_status()

                # 解析 OpenAI 格式响应
                data = response.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

                return ModelResponse(
                    content=content,
                    model_name=self.model.name,
                    error=None,
                )

            except httpx.HTTPStatusError as e:
                last_error = f"HTTP {e.response.status_code}: {e.response.text}"
                if attempt < self.model.max_retries:
                    # 指数退避：2^attempt 秒
                    backoff = 2**attempt
                    await asyncio.sleep(backoff)
                else:
                    return ModelResponse(
                        content="",
                        model_name=self.model.name,
                        error=last_error,
                    )

            except (httpx.RequestError, httpx.TimeoutException) as e:
                last_error = f"Request error: {str(e)}"
                if attempt < self.model.max_retries:
                    backoff = 2**attempt
                    await asyncio.sleep(backoff)
                else:
                    return ModelResponse(
                        content="",
                        model_name=self.model.name,
                        error=last_error,
                    )

        # 理论上不会到达这里，但为了类型安全
        return ModelResponse(
            content="",
            model_name=self.model.name,
            error=last_error or "Unknown error",
        )

    async def close(self):
        """关闭 HTTP 客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
