# tests/test_writer.py
import pytest
from pathlib import Path
from consensus_engine.writer import ResultWriter, ConsensusOutput


@pytest.fixture
def sample_output():
    """创建测试用的 ConsensusOutput 实例"""
    return ConsensusOutput(
        question="Implement user authentication",
        final_answer="## Final Plan\n\nThis is the consensus.",
        total_models=2,
        successful_models=2,
        proposals={
            "model-a": "Proposal A content",
            "model-b": "Proposal B content",
        },
        critiques={
            "model-a": "Critique A content",
            "model-b": "Critique B content",
        },
        discussion_summary="Model A and B agreed on approach X.",
        metadata={
            "scene": "planning",
            "rounds_executed": 3,
            "models_participated": ["model-a", "model-b"],
            "total_duration_ms": 5000,
        },
    )


def test_writer_creates_directory(tmp_path, sample_output):
    """测试写入器创建目录"""
    writer = ResultWriter(root_dir=str(tmp_path))
    output_path = writer.write(
        scene="planning",
        task="Implement user authentication",
        output=sample_output,
    )
    assert Path(output_path).exists()
    assert "plans" in output_path


def test_writer_filename_format(tmp_path, sample_output):
    """测试文件名格式化（特殊字符处理）"""
    writer = ResultWriter(root_dir=str(tmp_path))
    output_path = writer.write(
        scene="review",
        task="Fix login bug!! @#$",
        output=sample_output,
    )
    filename = Path(output_path).name
    assert "review" in filename
    assert ".md" in filename
    assert "@" not in filename
    assert "#" not in filename
    assert "!" not in filename


def test_writer_content_format(tmp_path, sample_output):
    """测试输出内容格式"""
    writer = ResultWriter(root_dir=str(tmp_path))
    output_path = writer.write(
        scene="planning",
        task="Test task",
        output=sample_output,
    )
    content = Path(output_path).read_text()
    assert "# PLANNING 共识报告" in content
    assert "Test task" in content
    assert "## Final Plan" in content
    assert "Model A and B agreed on approach X" in content


def test_scene_directory_mapping(tmp_path, sample_output):
    """测试场景到目录的映射"""
    writer = ResultWriter(root_dir=str(tmp_path))
    scenes = ["planning", "review", "arch", "debug"]
    for scene in scenes:
        output_path = writer.write(
            scene=scene,
            task=f"Test {scene}",
            output=sample_output,
        )
        assert scene in output_path


def test_writer_includes_metadata(tmp_path, sample_output):
    """测试元数据包含在输出中"""
    writer = ResultWriter(root_dir=str(tmp_path))
    output_path = writer.write(
        scene="planning",
        task="Test metadata",
        output=sample_output,
    )
    content = Path(output_path).read_text()
    assert "model-a" in content
    assert "model-b" in content


def test_writer_creates_nested_directories(tmp_path, sample_output):
    """测试创建嵌套目录"""
    writer = ResultWriter(root_dir=str(tmp_path))
    output_path = writer.write(
        scene="planning",
        task="Nested directory test",
        output=sample_output,
    )
    # 验证父目录存在
    parent_dir = Path(output_path).parent
    assert parent_dir.exists()
    assert parent_dir.name == "plans"
