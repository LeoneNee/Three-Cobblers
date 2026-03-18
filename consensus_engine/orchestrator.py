"""三阶段博弈编排器。"""

import asyncio
import sys
from dataclasses import dataclass, field

from consensus_engine.client import ModelClient
from consensus_engine.config import ModelConfig
from consensus_engine.templates import (
    build_proposal_prompt,
    build_review_prompt,
    build_synthesis_prompt,
)


@dataclass
class DebateResult:
    final_plan: str
    models_participated: list[str]
    models_failed: list[str]
    proposals: dict[str, str] = field(default_factory=dict)
    reviews: dict[str, str] = field(default_factory=dict)


async def _safe_chat(
    name: str, client: ModelClient, system: str, user: str
) -> tuple[str, str | None]:
    """安全调用模型，失败返回 (name, None)。"""
    try:
        result = await client.chat(system, user)
        return name, result
    except Exception as e:
        print(
            f"[consensus-engine] {name} 失败：{e}",
            file=sys.stderr,
        )
        return name, None


async def run_debate(
    configs: list[ModelConfig],
    task: str,
    content: str,
    scene: str,
    review_mode: str = "summarized",
) -> DebateResult:
    """执行三阶段博弈流程。"""
    judge_config = next(c for c in configs if c.role == "judge")
    participant_configs = [c for c in configs if c.role != "judge"]

    all_debaters = [judge_config] + participant_configs
    clients = {c.name: ModelClient(c) for c in all_debaters}

    failed: list[str] = []

    # === Phase 1: Proposal ===
    print(
        f"[Phase 1/3] 向 {len(all_debaters)} 个模型请求提案...",
        file=sys.stderr,
    )
    system_p, user_p = build_proposal_prompt(task, content, scene)
    tasks_p = [
        _safe_chat(c.name, clients[c.name], system_p, user_p) for c in all_debaters
    ]
    results_p = await asyncio.gather(*tasks_p)

    proposals: dict[str, str] = {}
    for name, result in results_p:
        if result is None:
            failed.append(name)
        else:
            proposals[name] = result

    if len(proposals) < 2:
        raise RuntimeError(f"提案阶段成功模型不足 2 个（成功：{list(proposals.keys())}）")

    # === Phase 2: Cross-Review ===
    print(
        f"[Phase 2/3] 交叉评审中（{review_mode} 模式）...",
        file=sys.stderr,
    )
    reviews: dict[str, str] = {}

    if review_mode == "full":
        review_tasks = []
        for reviewer_name, client in clients.items():
            if reviewer_name in failed:
                continue
            other_proposals = {
                k: v for k, v in proposals.items() if k != reviewer_name
            }
            if not other_proposals:
                continue
            system_r, user_r = build_review_prompt(task, other_proposals)
            review_tasks.append(_safe_chat(reviewer_name, client, system_r, user_r))

        results_r = await asyncio.gather(*review_tasks)
        for name, result in results_r:
            if result is None:
                if name not in failed:
                    failed.append(name)
            else:
                reviews[name] = result
    else:
        system_r, user_r = build_review_prompt(task, proposals)
        review_tasks = [
            _safe_chat(name, clients[name], system_r, user_r)
            for name in proposals
            if name not in failed
        ]
        results_r = await asyncio.gather(*review_tasks)
        for name, result in results_r:
            if result is None:
                if name not in failed:
                    failed.append(name)
            else:
                reviews[name] = result

    # === Phase 3: Synthesis ===
    print(
        f"[Phase 3/3] Judge ({judge_config.name}) 汇总共识...",
        file=sys.stderr,
    )
    system_s, user_s = build_synthesis_prompt(task, proposals, reviews)
    judge_client = clients[judge_config.name]
    _, synthesis = await _safe_chat(judge_config.name, judge_client, system_s, user_s)

    if synthesis is None:
        raise RuntimeError("Judge 模型汇总失败（可能在之前阶段已失败）")

    participated = [n for n in [c.name for c in all_debaters] if n not in failed]

    return DebateResult(
        final_plan=synthesis,
        models_participated=participated,
        models_failed=failed,
        proposals=proposals,
        reviews=reviews,
    )
