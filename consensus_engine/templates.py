"""各阶段 Prompt 模板。"""


def build_proposal_prompt(
    task: str, content: str, scene: str
) -> tuple[str, str]:
    """构建提案阶段的 system/user prompt。"""
    system = (
        "你是一位资深技术专家。请根据任务描述和上下文，"
        "提出你的详细方案。要求结构清晰、可执行。"
    )
    user = (
        f"## 任务\n{task}\n\n"
        f"## 上下文\n{content}\n\n"
        f"## 场景\n{scene}\n\n"
        "请输出你的完整方案（Markdown 格式）。"
    )
    return system, user


def build_review_prompt(
    task: str, proposals: dict[str, str]
) -> tuple[str, str]:
    """构建交叉评审阶段的 system/user prompt。"""
    system = (
        "你是一位严谨的技术评审专家。"
        "请对以下方案进行批判性评审，指出漏洞、安全风险或性能瓶颈。"
    )
    proposals_text = "\n\n".join(
        f"### {name} 的方案\n{text}" for name, text in proposals.items()
    )
    user = (
        f"## 任务\n{task}\n\n"
        f"## 各专家提案\n{proposals_text}\n\n"
        "请逐一评审以上方案，指出问题并给出改进建议。"
    )
    return system, user


def build_synthesis_prompt(
    task: str,
    proposals: dict[str, str],
    reviews: dict[str, str],
) -> tuple[str, str]:
    """构建汇总阶段的 system/user prompt（仅 Judge 使用）。"""
    system = (
        "你是最终裁判。综合所有专家的提案和评审意见，"
        "输出一份结构化的最终共识方案（Markdown 格式）。"
    )
    proposals_text = "\n\n".join(
        f"### {name} 的方案\n{text}" for name, text in proposals.items()
    )
    reviews_text = "\n\n".join(
        f"### {name} 的评审\n{text}" for name, text in reviews.items()
    )
    user = (
        f"## 任务\n{task}\n\n"
        f"## 原始提案\n{proposals_text}\n\n"
        f"## 评审意见\n{reviews_text}\n\n"
        "请输出最终共识方案。"
    )
    return system, user
