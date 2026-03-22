---
name: consensus-debate
version: 1.0.0
description: |
  多模型共识博弈 Skill - 用于复杂技术决策的三阶段辩论流程。
  
  适用场景：
  - 需要多个 AI 视角的技术问题
  - 架构设计、代码评审、功能规划、问题调试
  - 需要共识而非单一意见的决策
  
  前置条件：
  - 环境变量 LOCAL_MODEL_CONFIGS（JSON 格式的模型配置数组）
  - Python 3.10+ 环境
  - 已安装 httpx 库
---

# 多模型共识博弈 Skill

## 概述

实现三阶段辩论流程，通过多个 AI 模型达成共识：

1. **Phase 1 (提案)**: 所有模型独立提出方案（并发）
2. **Phase 2 (交叉评审)**: 模型互相评审对方方案（并发）
3. **Phase 3 (汇总)**: Judge 模型综合各方意见，输出最终共识

## 使用方法

```
执行共识博弈：
- scene: planning | review | arch | debug
- task: 核心任务描述
- content: 相关代码或上下文
- review_mode: summarized | full（可选，默认 summarized）
```

## 环境变量配置

```bash
export LOCAL_MODEL_CONFIGS='[
  {
    "name": "model-1",
    "endpoint": "https://api.example.com/v1/chat/completions",
    "api_key": "your-api-key",
    "model": "model-id",
    "role": "participant",
    "protocol": "openai"
  },
  {
    "name": "model-2",
    "endpoint": "https://api.anthropic.com/v1",
    "api_key": "your-api-key",
    "model": "claude-3-opus",
    "role": "judge",
    "protocol": "anthropic"
  }
]'
```

**必填字段**: `name`, `endpoint`, `api_key`, `model`
**可选字段**: `role`（participant/judge，默认 participant）, `protocol`（openai/anthropic，默认 openai）

**要求**: 至少 2 个模型，恰好 1 个 role="judge"

---

## 完整可执行代码

将以下代码保存为临时文件并执行：

```python
#!/usr/bin/env python3
"""多模型共识博弈 - 完整独立版本"""

import asyncio
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Literal

import httpx


# ============== 数据类定义 ==============

@dataclass(frozen=True)
class ModelConfig:
    """模型配置"""
    name: str
    endpoint: str
    api_key: str
    model: str
    role: str = "participant"
    protocol: str = "openai"


@dataclass
class DebateResult:
    """博弈结果"""
    final_plan: str
    models_participated: list[str]
    models_failed: list[str]
    proposals: dict[str, str] = field(default_factory=dict)
    reviews: dict[str, str] = field(default_factory=dict)


# ============== 配置解析 ==============

def load_model_configs() -> list[ModelConfig]:
    """从 LOCAL_MODEL_CONFIGS 环境变量解析模型配置"""
    raw = os.environ.get("LOCAL_MODEL_CONFIGS")
    if not raw:
        raise ValueError(
            "缺少 LOCAL_MODEL_CONFIGS 环境变量。\n"
            '格式: [{"name":"...", "endpoint":"...", "api_key":"...", "model":"...", "role":"judge"}]'
        )

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LOCAL_MODEL_CONFIGS JSON 解析失败: {e}")

    required_fields = {"name", "endpoint", "api_key", "model"}
    configs = []
    for item in items:
        missing = required_fields - set(item.keys())
        if missing:
            raise ValueError(f"模型配置缺少必填字段: {missing}")
        configs.append(
            ModelConfig(
                name=item["name"],
                endpoint=item["endpoint"],
                api_key=item["api_key"],
                model=item["model"],
                role=item.get("role", "participant"),
                protocol=item.get("protocol", "openai"),
            )
        )

    if len(configs) < 2:
        raise ValueError("至少需要 2 个模型配置")

    judges = [c for c in configs if c.role == "judge"]
    if len(judges) != 1:
        raise ValueError(f"恰好需要 1 个 judge 模型，当前有 {len(judges)} 个")

    return configs


# ============== 模型客户端 ==============

class ModelClient:
    """异步模型客户端，支持 OpenAI 和 Anthropic 协议"""

    def __init__(self, config: ModelConfig, timeout: float = 300.0):
        self.config = config
        self.timeout = timeout

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发送 chat completion 请求"""
        if self.config.protocol == "anthropic":
            return await self._chat_anthropic(system_prompt, user_prompt)
        return await self._chat_openai(system_prompt, user_prompt)

    async def _chat_openai(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as http:
            print(f"[consensus] 请求 {self.config.name} (openai)...", file=sys.stderr)
            resp = await http.post(self.config.endpoint, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"[consensus] {self.config.name} 响应完成", file=sys.stderr)
            return content

    async def _chat_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.config.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [{"role": "user", "content": user_prompt}],
        }

        async with httpx.AsyncClient(timeout=self.timeout) as http:
            print(f"[consensus] 请求 {self.config.name} (anthropic)...", file=sys.stderr)
            url = self.config.endpoint.rstrip("/")
            if not url.endswith("/messages"):
                url += "/messages"
            resp = await http.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
            content = data["content"][0]["text"]
            print(f"[consensus] {self.config.name} 响应完成", file=sys.stderr)
            return content


# ============== Prompt 模板 ==============

def build_proposal_prompt(task: str, content: str, scene: str) -> tuple[str, str]:
    """构建提案阶段 prompt"""
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


def build_review_prompt(task: str, proposals: dict[str, str]) -> tuple[str, str]:
    """构建评审阶段 prompt"""
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
    task: str, proposals: dict[str, str], reviews: dict[str, str]
) -> tuple[str, str]:
    """构建汇总阶段 prompt"""
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


# ============== 核心博弈逻辑 ==============

async def _safe_chat(
    name: str, client: ModelClient, system: str, user: str
) -> tuple[str, str | None]:
    """安全调用模型，失败返回 (name, None)"""
    try:
        result = await client.chat(system, user)
        return name, result
    except Exception as e:
        print(f"[consensus] {name} 失败: {e}", file=sys.stderr)
        return name, None


async def run_consensus_debate(
    task: str,
    content: str,
    scene: Literal["planning", "review", "arch", "debug"],
    review_mode: Literal["summarized", "full"] = "summarized",
) -> DebateResult:
    """
    执行三阶段共识博弈。

    Args:
        task: 核心任务描述
        content: 相关代码或上下文
        scene: 场景类型 (planning/review/arch/debug)
        review_mode: 评审模式 (summarized/full)

    Returns:
        DebateResult: 包含最终方案、参与模型、提案和评审
    """
    configs = load_model_configs()

    judge_config = next(c for c in configs if c.role == "judge")
    participant_configs = [c for c in configs if c.role != "judge"]

    all_debaters = [judge_config] + participant_configs
    clients = {c.name: ModelClient(c) for c in all_debaters}

    failed: list[str] = []

    # === Phase 1: Proposal ===
    print(f"[Phase 1/3] 向 {len(all_debaters)} 个模型请求提案...", file=sys.stderr)
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
    print(f"[Phase 2/3] 交叉评审中（{review_mode} 模式）...", file=sys.stderr)
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
    print(f"[Phase 3/3] Judge ({judge_config.name}) 汇总共识...", file=sys.stderr)
    system_s, user_s = build_synthesis_prompt(task, proposals, reviews)
    judge_client = clients[judge_config.name]
    _, synthesis = await _safe_chat(judge_config.name, judge_client, system_s, user_s)

    if synthesis is None:
        raise RuntimeError("Judge 模型汇总失败")

    participated = [n for n in [c.name for c in all_debaters] if n not in failed]

    return DebateResult(
        final_plan=synthesis,
        models_participated=participated,
        models_failed=failed,
        proposals=proposals,
        reviews=reviews,
    )


# ============== 入口函数 ==============

async def main():
    """示例入口"""
    result = await run_consensus_debate(
        task="设计一个用户认证系统",
        content="需要支持邮箱登录、OAuth、JWT token",
        scene="arch",
        review_mode="summarized",
    )
    print("\n" + "=" * 50)
    print("最终共识方案:")
    print("=" * 50)
    print(result.final_plan)
    print("\n参与模型:", result.models_participated)
    if result.models_failed:
        print("失败模型:", result.models_failed)


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 执行指令

1. 确保已安装 httpx: `pip install httpx`
2. 设置环境变量 `LOCAL_MODEL_CONFIGS`
3. 复制上述代码到临时文件 `consensus_debate.py`
4. 根据需要修改 `main()` 函数中的参数
5. 执行: `python consensus_debate.py`

或者直接在代码中调用:

```python
result = await run_consensus_debate(
    task="你的任务描述",
    content="相关代码或上下文",
    scene="planning",  # planning/review/arch/debug
    review_mode="summarized",  # summarized/full
)

# 输出结果
print(result.final_plan)
```

## 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| task | 是 | 核心任务描述 |
| content | 是 | 相关代码、文档或上下文 |
| scene | 是 | 场景类型: planning, review, arch, debug |
| review_mode | 否 | 评审模式: summarized(默认), full |

## 场景类型

- **planning**: 功能或项目规划
- **review**: 代码评审或质量评估
- **arch**: 架构或设计决策
- **debug**: 问题分析和调试

## 评审模式

- **summarized**: 评审者看到汇总后的提案（更快，更省 token）
- **full**: 评审者看到其他人的完整提案（更全面，消耗更多 token）

## 输出结构

```python
DebateResult(
    final_plan="综合后的最终共识方案...",
    models_participated=["model-1", "model-2"],
    models_failed=[],
    proposals={"model-1": "提案1...", "model-2": "提案2..."},
    reviews={"model-1": "评审1...", "model-2": "评审2..."}
)
```
