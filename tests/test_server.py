import json
import pytest
from unittest.mock import patch, AsyncMock
from consensus_engine.server import create_app


VALID_CONFIGS = json.dumps([
    {
        "name": "judge",
        "endpoint": "https://api.test.com/v1/chat/completions",
        "api_key": "sk-j",
        "model": "j-v1",
        "role": "judge",
    },
    {
        "name": "model-a",
        "endpoint": "https://api.a.com/v1/chat/completions",
        "api_key": "sk-a",
        "model": "a-v1",
    },
])


class TestCreateApp:
    def test_returns_mcp_instance(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", VALID_CONFIGS)
        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        app = create_app()
        assert app is not None
