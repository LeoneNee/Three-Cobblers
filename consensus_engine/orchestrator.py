# consensus_engine/orchestrator.py
"""辩论编排器模块

本模块实现了三阶段辩论流程：
1. 第一轮：各模型并发提案
2. 第二轮：交叉评审（A评审B，B评审C，...）
3. 第三轮：judge模型合成最终共识
"""

import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from consensus_engine.client import ModelClient, ModelResponse
from consensus_engine.config import ModelConfig
from consensus_engine.templates import TemplateRegistry
from consensus_engine.writer import ConsensusOutput


@dataclass
class ConsensusInput:
    """共识输入参数

    用于启动辩论流程的输入数据。
    """
    question: str
    """需要讨论的问题"""

    scene: str = "planning"
    """场景类型（planning, review, arch, debug）"""

    context: str = ""
    """额外的上下文信息"""


class DebateOrchestrator:
    """辩论编排器

    协调多模型进行三轮辩论，生成最终共识。
    """

    def __init__(
        self,
        models: List[ModelConfig],
        scene: str = "planning",
        judge_index: int = -1,
        client_factory=None,
    ):
        """初始化辩论编排器

        Args:
            models: 模型配置列表，最后一个作为 judge
            scene: 场景类型，用于选择提示词模板
            judge_index: judge 模型的索引，默认为最后一个
            client_factory: 客户端工厂函数，用于测试时注入 mock
        """
        if len(models) < 2:
            raise ValueError("至少需要2个模型（1个提案者 + 1个judge）")

        self.models = models
        self.scene = scene
        self.judge_index = judge_index if judge_index >= 0 else len(models) - 1
        self.template_registry = TemplateRegistry()
        self._client_factory = client_factory or ModelClient

        # 分离提案者和 judge
        self.proposer_models = [
            m for i, m in enumerate(models) if i != self.judge_index
        ]
        self.judge_model = models[self.judge_index]

    async def run_debate(self, input_data: ConsensusInput) -> ConsensusOutput:
        """运行完整的辩论流程

        Args:
            input_data: 输入参数

        Returns:
            ConsensusOutput: 包含最终共识和中间过程的输出结果
        """
        # 获取场景模板
        system_prompt = self.template_registry.get_prompt(input_data.scene)

        # 第一轮：并发提案
        proposals = await self._round1_proposal(
            question=input_data.question,
            system_prompt=system_prompt,
        )

        # 如果没有成功的提案，返回错误结果
        if not proposals:
            return ConsensusOutput(
                question=input_data.question,
                final_answer="无法生成共识：所有模型调用失败",
                total_models=len(self.proposer_models),
                successful_models=0,
            )

        # 第二轮：交叉评审
        critiques = await self._round2_critique(
            proposals=proposals,
            system_prompt=system_prompt,
        )

        # 第三轮：合成共识
        final_answer = await self._round3_consensus(
            question=input_data.question,
            context=input_data.context,
            proposals=proposals,
            critiques=critiques,
            system_prompt=system_prompt,
        )

        # 构建讨论摘要
        discussion_summary = self._build_summary(proposals, critiques)

        return ConsensusOutput(
            question=input_data.question,
            final_answer=final_answer,
            total_models=len(self.proposer_models),
            successful_models=len(proposals),
            proposals=proposals,
            critiques=critiques,
            discussion_summary=discussion_summary,
            metadata={
                "scene": input_data.scene,
                "judge_model": self.judge_model.name,
            },
        )

    async def _round1_proposal(
        self,
        question: str,
        system_prompt: str = "",
    ) -> Dict[str, str]:
        """第一轮：并发生成提案

        所有提案者模型同时生成各自的提案。

        Args:
            question: 待讨论的问题
            system_prompt: 系统提示词

        Returns:
            {model_name: proposal} 成功的提案字典
        """
        # 为每个提案者创建客户端
        tasks = []
        for model in self.proposer_models:
            client = self._client_factory(model)
            tasks.append(self._call_model(client, question, system_prompt))

        # 并发调用所有模型
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集成功的提案
        proposals = {}
        for i, result in enumerate(results):
            model_name = self.proposer_models[i].name
            if isinstance(result, str) and result:
                proposals[model_name] = result

        return proposals

    async def _round2_critique(
        self,
        proposals: Dict[str, str],
        system_prompt: str = "",
    ) -> Dict[str, str]:
        """第二轮：交叉评审

        每个模型评审下一个模型的提案（循环）。

        Args:
            proposals: 第一轮的提案字典
            system_prompt: 系统提示词

        Returns:
            {model_name: critique} 评审结果字典
        """
        if len(proposals) < 2:
            # 只有一个提案，无法交叉评审
            return {}

        model_names = list(proposals.keys())
        critiques = {}

        # 创建评审任务：A评审B，B评审C，...，最后一个评审第一个
        tasks = []
        reviewer_target_pairs = []

        for i, reviewer_name in enumerate(model_names):
            target_name = model_names[(i + 1) % len(model_names)]
            target_proposal = proposals[target_name]

            reviewer_model = next(
                m for m in self.proposer_models if m.name == reviewer_name
            )
            client = self._client_factory(reviewer_model)

            # 构建评审提示词
            critique_prompt = self._build_critique_prompt(
                target_name=target_name,
                target_proposal=target_proposal,
            )

            tasks.append(self._call_model(client, critique_prompt, system_prompt))
            reviewer_target_pairs.append(reviewer_name)

        # 并发执行评审
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集成功的评审
        for i, result in enumerate(results):
            reviewer_name = reviewer_target_pairs[i]
            if isinstance(result, str) and result:
                critiques[reviewer_name] = result

        return critiques

    async def _round3_consensus(
        self,
        question: str,
        proposals: Dict[str, str],
        critiques: Dict[str, str],
        context: str = "",
        system_prompt: str = "",
    ) -> str:
        """第三轮：合成共识

        Judge 模型综合所有提案和评审，生成最终共识。

        Args:
            question: 原始问题
            proposals: 第一轮提案
            critiques: 第二轮评审
            context: 额外上下文
            system_prompt: 系统提示词

        Returns:
            最终共识答案
        """
        # 构建共识提示词
        consensus_prompt = self._build_consensus_prompt(
            question=question,
            proposals=proposals,
            critiques=critiques,
            context=context,
        )

        # 调用 judge 模型
        judge_client = self._client_factory(self.judge_model)
        result = await self._call_model(judge_client, consensus_prompt, system_prompt)

        return result if result else "无法生成共识：judge 模型调用失败"

    async def _call_model(
        self,
        client: ModelClient,
        prompt: str,
        system_prompt: str = "",
    ) -> Optional[str]:
        """调用单个模型

        Args:
            client: 模型客户端
            prompt: 用户提示词
            system_prompt: 系统提示词

        Returns:
            模型响应内容，失败时返回 None
        """
        try:
            response: ModelResponse = await client.call(prompt, system_prompt)

            if response.error:
                return None

            return response.content

        except Exception:
            return None

        finally:
            await client.close()

    def _build_critique_prompt(
        self,
        target_name: str,
        target_proposal: str,
    ) -> str:
        """构建评审提示词

        Args:
            target_name: 被评审的模型名称
            target_proposal: 被评审的提案内容

        Returns:
            评审提示词
        """
        return f"""请评审以下提案（来自 {target_name}）：

{target_proposal}

请从以下角度进行评审：
1. 优点：该提案有哪些可取之处？
2. 缺点：该提案存在哪些问题或不足？
3. 改进建议：如何改进该提案？
4. 可行性：该提案是否可行？有哪些风险？

请给出具体、建设性的评审意见。"""

    def _build_consensus_prompt(
        self,
        question: str,
        proposals: Dict[str, str],
        critiques: Dict[str, str],
        context: str = "",
    ) -> str:
        """构建共识合成提示词

        Args:
            question: 原始问题
            proposals: 第一轮提案
            critiques: 第二轮评审
            context: 额外上下文

        Returns:
            共识合成提示词
        """
        prompt_parts = [
            f"问题：{question}",
        ]

        if context:
            prompt_parts.append(f"\n上下文：{context}")

        prompt_parts.append("\n各模型提案：")
        for model_name, proposal in proposals.items():
            prompt_parts.append(f"\n### {model_name} 的提案 ###\n{proposal}")

        if critiques:
            prompt_parts.append("\n交叉评审：")
            for reviewer_name, critique in critiques.items():
                prompt_parts.append(f"\n### {reviewer_name} 的评审 ###\n{critique}")

        prompt_parts.append("""
\n请综合以上所有提案和评审，给出一个平衡、全面的最终共识答案。

你的回答应该：
1. 综合考虑各模型的观点
2. 平衡不同方案的优缺点
3. 给出明确的结论和建议
4. 如有必要，指出需要进一步讨论的问题""")

        return "\n".join(prompt_parts)

    def _build_summary(
        self,
        proposals: Dict[str, str],
        critiques: Dict[str, str],
    ) -> str:
        """构建讨论摘要

        Args:
            proposals: 第一轮提案
            critiques: 第二轮评审

        Returns:
            讨论摘要文本
        """
        summary_parts = ["## 讨论摘要\n\n### 提案阶段\n"]

        for model_name, proposal in proposals.items():
            # 截取前100个字符作为摘要
            summary = proposal[:100] + "..." if len(proposal) > 100 else proposal
            summary_parts.append(f"**{model_name}**: {summary}\n")

        if critiques:
            summary_parts.append("\n### 评审阶段\n")
            for reviewer_name, critique in critiques.items():
                summary = critique[:100] + "..." if len(critique) > 100 else critique
                summary_parts.append(f"**{reviewer_name}**: {summary}\n")

        return "\n".join(summary_parts)
