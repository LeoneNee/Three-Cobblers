#!/usr/bin/env python3
"""Consensus-Engine MCP 示例测试脚本

本脚本演示如何使用 Consensus-Engine 进行多模型辩论。
"""

import asyncio
from consensus_engine.config import ModelConfig, ConfigManager
from consensus_engine.orchestrator import DebateOrchestrator, ConsensusInput
from consensus_engine.writer import ResultWriter


async def main():
    """主测试函数"""
    print("=" * 60)
    print("Consensus-Engine MCP 测试示例")
    print("=" * 60)

    # 方式一：使用模拟配置（用于测试）
    print("\n[1] 创建模拟模型配置...")
    mock_models = [
        ModelConfig(
            name="model-a",
            url="https://api.example.com/v1/chat/completions",
            key="test-key-a",
            provider="openai",
            timeout=60,
            max_retries=2
        ),
        ModelConfig(
            name="model-b",
            url="https://api.example.com/v1/chat/completions",
            key="test-key-b",
            provider="openai",
            timeout=60,
            max_retries=2
        ),
        ModelConfig(
            name="judge-model",
            url="https://api.example.com/v1/chat/completions",
            key="test-key-judge",
            provider="openai",
            timeout=60,
            max_retries=2
        )
    ]
    print(f"已创建 {len(mock_models)} 个模型配置")
    for model in mock_models:
        print(f"  - {model.name} ({model.provider})")

    # 方式二：从实际配置文件加载（注释掉，避免实际 API 调用）
    # print("\n[2] 从配置文件加载模型配置...")
    # config_manager = ConfigManager("config.json")
    # models = config_manager.get_models()
    # print(f"已加载 {len(models)} 个模型配置")

    print("\n[2] 创建辩论编排器...")
    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="planning",
        judge_index=-1  # 使用最后一个模型作为 judge
    )
    print(f"场景类型: {orchestrator.scene}")
    print(f"提案者模型: {[m.name for m in orchestrator.proposer_models]}")
    print(f"Judge 模型: {orchestrator.judge_model.name}")

    print("\n[3] 准备辩论输入...")
    input_data = ConsensusInput(
        task="设计一个微服务架构的电商平台后端系统",
        scene="planning",
        content="""
需求：
- 支持用户注册、登录、商品浏览、购物车、下单支付
- 需要高可用、可扩展
- 预期日活用户 10 万，峰值并发 1000
- 技术栈偏好：Python/Go + PostgreSQL + Redis
"""
    )
    print(f"任务: {input_data.task}")
    print(f"场景: {input_data.scene}")

    print("\n[4] 运行辩论流程...")
    print("提示：此示例使用模拟配置，实际使用时请配置真实的 API 端点")

    # 注意：由于使用模拟配置，实际运行会失败
    # 实际使用时，请配置真实的 API 密钥和端点
    try:
        output = await orchestrator.run_debate(input_data)

        print("\n[5] 辩论完成！")
        print(f"执行轮数: {output.rounds_executed}")
        print(f"参与模型: {', '.join(output.models_participated)}")
        print(f"总耗时: {output.total_duration_ms} ms")

        print("\n[6] 保存结果...")
        writer = ResultWriter(root_dir="docs")
        output_path = writer.write(
            scene=input_data.scene,
            task=input_data.task,
            output=output
        )
        print(f"结果已保存到: {output_path}")

        print("\n[7] 输出摘要:")
        print("-" * 60)
        print("最终共识:")
        print(output.final_consensus[:500] + "..." if len(output.final_consensus) > 500 else output.final_consensus)
        print("-" * 60)
        print("讨论摘要:")
        print(output.debate_summary[:500] + "..." if len(output.debate_summary) > 500 else output.debate_summary)
        print("-" * 60)

    except Exception as e:
        print(f"\n[错误] 辩论执行失败: {e}")
        print("提示：请确保配置了有效的 API 密钥和端点")

    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    # 运行异步主函数
    asyncio.run(main())
