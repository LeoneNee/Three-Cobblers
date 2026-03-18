import pytest
from pathlib import Path
from consensus_engine.writer import write_consensus, build_markdown


SCENE_DIR_MAP = {
    "planning": "plans",
    "review": "reviews",
    "arch": "archs",
    "debug": "debugs",
}


class TestBuildMarkdown:
    def test_contains_all_sections(self):
        md = build_markdown(
            task="设计登录",
            scene="planning",
            models=["deepseek", "qwen"],
            final_plan="最终方案内容",
            proposals={"deepseek": "提案A", "qwen": "提案B"},
            reviews={"deepseek": "评审A", "qwen": "评审B"},
        )
        assert "设计登录" in md
        assert "planning" in md
        assert "最终方案内容" in md
        assert "deepseek" in md
        assert "提案A" in md
        assert "评审A" in md


class TestWriteConsensus:
    @pytest.mark.parametrize("scene,subdir", SCENE_DIR_MAP.items())
    def test_creates_file_in_correct_directory(self, tmp_path, scene, subdir):
        path = write_consensus(
            project_root=tmp_path,
            scene=scene,
            task="测试任务",
            models=["a", "b"],
            final_plan="内容",
            proposals={"a": "pa", "b": "pb"},
            reviews={"a": "ra", "b": "rb"},
        )
        assert path.exists()
        assert f"docs/{subdir}/" in str(path)
        assert path.suffix == ".md"
        content = path.read_text()
        assert "测试任务" in content

    def test_filename_format(self, tmp_path):
        path = write_consensus(
            project_root=tmp_path,
            scene="planning",
            task="t",
            models=["a", "b"],
            final_plan="c",
            proposals={"a": "p"},
            reviews={"a": "r"},
        )
        assert "_plan.md" in path.name
        assert len(path.stem.split("_")[0]) == 8  # YYYYMMDD
