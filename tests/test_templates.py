# tests/test_templates.py
from consensus_engine.templates import TemplateRegistry


def test_template_registry_planning():
    """测试planning场景模板"""
    registry = TemplateRegistry()
    prompt = registry.get_prompt("planning")
    assert "任务拆解" in prompt or "planning" in prompt.lower()


def test_template_registry_review():
    """测试review场景模板"""
    registry = TemplateRegistry()
    prompt = registry.get_prompt("review")
    assert "代码" in prompt or "review" in prompt.lower() or "bug" in prompt.lower()


def test_template_registry_arch():
    """测试arch场景模板"""
    registry = TemplateRegistry()
    prompt = registry.get_prompt("arch")
    assert "架构" in prompt or "architect" in prompt.lower() or "设计" in prompt


def test_template_registry_debug():
    """测试debug场景模板"""
    registry = TemplateRegistry()
    prompt = registry.get_prompt("debug")
    assert "调试" in prompt or "debug" in prompt.lower() or "问题" in prompt


def test_template_registry_invalid_scene():
    """测试无效场景返回默认模板"""
    registry = TemplateRegistry()
    prompt = registry.get_prompt("invalid")
    assert prompt is not None  # Should return default prompt


def test_template_registry_get_supported_scenes():
    """测试获取支持的场景列表"""
    registry = TemplateRegistry()
    scenes = registry.get_supported_scenes()
    assert isinstance(scenes, list)
    assert len(scenes) == 4
    assert "planning" in scenes
    assert "review" in scenes
    assert "arch" in scenes
    assert "debug" in scenes
