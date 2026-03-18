# consensus_engine/writer.py
"""Writer 模块 - 负责输出共识结果

本模块定义了共识输出的数据结构。
完整的 Writer 类将在 Task 6 中实现。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class ConsensusOutput:
    """共识输出结果

    包含多轮辩论后的最终共识结果和中间过程。
    """
    question: str
    """原始问题"""

    final_answer: str
    """最终共识答案"""

    total_models: int
    """参与辩论的模型数量"""

    successful_models: int
    """成功参与辩论的模型数量（排除错误）"""

    proposals: Dict[str, str] = field(default_factory=dict)
    """第一轮：各模型的提案 {model_name: proposal}"""

    critiques: Dict[str, str] = field(default_factory=dict)
    """第二轮：交叉评审 {model_name: critique}"""

    discussion_summary: str = ""
    """讨论摘要（包含提案和评审的总结）"""

    confidence_score: Optional[float] = None
    """共识置信度（0-1），可选"""

    metadata: Dict[str, object] = field(default_factory=dict)
    """额外的元数据信息"""
