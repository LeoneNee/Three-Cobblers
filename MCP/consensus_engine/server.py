"""FastMCP 服务器入口 - 使用标准 MCP HTTP 传输。"""

import os
import sys
from typing import Literal

import uvicorn
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from consensus_engine.config import load_model_configs
from consensus_engine.orchestrator import run_debate

# 默认端口
DEFAULT_PORT = 38517


class AuthMiddleware(BaseHTTPMiddleware):
    """API Key 验证中间件。"""

    def __init__(self, app, required_key: str):
        super().__init__(app)
        self.required_key = required_key

    async def dispatch(self, request: Request, call_next):
        auth_header = request.headers.get("authorization", "")

        # 尝试从 URL 参数获取（用于 SSE 模式）
        if not auth_header.startswith("Bearer "):
            token_param = request.query_params.get("token", "")
            if token_param:
                auth_header = f"Bearer {token_param}"

        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "Missing or invalid Authorization header"},
                status_code=401
            )

        token = auth_header[7:]
        if token != self.required_key:
            return JSONResponse(
                {"error": "Invalid API key"},
                status_code=403
            )

        return await call_next(request)


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

    @mcp.custom_route("/health", methods=["GET"])
    async def health_check(request):
        """健康检查端点。"""
        return JSONResponse({"status": "healthy", "service": "consensus-engine"})

    return mcp


# 创建 FastMCP 实例
mcp = create_app()

# 获取 API Key
api_key = os.environ.get("MCP_API_KEY")

# 创建 ASGI 应用
app = mcp.http_app()

# 添加认证中间件（如果设置了 API Key）
if api_key:
    print(f"[consensus-engine] API Key 验证已启用", file=sys.stderr)
    app.add_middleware(AuthMiddleware, required_key=api_key)
else:
    print(f"[consensus-engine] 警告：未设置 MCP_API_KEY，服务无验证", file=sys.stderr)


def main():
    """启动 HTTP 服务器。"""
    port = int(os.environ.get("MCP_PORT", DEFAULT_PORT))
    host = os.environ.get("MCP_HOST", "0.0.0.0")
    transport = os.environ.get("MCP_TRANSPORT", "http")

    if transport == "sse":
        print(f"[consensus-engine] MCP SSE 服务启动 → {host}:{port}/sse", file=sys.stderr)
        mcp.run(transport="sse", host=host, port=port)
    else:
        print(f"[consensus-engine] MCP HTTP 服务启动 → {host}:{port}/mcp", file=sys.stderr)
        uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    main()
