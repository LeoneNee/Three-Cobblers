"""FastMCP 服务器入口。"""

import sys
from typing import Literal

from fastmcp import FastMCP

from consensus_engine.config import load_model_configs, load_project_root
from consensus_engine.orchestrator import run_debate
from consensus_engine.writer import write_consensus


def create_app() -> FastMCP:
    """创建并配置 FastMCP 应用实例。"""
    configs = load_model_configs()
    project_root = load_project_root()

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
        输出共识方案并自动存档到本地 docs/ 目录。

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

        filepath = write_consensus(
            project_root=project_root,
            scene=scene,
            task=task,
            models=result.models_participated,
            final_plan=result.final_plan,
            proposals=result.proposals,
            reviews=result.reviews,
        )

        relative_path = filepath.relative_to(project_root)
        print(
            f"[Done] 共识结论已保存至 {relative_path}",
            file=sys.stderr,
        )

        return {
            "final_plan": result.final_plan,
            "file_path": str(relative_path),
            "models_participated": result.models_participated,
            "models_failed": result.models_failed,
        }

    return mcp


def main():
    app = create_app()
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
