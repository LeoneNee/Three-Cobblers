"""FastMCP 服务器入口。"""

import os
import sys
from typing import Literal

from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers

from consensus_engine.config import load_model_configs
from consensus_engine.orchestrator import run_debate

# 默认冷门端口
DEFAULT_PORT = 38517


class AuthMiddleware(Middleware):
    """API Key 验证中间件。"""

    def __init__(self, required_key: str):
        self.required_key = required_key

    async def on_request(self, context: MiddlewareContext, call_next):
        headers = get_http_headers()
        auth_header = headers.get("authorization", "")

        if not auth_header.startswith("Bearer "):
            raise PermissionError("Missing or invalid Authorization header")

        token = auth_header[7:]
        if token != self.required_key:
            raise PermissionError("Invalid API key")

        return await call_next(context)


def create_app() -> FastMCP:
    """创建并配置 FastMCP 应用实例。"""
    configs = load_model_configs()

    model_names = [c.name for c in configs]
    judge_name = next(c.name for c in configs if c.role == "judge")
    print(
        f"[consensus-engine] 已加载 {len(configs)} 个模型：{model_names}，Judge：{judge_name}",
        file=sys.stderr,
    )

    mcp = FastMCP("consensus-engine")

    # 添加 API Key 验证中间件
    api_key = os.environ.get("MCP_API_KEY")
    if api_key:
        print(f"[consensus-engine] API Key 验证已启用", file=sys.stderr)
        mcp.add_middleware(AuthMiddleware(required_key=api_key))
    else:
        print(f"[consensus-engine] 警告：未设置 MCP_API_KEY，服务无验证", file=sys.stderr)

    @mcp.tool()
    async def run_consensus_debate(
        task: str,
        content: str,
        scene: Literal["planning", "review", "arch", "debug"],
        review_mode: Literal["summarized", "full"] = "summarized",
    ) -> dict:
        """运行多模型共识博弈。

        并发调用多个 AI 模型进行三阶段博弈（提案→评审→汇总），
        返回共识方案，由调用方负责本地存档。

        Args:
            task: 核心任务描述
            content: 相关代码或上下文
            scene: 场景类型 (planning/review/arch/debug)
            review_mode: 评审模式 (summarized/full)，默认 summarized
        """
        result = await run_debate(
            configs=configs,
            task=task,
            content=content,
            scene=scene,
            review_mode=review_mode,
        )

        return {
            "final_plan": result.final_plan,
            "models_participated": result.models_participated,
            "models_failed": result.models_failed,
            "proposals": result.proposals,
            "reviews": result.reviews,
        }

    return mcp


def main():
    app = create_app()
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    if transport == "sse":
        port = int(os.environ.get("MCP_PORT", DEFAULT_PORT))
        host = os.environ.get("MCP_HOST", "0.0.0.0")
        print(f"[consensus-engine] SSE 模式启动 → {host}:{port}", file=sys.stderr)
        app.run(transport="sse", host=host, port=port)
    else:
        app.run(transport="stdio")


if __name__ == "__main__":
    main()
