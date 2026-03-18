"""基础测试，验证项目结构正确设置"""
import pytest


def test_package_import():
    """验证包可以正常导入"""
    import consensus_engine

    assert consensus_engine is not None


def test_dependencies_available():
    """验证关键依赖可用"""
    # 验证核心依赖
    import fastmcp
    import httpx
    import pydantic
    import structlog

    assert fastmcp is not None
    assert httpx is not None
    assert pydantic is not None
    assert structlog is not None


def test_pydantic_version():
    """验证 Pydantic 版本 >= 2.0"""
    import pydantic

    # Pydantic v2 的 __version__ 属性
    version = getattr(pydantic, '__version__', '2.0.0')
    major_version = int(version.split('.')[0])
    assert major_version >= 2, f"需要 Pydantic >= 2.0，当前版本: {version}"


def test_project_metadata():
    """验证项目元数据"""
    import consensus_engine

    # 验证包有基本属性（可以后续添加）
    assert hasattr(consensus_engine, '__name__')
    assert consensus_engine.__name__ == 'consensus_engine'
