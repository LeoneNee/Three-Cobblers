import httpx
import pytest
import respx
from consensus_engine.client import ModelClient
from consensus_engine.config import ModelConfig


@pytest.fixture
def model_config():
    return ModelConfig(
        name="test-model",
        endpoint="https://api.test.com/v1/chat/completions",
        api_key="sk-test",
        model="test-v1",
    )


@pytest.fixture
def client(model_config):
    return ModelClient(model_config, timeout=5.0)


class TestModelClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_success(self, client, model_config):
        respx.post(model_config.endpoint).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "test response"}}
                    ]
                },
            )
        )
        result = await client.chat("You are a helpful assistant.", "Hello")
        assert result == "test response"

    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_api_error(self, client, model_config):
        respx.post(model_config.endpoint).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat("system", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_timeout(self, client, model_config):
        respx.post(model_config.endpoint).mock(side_effect=httpx.ReadTimeout("timeout"))
        with pytest.raises(httpx.ReadTimeout):
            await client.chat("system", "user")
