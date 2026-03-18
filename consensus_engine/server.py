# consensus_engine/server.py
"""MCP Server 模块 - FastMCP 服务器实现

本模块实现了基于 FastMCP 的 MCP 服务器，提供 run_consensus_debate 工具。
"""

import argparse

from fastmcp import FastMCP

from consensus_engine.config import ConfigManager
from consensus_engine.orchestrator import DebateOrchestrator, ConsensusInput
from consensus_engine.writer import ResultWriter


async def run_consensus_debate(
    task: str,
    scene: str = "planning",
    content: str = "",
    output_dir: str = "docs",
) -> str:
    """运行多模型共识辩论

    通过多模型三轮辩论（提案 -> 评审 -> 共识）生成高质量的共识答案。

    Args:
        task: 需要讨论的任务或问题
        scene: 场景类型（planning, review, arch, debug），默认为 planning
        content: 额外的上下文信息，可选
        output_dir: 输出目录，默认为 docs

    Returns:
        str: 格式化的 Markdown 结果，包含最终共识、讨论摘要和统计信息
    """
    # 1. 加载模型配置
    config_manager = ConfigManager()
    models = config_manager.get_models()

    # 2. 创建辩论编排器
    orchestrator = DebateOrchestrator(
        models=models,
        scene=scene,
    )

    # 3. 运行辩论流程
    input_data = ConsensusInput(
        task=task,
        scene=scene,
        content=content,
    )

    output = await orchestrator.run_debate(input_data)

    # 4. 写入结果文件
    writer = ResultWriter(root_dir=output_dir)
    output_path = writer.write(
        scene=scene,
        task=task,
        output=output,
    )

    # 5. 返回格式化的 Markdown 结果
    return _format_result(output, output_path)


def create_server() -> FastMCP:
    """创建 FastMCP 服务器实例

    Returns:
        FastMCP: 配置好的 MCP 服务器实例
    """
    # 创建 FastMCP 服务器
    mcp = FastMCP("consensus-engine")

    # 注册工具：运行共识辩论
    mcp.add_tool(run_consensus_debate)

    return mcp


def _format_result(output, output_path: str) -> str:
    """格式化输出结果为 Markdown

    Args:
        output: ConsensusOutput 实例
        output_path: 输出文件路径

    Returns:
        str: 格式化的 Markdown 文本
    """
    parts = [
        "## 共识结果已生成",
        "",
        f"**输出文件**: `{output_path}`",
        "",
        "---",
        "",
        "## 最终共识",
        "",
        output.final_consensus,
        "",
        "---",
        "",
        "## 讨论摘要",
        "",
        output.debate_summary,
        "",
        "---",
        "",
        "## 统计信息",
        "",
        f"- **执行轮数**: {output.rounds_executed}",
        f"- **参与模型**: {', '.join(output.models_participated)}",
        f"- **总耗时**: {output.total_duration_ms} ms",
    ]

    # 添加元数据
    if output.metadata:
        parts.append("")
        parts.append("## 元数据")
        parts.append("")
        for key, value in output.metadata.items():
            if isinstance(value, list):
                value_str = ", ".join(str(v) for v in value)
            else:
                value_str = str(value)
            parts.append(f"- **{key}**: {value_str}")

    return "\n".join(parts)


def main():
    """CLI 入口点

    启动 MCP 服务器，支持以下参数：
    --transport: 传输协议（stdio 或 sse），默认为 stdio
    --port: 端口号（仅用于 sse），默认为 8000
    --log-level: 日志级别（DEBUG, INFO, WARNING, ERROR），默认为 INFO
    """
    parser = argparse.ArgumentParser(description="Consensus Engine MCP Server - 多模型共识辩论服务")
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "sse"],
        help="传输协议：stdio（标准输入输出）或 sse（服务器发送事件）",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="端口号（仅用于 sse 传输）",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别",
    )

    args = parser.parse_args()

    # 创建服务器
    server = create_server()

    # 根据传输协议启动服务器
    if args.transport == "stdio":
        # stdio 模式：通过标准输入输出通信
        server.run(transport="stdio")
    elif args.transport == "sse":
        # sse 模式：通过 HTTP 服务器通信
        server.run(transport="sse", port=args.port, log_level=args.log_level)
    else:
        parser.error(f"不支持的传输协议: {args.transport}")


if __name__ == "__main__":
    main()
