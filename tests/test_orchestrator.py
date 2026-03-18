import pytest
from unittest.mock import AsyncMock, patch
from consensus_engine.config import ModelConfig
from consensus_engine.orchestrator import run_debate, DebateResult


@pytest.fixture
def judge_config():
    return ModelConfig(
        name="judge-model",
        endpoint="https://api.test.com/v1/chat/completions",
        api_key="sk-j",
        model="judge-v1",
        role="judge",
    )


@pytest.fixture
def participant_configs():
    return [
        ModelConfig(
            name=f"model-{i}",
            endpoint=f"https://api.test{i}.com/v1/chat/completions",
            api_key=f"sk-{i}",
            model=f"test-v{i}",
        )
        for i in range(2)
    ]


@pytest.fixture
def all_configs(judge_config, participant_configs):
    return [judge_config] + participant_configs


class TestRunDebate:
    @pytest.mark.asyncio
    async def test_full_flow_returns_result(self, all_configs):
        with patch("consensus_engine.orchestrator.ModelClient") as MockClient:
            instance = AsyncMock()
            instance.chat.return_value = "mock response"
            instance.config = all_configs[0]
            MockClient.return_value = instance

            result = await run_debate(
                configs=all_configs,
                task="测试任务",
                content="测试上下文",
                scene="planning",
            )

            assert isinstance(result, DebateResult)
            assert result.final_plan == "mock response"
            assert len(result.models_participated) > 0
            assert result.models_failed == []

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self, all_configs):
        call_count = 0

        async def side_effect(system, user):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("model timeout")
            return "mock response"

        with patch("consensus_engine.orchestrator.ModelClient") as MockClient:
            instance = AsyncMock()
            instance.chat.side_effect = side_effect
            instance.config = all_configs[0]
            MockClient.return_value = instance

            result = await run_debate(
                configs=all_configs,
                task="测试任务",
                content="测试上下文",
                scene="planning",
            )
            assert isinstance(result, DebateResult)

    @pytest.mark.asyncio
    async def test_review_mode_parameter(self, all_configs):
        with patch("consensus_engine.orchestrator.ModelClient") as MockClient:
            instance = AsyncMock()
            instance.chat.return_value = "mock response"
            instance.config = all_configs[0]
            MockClient.return_value = instance

            result = await run_debate(
                configs=all_configs,
                task="t",
                content="c",
                scene="review",
                review_mode="full",
            )
            assert isinstance(result, DebateResult)
