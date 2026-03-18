# consensus_engine/writer.py
"""Writer 模块 - 负责输出共识结果

本模块定义了共识输出的数据结构和结果写入器。
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ConsensusOutput:
    """共识输出结果

    包含多轮辩论后的最终共识结果和中间过程。
    """
    final_consensus: str
    """最终共识答案"""

    debate_summary: str
    """讨论摘要（包含提案和评审的总结）"""

    rounds_executed: int
    """执行的辩论轮数"""

    models_participated: List[str]
    """参与辩论的模型名称列表"""

    total_duration_ms: int
    """总执行时间（毫秒）"""

    proposals: Dict[str, str] = field(default_factory=dict)
    """第一轮：各模型的提案 {model_name: proposal}"""

    critiques: Dict[str, str] = field(default_factory=dict)
    """第二轮：交叉评审 {model_name: critique}"""

    confidence_score: Optional[float] = None
    """共识置信度（0-1），可选"""

    metadata: Dict[str, object] = field(default_factory=dict)
    """额外的元数据信息"""


# 场景到目录的映射
SCENE_DIR_MAP = {
    "planning": "plans",
    "review": "reviews",
    "arch": "architecture",
    "debug": "debugging",
}


class ResultWriter:
    """结果写入器

    将共识结果写入 Markdown 文件，按场景类型组织目录结构。
    """

    def __init__(self, root_dir: str = "docs"):
        """初始化结果写入器

        Args:
            root_dir: 输出根目录，默认为 "docs"
        """
        self.root_dir = Path(root_dir)

    def sanitize_filename(self, task: str) -> str:
        """清理任务名称，使其适合作为文件名

        移除特殊字符，只保留字母、数字、下划线和短横线。

        Args:
            task: 原始任务名称

        Returns:
            清理后的文件名
        """
        # 移除或替换特殊字符
        sanitized = re.sub(r'[^\w\s-]', '', task)
        # 将空白字符替换为短横线
        sanitized = re.sub(r'[\s]+', '-', sanitized)
        # 移除连续的短横线
        sanitized = re.sub(r'-+', '-', sanitized)
        # 去除首尾短横线
        sanitized = sanitized.strip('-')
        # 限制长度
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        return sanitized

    def write(
        self,
        scene: str,
        task: str,
        output: ConsensusOutput,
    ) -> str:
        """写入共识结果到 Markdown 文件

        Args:
            scene: 场景类型（planning, review, arch, debug）
            task: 任务描述
            output: 共识输出结果

        Returns:
            输出文件的绝对路径
        """
        # 获取场景对应的目录
        scene_dir = SCENE_DIR_MAP.get(scene, scene)

        # 创建输出目录
        output_dir = self.root_dir / scene_dir
        output_dir.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        sanitized_task = self.sanitize_filename(task)
        filename = f"{timestamp}-{scene}-{sanitized_task}.md"

        # 写入文件
        output_path = output_dir / filename
        markdown_content = self._build_markdown(scene, task, output)

        output_path.write_text(markdown_content, encoding="utf-8")

        return str(output_path.absolute())

    def _build_markdown(
        self,
        scene: str,
        task: str,
        output: ConsensusOutput,
    ) -> str:
        """构建 Markdown 内容

        Args:
            scene: 场景类型
            task: 任务描述
            output: 共识输出结果

        Returns:
            Markdown 格式的文本
        """
        scene_upper = scene.upper()

        # 构建各部分内容
        parts = [
            f"# {scene_upper} 共识报告",
            "",
            f"**任务**: {task}",
            f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "---",
            "",
            "## 最终共识",
            "",
            output.final_consensus,
            "",
            "---",
            "",
            "## 讨论摘要",
            "",
            output.debate_summary,
            "",
            "---",
            "",
            "## 统计信息",
            "",
            f"- **执行轮数**: {output.rounds_executed}",
            f"- **参与模型**: {', '.join(output.models_participated)}",
            f"- **总耗时**: {output.total_duration_ms} ms",
        ]

        # 添加元数据信息
        if output.metadata:
            parts.append("")
            parts.append("## 元数据")
            parts.append("")
            for key, value in output.metadata.items():
                if isinstance(value, list):
                    value_str = ", ".join(str(v) for v in value)
                else:
                    value_str = str(value)
                parts.append(f"- **{key}**: {value_str}")

        # 添加提案详情（如果有）
        if output.proposals:
            parts.append("")
            parts.append("---")
            parts.append("")
            parts.append("## 各模型提案")
            parts.append("")
            for model_name, proposal in output.proposals.items():
                parts.append(f"### {model_name}")
                parts.append("")
                parts.append(proposal)
                parts.append("")

        # 添加评审详情（如果有）
        if output.critiques:
            parts.append("---")
            parts.append("")
            parts.append("## 交叉评审")
            parts.append("")
            for reviewer_name, critique in output.critiques.items():
                parts.append(f"### {reviewer_name} 的评审")
                parts.append("")
                parts.append(critique)
                parts.append("")

        return "\n".join(parts)
