# tests/test_client.py
import pytest
import httpx
import respx
from consensus_engine.config import ModelConfig
from consensus_engine.client import ModelClient


@pytest.mark.asyncio
async def test_model_client_basic_call(respx_mock):
    model = ModelConfig(
        name="test-model", url="https://api.example.com/v1/chat/completions", key="sk-test"
    )
    respx.post("https://api.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(
            200, json={"choices": [{"message": {"content": "Test response"}}]}
        )
    )
    client = ModelClient(model)
    response = await client.call("Hello", system_prompt="You are helpful")
    assert response.content == "Test response"
    assert response.model_name == "test-model"
    assert response.error is None


@pytest.mark.asyncio
async def test_model_client_retry_on_failure(respx_mock):
    model = ModelConfig(
        name="test-model",
        url="https://api.example.com/v1/chat/completions",
        key="sk-test",
        max_retries=2,
    )
    route = respx.post("https://api.example.com/v1/chat/completions")
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(200, json={"choices": [{"message": {"content": "Success"}}]}),
    ]
    client = ModelClient(model)
    response = await client.call("Hello")
    assert response.content == "Success"
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_model_client_exhausted_retries(respx_mock):
    model = ModelConfig(
        name="test-model",
        url="https://api.example.com/v1/chat/completions",
        key="sk-test",
        max_retries=1,
    )
    respx.post("https://api.example.com/v1/chat/completions").mock(return_value=httpx.Response(500))
    client = ModelClient(model)
    response = await client.call("Hello")
    assert response.content == ""
    assert response.error is not None
    assert "500" in response.error
