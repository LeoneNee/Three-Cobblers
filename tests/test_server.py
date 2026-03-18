# tests/test_server.py
"""测试 MCP Server 模块"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from consensus_engine.server import create_server, run_consensus_debate
from consensus_engine.config import ModelConfig
from consensus_engine.writer import ConsensusOutput


@pytest.fixture
def mock_models():
    """创建模拟模型配置"""
    return [
        ModelConfig(
            name="model-a",
            url="https://api.example.com/v1/chat/completions",
            key="sk-test-a",
            provider="openai",
            timeout=60,
            max_retries=2,
        ),
        ModelConfig(
            name="model-b",
            url="https://api.example.com/v1/chat/completions",
            key="sk-test-b",
            provider="openai",
            timeout=60,
            max_retries=2,
        ),
        ModelConfig(
            name="judge",
            url="https://api.example.com/v1/chat/completions",
            key="sk-test-judge",
            provider="openai",
            timeout=60,
            max_retries=2,
        ),
    ]


@pytest.fixture
def mock_consensus_output():
    """创建模拟的共识输出"""
    return ConsensusOutput(
        final_consensus="最终共识：根据业务规模选择架构",
        debate_summary="## 讨论摘要\n\n### 提案阶段\n\n**model-a**: 微服务架构\n\n**model-b**: 单体架构",
        rounds_executed=3,
        models_participated=["model-a", "model-b"],
        total_duration_ms=1500,
        proposals={
            "model-a": "微服务架构提案",
            "model-b": "单体架构提案",
        },
        critiques={
            "model-a": "对单体架构的评审",
            "model-b": "对微服务架构的评审",
        },
        metadata={
            "scene": "arch",
            "judge_model": "judge",
        },
    )


def test_create_server():
    """测试创建 FastMCP 服务器实例"""
    server = create_server()

    assert server is not None
    assert hasattr(server, "run")
    # 验证服务器名称
    assert server.name == "consensus-engine"


@pytest.mark.asyncio
async def test_run_consensus_debate_success(mock_models, mock_consensus_output, tmp_path):
    """测试成功运行共识辩论"""
    # Mock ConfigManager
    with patch("consensus_engine.server.ConfigManager") as mock_config_mgr:
        mock_config_mgr.return_value.get_models.return_value = mock_models

        # Mock DebateOrchestrator
        with patch("consensus_engine.server.DebateOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_debate.return_value = mock_consensus_output
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock ResultWriter
            with patch("consensus_engine.server.ResultWriter") as mock_writer_class:
                mock_writer = MagicMock()
                mock_writer.write.return_value = str(tmp_path / "output.md")
                mock_writer_class.return_value = mock_writer

                # 调用函数
                result = await run_consensus_debate(
                    task="如何设计一个高可用的系统？",
                    scene="arch",
                    content="考虑成本和维护性",
                    output_dir=str(tmp_path),
                )

                # 验证结果
                assert result is not None
                assert "最终共识" in result
                assert "讨论摘要" in result
                assert "微服务架构" in result
                assert "单体架构" in result
                assert "统计信息" in result

                # 验证调用
                mock_config_mgr.return_value.get_models.assert_called_once()
                mock_orchestrator.run_debate.assert_called_once()
                mock_writer.write.assert_called_once()


@pytest.mark.asyncio
async def test_run_consensus_debate_with_defaults(mock_models, mock_consensus_output):
    """测试使用默认参数运行共识辩论"""
    with patch("consensus_engine.server.ConfigManager") as mock_config_mgr:
        mock_config_mgr.return_value.get_models.return_value = mock_models

        with patch("consensus_engine.server.DebateOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_debate.return_value = mock_consensus_output
            mock_orchestrator_class.return_value = mock_orchestrator

            with patch("consensus_engine.server.ResultWriter") as mock_writer_class:
                mock_writer = MagicMock()
                mock_writer.write.return_value = "/tmp/output.md"
                mock_writer_class.return_value = mock_writer

                # 使用默认参数调用
                result = await run_consensus_debate(
                    task="测试任务",
                )

                # 验证默认值
                assert result is not None
                mock_orchestrator_class.assert_called_once()
                # 验证 scene 默认值为 "planning"
                call_kwargs = mock_orchestrator_class.call_args[1]
                assert call_kwargs["scene"] == "planning"


@pytest.mark.asyncio
async def test_run_consensus_debate_no_proposals(mock_models):
    """测试所有模型调用失败的情况"""
    from consensus_engine.writer import ConsensusOutput

    # 创建没有提案的输出
    failed_output = ConsensusOutput(
        final_consensus="无法生成共识：所有模型调用失败",
        debate_summary="所有模型调用失败",
        rounds_executed=0,
        models_participated=[],
        total_duration_ms=100,
    )

    with patch("consensus_engine.server.ConfigManager") as mock_config_mgr:
        mock_config_mgr.return_value.get_models.return_value = mock_models

        with patch("consensus_engine.server.DebateOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_debate.return_value = failed_output
            mock_orchestrator_class.return_value = mock_orchestrator

            with patch("consensus_engine.server.ResultWriter") as mock_writer_class:
                mock_writer = MagicMock()
                mock_writer.write.return_value = "/tmp/failed.md"
                mock_writer_class.return_value = mock_writer

                result = await run_consensus_debate(
                    task="测试任务",
                    scene="planning",
                )

                # 验证错误消息被返回
                assert "无法生成共识" in result
                assert "所有模型调用失败" in result


@pytest.mark.asyncio
async def test_run_consensus_debate_file_output(mock_models, mock_consensus_output, tmp_path):
    """测试文件输出功能"""
    output_dir = tmp_path / "docs"
    output_dir.mkdir()

    with patch("consensus_engine.server.ConfigManager") as mock_config_mgr:
        mock_config_mgr.return_value.get_models.return_value = mock_models

        with patch("consensus_engine.server.DebateOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_debate.return_value = mock_consensus_output
            mock_orchestrator_class.return_value = mock_orchestrator

            # 真正的 ResultWriter，测试文件写入
            from consensus_engine.writer import ResultWriter

            with patch("consensus_engine.server.ResultWriter", ResultWriter):
                result = await run_consensus_debate(
                    task="测试文件输出",
                    scene="planning",
                    output_dir=str(output_dir),
                )

                # 验证文件被创建
                assert result is not None
                # 检查 docs/planning 目录下有文件
                planning_dir = output_dir / "plans"
                assert planning_dir.exists()
                files = list(planning_dir.glob("*.md"))
                assert len(files) > 0

                # 验证文件内容
                content = files[0].read_text(encoding="utf-8")
                assert "最终共识" in content
                assert "根据业务规模选择架构" in content


def test_server_has_required_tools():
    """测试服务器创建成功"""
    server = create_server()

    # 验证服务器实例
    assert server is not None
    assert server.name == "consensus-engine"


def test_server_tool_metadata():
    """测试工具函数具有正确的元数据"""
    # 验证函数存在且具有文档字符串
    assert run_consensus_debate.__doc__ is not None
    assert (
        "共识" in run_consensus_debate.__doc__ or "debate" in run_consensus_debate.__doc__.lower()
    )


@pytest.mark.asyncio
async def test_run_consensus_debate_custom_scene(mock_models, mock_consensus_output):
    """测试自定义场景"""
    with patch("consensus_engine.server.ConfigManager") as mock_config_mgr:
        mock_config_mgr.return_value.get_models.return_value = mock_models

        with patch("consensus_engine.server.DebateOrchestrator") as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator.run_debate.return_value = mock_consensus_output
            mock_orchestrator_class.return_value = mock_orchestrator

            with patch("consensus_engine.server.ResultWriter") as mock_writer_class:
                mock_writer = MagicMock()
                mock_writer.write.return_value = "/tmp/debug.md"
                mock_writer_class.return_value = mock_writer

                # 使用 debug 场景
                result = await run_consensus_debate(
                    task="如何调试这个bug？",
                    scene="debug",
                )

                # 验证 orchestrator 使用了正确的场景
                call_kwargs = mock_orchestrator_class.call_args[1]
                assert call_kwargs["scene"] == "debug"
                assert result is not None
