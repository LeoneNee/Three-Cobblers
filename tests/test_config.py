import json
import os
import pytest
from consensus_engine.config import load_model_configs, load_project_root, ModelConfig


VALID_CONFIGS = [
    {
        "name": "deepseek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "api_key": "sk-test1",
        "model": "deepseek-chat",
        "role": "judge",
    },
    {
        "name": "qwen",
        "endpoint": "https://api.qwen.com/v1/chat/completions",
        "api_key": "sk-test2",
        "model": "qwen-plus",
    },
]


class TestLoadModelConfigs:
    def test_valid_configs(self, monkeypatch):
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(VALID_CONFIGS))
        configs = load_model_configs()
        assert len(configs) == 2
        assert configs[0].name == "deepseek"
        assert configs[0].role == "judge"
        assert configs[1].role == "participant"

    def test_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("LOCAL_MODEL_CONFIGS", raising=False)
        with pytest.raises(SystemExit):
            load_model_configs()

    def test_less_than_two_models(self, monkeypatch):
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps([VALID_CONFIGS[0]]))
        with pytest.raises(ValueError, match="至少需要 2 个模型"):
            load_model_configs()

    def test_no_judge(self, monkeypatch):
        configs_no_judge = [
            {**c, "role": "participant"} if "role" in c else c
            for c in VALID_CONFIGS
        ]
        for c in configs_no_judge:
            c.pop("role", None)
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(configs_no_judge))
        with pytest.raises(ValueError, match="恰好需要 1 个 judge"):
            load_model_configs()

    def test_multiple_judges(self, monkeypatch):
        configs_two_judges = [
            {**c, "role": "judge"} for c in VALID_CONFIGS
        ]
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(configs_two_judges))
        with pytest.raises(ValueError, match="恰好需要 1 个 judge"):
            load_model_configs()

    def test_missing_required_field(self, monkeypatch):
        bad = [{"name": "x"}, VALID_CONFIGS[1]]
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(bad))
        with pytest.raises(ValueError):
            load_model_configs()


class TestLoadProjectRoot:
    def test_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        assert load_project_root() == tmp_path

    def test_fallback_to_cwd(self, monkeypatch):
        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        result = load_project_root()
        assert result.exists()
