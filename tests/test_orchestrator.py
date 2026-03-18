# tests/test_orchestrator.py
"""测试辩论编排器模块"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch, AsyncMock as MockAsyncMock
from dataclasses import asdict

import pytest

from consensus_engine.orchestrator import DebateOrchestrator, ConsensusInput
from consensus_engine.client import ModelClient, ModelResponse
from consensus_engine.config import ModelConfig
from consensus_engine.writer import ConsensusOutput


class MockModelClient:
    """模拟的 ModelClient，用于测试"""

    def __init__(self, model, response_map=None):
        self.model = model
        self.response_map = response_map or {}

    async def call(self, prompt: str, system_prompt: str = "") -> ModelResponse:
        """模拟调用，根据模型名称返回预设响应"""
        response = self.response_map.get(self.model.name)
        if response:
            if isinstance(response, Exception):
                raise response
            return response
        return ModelResponse(
            content="",
            model_name=self.model.name,
            error="Mock not configured",
        )

    async def close(self):
        """模拟关闭"""
        pass


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
def mock_orchestrator(mock_models):
    """创建模拟的编排器实例"""
    return DebateOrchestrator(models=mock_models, scene="planning")


def create_mock_client_factory(response_map):
    """创建模拟客户端工厂"""
    def factory(model):
        return MockModelClient(model, response_map)
    return factory


@pytest.mark.asyncio
async def test_consensus_input_creation():
    """测试 ConsensusInput 数据类的创建"""
    input_data = ConsensusInput(
        task="如何设计一个高可用的系统？",
        scene="arch",
    )

    assert input_data.task == "如何设计一个高可用的系统？"
    assert input_data.scene == "arch"
    assert input_data.content == ""


@pytest.mark.asyncio
async def test_orchestrator_initialization(mock_orchestrator):
    """测试编排器初始化"""
    assert len(mock_orchestrator.models) == 3
    assert mock_orchestrator.scene == "planning"
    assert mock_orchestrator.judge_index == 2  # 最后一个模型作为 judge


@pytest.mark.asyncio
async def test_round1_proposal_concurrent(mock_models):
    """测试第一轮：并发提案生成"""
    response_map = {
        "model-a": ModelResponse(
            content="Model A 的提案：使用微服务架构",
            model_name="model-a",
            error=None,
        ),
        "model-b": ModelResponse(
            content="Model B 的提案：使用单体架构",
            model_name="model-b",
            error=None,
        ),
    }

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="planning",
        client_factory=create_mock_client_factory(response_map),
    )

    proposals = await orchestrator._round1_proposal(
        question="设计一个高可用系统",
    )

    assert len(proposals) == 2
    assert "model-a" in proposals
    assert "model-b" in proposals
    assert "微服务架构" in proposals["model-a"]
    assert "单体架构" in proposals["model-b"]


@pytest.mark.asyncio
async def test_round2_critique_cross_review(mock_models):
    """测试第二轮：交叉评审"""
    proposals = {
        "model-a": "Model A 的提案：使用微服务架构",
        "model-b": "Model B 的提案：使用单体架构",
    }

    response_map = {
        "model-a": ModelResponse(
            content="Model A 对 Model B 的评审：单体架构可能难以扩展",
            model_name="model-a",
            error=None,
        ),
        "model-b": ModelResponse(
            content="Model B 对 Model A 的评审：微服务架构复杂度高",
            model_name="model-b",
            error=None,
        ),
    }

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="planning",
        client_factory=create_mock_client_factory(response_map),
    )

    critiques = await orchestrator._round2_critique(proposals)

    assert len(critiques) == 2
    assert "model-a" in critiques
    assert "model-b" in critiques
    # 验证交叉评审：A 评论 B 的提案
    assert "单体架构" in critiques["model-a"]
    # 验证交叉评审：B 评论 A 的提案
    assert "微服务架构" in critiques["model-b"]


@pytest.mark.asyncio
async def test_round3_consensus_synthesis(mock_models):
    """测试第三轮：共识合成"""
    proposals = {
        "model-a": "Model A 的提案：使用微服务架构",
        "model-b": "Model B 的提案：使用单体架构",
    }
    critiques = {
        "model-a": "Model A 对 Model B 的评审：单体架构可能难以扩展",
        "model-b": "Model B 对 Model A 的评审：微服务架构复杂度高",
    }

    response_map = {
        "judge": ModelResponse(
            content="综合建议：根据业务规模选择，小型项目用单体，大型项目用微服务",
            model_name="judge",
            error=None,
        ),
    }

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="planning",
        client_factory=create_mock_client_factory(response_map),
    )

    final_answer = await orchestrator._round3_consensus(
        question="设计一个高可用系统",
        proposals=proposals,
        critiques=critiques,
    )

    assert "综合建议" in final_answer
    assert "微服务" in final_answer
    assert "单体" in final_answer


@pytest.mark.asyncio
async def test_build_summary(mock_orchestrator):
    """测试讨论摘要构建"""
    proposals = {
        "model-a": "Model A 的提案：使用微服务架构",
        "model-b": "Model B 的提案：使用单体架构",
    }
    critiques = {
        "model-a": "Model A 对 Model B 的评审：单体架构可能难以扩展",
        "model-b": "Model B 对 Model A 的评审：微服务架构复杂度高",
    }

    summary = mock_orchestrator._build_summary(proposals, critiques)

    assert "提案" in summary
    assert "评审" in summary
    assert "model-a" in summary
    assert "model-b" in summary
    assert "微服务架构" in summary
    assert "单体架构" in summary


@pytest.mark.asyncio
async def test_call_model_error_handling(mock_models):
    """测试模型调用的错误处理"""
    response_map = {
        "model-a": ModelResponse(
            content="",
            model_name="model-a",
            error="HTTP 500: Internal Server Error",
        ),
    }

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="planning",
        client_factory=create_mock_client_factory(response_map),
    )

    result = await orchestrator._call_model(
        client=orchestrator._client_factory(mock_models[0]),
        prompt="测试问题",
        system_prompt="",
    )

    assert result is None  # 错误时返回 None


@pytest.mark.asyncio
async def test_run_debate_full_flow(mock_models):
    """测试完整的辩论流程"""
    input_data = ConsensusInput(
        task="如何设计一个高可用的系统？",
        scene="arch",
        content="考虑成本和维护性",
    )

    call_count = {"count": 0}
    call_lock = asyncio.Lock()

    async def mock_call(prompt: str, system_prompt: str = "") -> ModelResponse:
        async with call_lock:
            call_count["count"] += 1
            current_count = call_count["count"]

        # 第一轮：提案
        if current_count <= 2:
            if current_count == 1:
                return ModelResponse(
                    content="Model A 提案：微服务 + Kubernetes",
                    model_name="model-a",
                    error=None,
                )
            else:
                return ModelResponse(
                    content="Model B 提案：单体 + 负载均衡",
                    model_name="model-b",
                    error=None,
                )
        # 第二轮：评审
        elif current_count <= 4:
            if current_count == 3:
                return ModelResponse(
                    content="Model A 评审：单体方案在扩展性上有局限",
                    model_name="model-a",
                    error=None,
                )
            else:
                return ModelResponse(
                    content="Model B 评审：微服务方案运维成本高",
                    model_name="model-b",
                    error=None,
                )
        # 第三轮：共识
        else:
            return ModelResponse(
                content="最终共识：根据团队规模和业务复杂度选择架构方案",
                model_name="judge",
                error=None,
            )

    # 创建状态感知的 mock 客户端
    class StatefulMockClient:
        def __init__(self, model):
            self.model = model

        async def call(self, prompt: str, system_prompt: str = ""):
            return await mock_call(prompt, system_prompt)

        async def close(self):
            pass

    def factory(model):
        return StatefulMockClient(model)

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="arch",
        client_factory=factory,
    )

    result = await orchestrator.run_debate(input_data)

    assert isinstance(result, ConsensusOutput)
    assert result.final_consensus != ""
    assert result.rounds_executed == 3
    assert len(result.models_participated) == 2
    assert len(result.proposals) == 2
    assert len(result.critiques) == 2
    assert "微服务" in result.final_consensus or "最终共识" in result.final_consensus
    assert result.debate_summary != ""
    assert result.total_duration_ms >= 0


@pytest.mark.asyncio
async def test_run_debate_with_model_error(mock_models):
    """测试包含模型错误的辩论流程"""
    input_data = ConsensusInput(
        task="测试问题",
        scene="planning",
    )

    response_map = {
        "model-a": ModelResponse(
            content="",
            model_name="model-a",
            error="Connection timeout",
        ),
        "model-b": ModelResponse(
            content="Model B 的提案",
            model_name="model-b",
            error=None,
        ),
        "judge": ModelResponse(
            content="基于单一模型的共识",
            model_name="judge",
            error=None,
        ),
    }

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="planning",
        client_factory=create_mock_client_factory(response_map),
    )

    result = await orchestrator.run_debate(input_data)

    assert len(result.models_participated) == 1
    assert len(result.proposals) == 1
    assert "model-b" in result.proposals


@pytest.mark.asyncio
async def test_orchestrator_custom_scene(mock_models):
    """测试自定义场景"""
    response_map = {
        "model-a": ModelResponse(
            content="调试建议 A",
            model_name="model-a",
            error=None,
        ),
        "model-b": ModelResponse(
            content="调试建议 B",
            model_name="model-b",
            error=None,
        ),
    }

    orchestrator = DebateOrchestrator(
        models=mock_models,
        scene="debug",
        client_factory=create_mock_client_factory(response_map),
    )

    assert orchestrator.scene == "debug"

    # 验证场景模板被正确使用
    input_data = ConsensusInput(
        task="如何调试这个bug？",
        scene="debug",
    )

    proposals = await orchestrator._round1_proposal(question="如何调试这个bug？")

    assert len(proposals) == 2


@pytest.mark.asyncio
async def test_orchestrator_single_model():
    """测试只有一个模型的情况（边界情况）"""
    single_model = [
        ModelConfig(
            name="only-model",
            url="https://api.example.com/v1/chat/completions",
            key="sk-test",
            provider="openai",
        ),
        ModelConfig(
            name="judge",
            url="https://api.example.com/v1/chat/completions",
            key="sk-test-judge",
            provider="openai",
        ),
    ]

    response_map = {
        "only-model": ModelResponse(
            content="单一模型的提案",
            model_name="only-model",
            error=None,
        ),
    }

    orchestrator = DebateOrchestrator(
        models=single_model,
        scene="planning",
        client_factory=create_mock_client_factory(response_map),
    )

    proposals = await orchestrator._round1_proposal(question="测试问题")

    assert len(proposals) == 1
    assert "only-model" in proposals
