# tests/test_config.py
import pytest
from pydantic import ValidationError
from consensus_engine.config import ModelConfig, ConfigManager


def test_model_config_valid():
    """测试有效的模型配置"""
    config = ModelConfig(name="test-model", url="https://api.example.com/v1/chat", key="sk-test")
    assert config.name == "test-model"
    assert config.provider == "openai"  # default
    assert config.timeout == 60  # default


def test_model_config_missing_required():
    """测试缺少必填字段的模型配置"""
    with pytest.raises(ValidationError):
        ModelConfig(name="test", url="https://example.com")
    # missing 'key'


def test_config_manager_from_env(monkeypatch):
    """测试从环境变量加载配置"""
    import json

    models_json = json.dumps([{"name": "model1", "url": "https://api1.com", "key": "key1"}])
    monkeypatch.setenv("MCP_MODELS", models_json)

    manager = ConfigManager()
    models = manager.get_models()
    assert len(models) == 1
    assert models[0].name == "model1"


def test_config_manager_fallback_to_file(tmp_path, monkeypatch):
    """测试回退到配置文件加载"""
    # No env var
    monkeypatch.delenv("MCP_MODELS", raising=False)

    # Create config file
    config_file = tmp_path / "config.json"
    config_file.write_text('[{"name": "model2", "url": "https://api2.com", "key": "key2"}]')

    manager = ConfigManager(config_path=str(config_file))
    models = manager.get_models()
    assert len(models) == 1
    assert models[0].name == "model2"


def test_config_manager_no_config_no_file(monkeypatch, tmp_path, capsys):
    """测试无配置且无文件时的错误处理"""
    monkeypatch.delenv("MCP_MODELS", raising=False)
    manager = ConfigManager(config_path=str(tmp_path / "nonexistent.json"))

    with pytest.raises(SystemExit):
        manager.get_models()

    captured = capsys.readouterr()
    assert "配置错误" in captured.err or "缺少模型配置" in captured.err
