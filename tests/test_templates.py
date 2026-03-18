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


def test_template_registry_has_scene():
    """测试has_scene方法"""
    registry = TemplateRegistry()

    # 测试已存在的场景
    assert registry.has_scene("planning") is True
    assert registry.has_scene("review") is True
    assert registry.has_scene("arch") is True
    assert registry.has_scene("debug") is True

    # 测试不存在的场景
    assert registry.has_scene("invalid") is False
    assert registry.has_scene("") is False
    assert registry.has_scene("nonexistent") is False


def test_template_registry_register_template():
    """测试register_template方法"""
    registry = TemplateRegistry()

    # 测试注册新模板
    registry.register_template("custom", "自定义模板内容")
    assert registry.has_scene("custom") is True
    assert registry.get_prompt("custom") == "自定义模板内容"

    # 测试更新已存在的模板
    registry.register_template("planning", "更新后的planning模板")
    assert registry.get_prompt("planning") == "更新后的planning模板"

    # 测试注册后的模板出现在支持列表中
    scenes = registry.get_supported_scenes()
    assert "custom" in scenes

    # 测试多个自定义模板
    registry.register_template("scene1", "模板1")
    registry.register_template("scene2", "模板2")
    assert registry.has_scene("scene1") is True
    assert registry.has_scene("scene2") is True
    assert len(registry.get_supported_scenes()) >= 6  # 原始4个 + 3个新注册的
