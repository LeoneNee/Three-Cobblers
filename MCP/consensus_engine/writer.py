"""Markdown 生成与文件持久化。"""

from datetime import datetime
from pathlib import Path

SCENE_DIR_MAP: dict[str, tuple[str, str]] = {
    "planning": ("plans", "plan"),
    "review": ("reviews", "review"),
    "arch": ("archs", "arch"),
    "debug": ("debugs", "debug"),
}


def build_markdown(
    task: str,
    scene: str,
    models: list[str],
    final_plan: str,
    proposals: dict[str, str],
    reviews: dict[str, str],
) -> str:
    """生成共识结论的 Markdown 文档。"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    model_list = ", ".join(models)

    proposals_section = "\n".join(
        f"- **{name}**: {text[:200]}..." if len(text) > 200 else f"- **{name}**: {text}"
        for name, text in proposals.items()
    )
    reviews_section = "\n".join(
        f"- **{name}**: {text[:200]}..." if len(text) > 200 else f"- **{name}**: {text}"
        for name, text in reviews.items()
    )

    return (
        f"# 共识结论：{task}\n\n"
        f"> 场景：{scene} | 时间：{now} | 参与模型：{model_list}\n\n"
        f"## 最终方案\n\n{final_plan}\n\n"
        f"## 博弈摘要\n\n"
        f"### 提案阶段\n{proposals_section}\n\n"
        f"### 评审阶段\n{reviews_section}\n"
    )


def write_consensus(
    project_root: Path,
    scene: str,
    task: str,
    models: list[str],
    final_plan: str,
    proposals: dict[str, str],
    reviews: dict[str, str],
) -> Path:
    """生成 Markdown 并写入对应目录，返回文件路径。"""
    subdir, suffix = SCENE_DIR_MAP[scene]
    now = datetime.now()
    filename = f"{now.strftime('%Y%m%d_%H%M')}_{suffix}.md"

    target_dir = project_root / "docs" / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    content = build_markdown(
        task=task,
        scene=scene,
        models=models,
        final_plan=final_plan,
        proposals=proposals,
        reviews=reviews,
    )

    filepath = target_dir / filename
    filepath.write_text(content, encoding="utf-8")
    return filepath
