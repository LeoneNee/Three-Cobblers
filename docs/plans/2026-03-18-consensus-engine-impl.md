# Consensus-Engine MCP 实现计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 构建一个 FastMCP 服务器，并发调用多个 OpenAI 兼容模型进行三阶段博弈，输出共识方案并自动存档到本地 `docs/` 目录。

**Architecture:** Python 包 `consensus_engine`，4 个核心模块（client/templates/orchestrator/writer）+ 1 个 FastMCP 入口（server）。所有模型配置通过环境变量注入，文件写入路径通过 `PROJECT_ROOT` 环境变量控制。

**Tech Stack:** Python 3.10+, FastMCP, httpx, asyncio, pytest, pytest-asyncio

---

### Task 1: 项目脚手架

**Files:**
- Create: `pyproject.toml`
- Create: `consensus_engine/__init__.py`
- Create: `tests/__init__.py`
- Create: `.gitignore`

**Step 1: 创建 pyproject.toml**

```toml
[project]
name = "consensus-engine"
version = "0.1.0"
description = "MCP server for multi-model consensus debate"
requires-python = ">=3.10"
dependencies = [
    "fastmcp>=2.0.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24.0",
    "respx>=0.22.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 2: 创建包初始化文件**

`consensus_engine/__init__.py`:
```python
"""Consensus Engine - Multi-model debate MCP server."""
```

`tests/__init__.py`:
```python
```

**Step 3: 更新 .gitignore**

```
__pycache__/
*.pyc
.venv/
*.egg-info/
dist/
.pytest_cache/
```

**Step 4: 安装依赖**

Run: `cd /Users/leone/AI/fake-verdent && pip install -e ".[dev]"`
Expected: 成功安装所有依赖

**Step 5: 验证 pytest 可运行**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest --co`
Expected: `no tests ran` 或 `collected 0 items`

**Step 6: Commit**

```bash
git add pyproject.toml consensus_engine/__init__.py tests/__init__.py .gitignore
git commit -m "chore: init project scaffold with dependencies"
```

---

### Task 2: 配置解析模块（config.py）

**Files:**
- Create: `consensus_engine/config.py`
- Create: `tests/test_config.py`

**Step 1: 写失败测试**

`tests/test_config.py`:
```python
import json
import os
import pytest
from consensus_engine.config import load_model_configs, load_project_root, ModelConfig


VALID_CONFIGS = [
    {
        "name": "deepseek",
        "endpoint": "https://api.deepseek.com/v1/chat/completions",
        "api_key": "sk-test1",
        "model": "deepseek-chat",
        "role": "judge",
    },
    {
        "name": "qwen",
        "endpoint": "https://api.qwen.com/v1/chat/completions",
        "api_key": "sk-test2",
        "model": "qwen-plus",
    },
]


class TestLoadModelConfigs:
    def test_valid_configs(self, monkeypatch):
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(VALID_CONFIGS))
        configs = load_model_configs()
        assert len(configs) == 2
        assert configs[0].name == "deepseek"
        assert configs[0].role == "judge"
        assert configs[1].role == "participant"

    def test_missing_env_var(self, monkeypatch):
        monkeypatch.delenv("LOCAL_MODEL_CONFIGS", raising=False)
        with pytest.raises(SystemExit):
            load_model_configs()

    def test_less_than_two_models(self, monkeypatch):
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps([VALID_CONFIGS[0]]))
        with pytest.raises(ValueError, match="至少需要 2 个模型"):
            load_model_configs()

    def test_no_judge(self, monkeypatch):
        configs_no_judge = [
            {**c, "role": "participant"} if "role" in c else c
            for c in VALID_CONFIGS
        ]
        # Remove role field entirely
        for c in configs_no_judge:
            c.pop("role", None)
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(configs_no_judge))
        with pytest.raises(ValueError, match="恰好需要 1 个 judge"):
            load_model_configs()

    def test_multiple_judges(self, monkeypatch):
        configs_two_judges = [
            {**c, "role": "judge"} for c in VALID_CONFIGS
        ]
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(configs_two_judges))
        with pytest.raises(ValueError, match="恰好需要 1 个 judge"):
            load_model_configs()

    def test_missing_required_field(self, monkeypatch):
        bad = [{"name": "x"}, VALID_CONFIGS[1]]
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", json.dumps(bad))
        with pytest.raises(ValueError):
            load_model_configs()


class TestLoadProjectRoot:
    def test_from_env(self, monkeypatch, tmp_path):
        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        assert load_project_root() == tmp_path

    def test_fallback_to_cwd(self, monkeypatch):
        monkeypatch.delenv("PROJECT_ROOT", raising=False)
        result = load_project_root()
        assert result.exists()
```

**Step 2: 运行测试确认失败**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_config.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'consensus_engine.config'`

**Step 3: 实现 config.py**

`consensus_engine/config.py`:
```python
"""配置解析：从环境变量加载模型配置和项目根目录。"""

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ModelConfig:
    name: str
    endpoint: str
    api_key: str
    model: str
    role: str = "participant"


def load_model_configs() -> list[ModelConfig]:
    """从 LOCAL_MODEL_CONFIGS 环境变量解析模型配置列表。"""
    raw = os.environ.get("LOCAL_MODEL_CONFIGS")
    if not raw:
        print(
            "[consensus-engine] 错误：缺少 LOCAL_MODEL_CONFIGS 环境变量。\n"
            "请通过 claude mcp add 配置，格式为 JSON 数组：\n"
            '[{"name":"...", "endpoint":"...", "api_key":"...", "model":"...", "role":"judge"}]',
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"LOCAL_MODEL_CONFIGS JSON 解析失败：{e}")

    required_fields = {"name", "endpoint", "api_key", "model"}
    configs = []
    for item in items:
        missing = required_fields - set(item.keys())
        if missing:
            raise ValueError(f"模型配置缺少必填字段：{missing}（模型：{item.get('name', '?')}）")
        configs.append(
            ModelConfig(
                name=item["name"],
                endpoint=item["endpoint"],
                api_key=item["api_key"],
                model=item["model"],
                role=item.get("role", "participant"),
            )
        )

    if len(configs) < 2:
        raise ValueError("至少需要 2 个模型配置")

    judges = [c for c in configs if c.role == "judge"]
    if len(judges) != 1:
        raise ValueError(f"恰好需要 1 个 judge 模型，当前有 {len(judges)} 个")

    return configs


def load_project_root() -> Path:
    """从 PROJECT_ROOT 环境变量获取项目根目录，缺失则 fallback 到 cwd。"""
    root = os.environ.get("PROJECT_ROOT")
    if root:
        return Path(root)
    print(
        "[consensus-engine] 警告：未设置 PROJECT_ROOT，使用当前工作目录。",
        file=sys.stderr,
    )
    return Path.cwd()
```

**Step 4: 运行测试确认通过**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_config.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add consensus_engine/config.py tests/test_config.py
git commit -m "feat: add config parser with validation"
```

---

### Task 3: 异步模型客户端（client.py）

**Files:**
- Create: `consensus_engine/client.py`
- Create: `tests/test_client.py`

**Step 1: 写失败测试**

`tests/test_client.py`:
```python
import httpx
import pytest
import respx
from consensus_engine.client import ModelClient
from consensus_engine.config import ModelConfig


@pytest.fixture
def model_config():
    return ModelConfig(
        name="test-model",
        endpoint="https://api.test.com/v1/chat/completions",
        api_key="sk-test",
        model="test-v1",
    )


@pytest.fixture
def client(model_config):
    return ModelClient(model_config, timeout=5.0)


class TestModelClient:
    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_success(self, client, model_config):
        respx.post(model_config.endpoint).mock(
            return_value=httpx.Response(
                200,
                json={
                    "choices": [
                        {"message": {"content": "test response"}}
                    ]
                },
            )
        )
        result = await client.chat("You are a helpful assistant.", "Hello")
        assert result == "test response"

    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_api_error(self, client, model_config):
        respx.post(model_config.endpoint).mock(
            return_value=httpx.Response(500, text="Internal Server Error")
        )
        with pytest.raises(httpx.HTTPStatusError):
            await client.chat("system", "user")

    @respx.mock
    @pytest.mark.asyncio
    async def test_chat_timeout(self, client, model_config):
        respx.post(model_config.endpoint).mock(side_effect=httpx.ReadTimeout("timeout"))
        with pytest.raises(httpx.ReadTimeout):
            await client.chat("system", "user")
```

**Step 2: 运行测试确认失败**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_client.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 client.py**

`consensus_engine/client.py`:
```python
"""异步模型客户端：统一 OpenAI Chat Completions 兼容接口。"""

import sys
import httpx
from consensus_engine.config import ModelConfig


class ModelClient:
    """单个模型的异步 HTTP 客户端。"""

    def __init__(self, config: ModelConfig, timeout: float = 60.0):
        self.config = config
        self.timeout = timeout

    async def chat(self, system_prompt: str, user_prompt: str) -> str:
        """发送 chat completion 请求，返回模型回复文本。"""
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
            print(
                f"[consensus-engine] 请求 {self.config.name}...",
                file=sys.stderr,
            )
            resp = await http.post(
                self.config.endpoint, json=payload, headers=headers
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(
                f"[consensus-engine] {self.config.name} 响应完成",
                file=sys.stderr,
            )
            return content
```

**Step 4: 运行测试确认通过**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_client.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add consensus_engine/client.py tests/test_client.py
git commit -m "feat: add async model client with OpenAI-compatible API"
```

---

### Task 4: Prompt 模板（templates.py）

**Files:**
- Create: `consensus_engine/templates.py`
- Create: `tests/test_templates.py`

**Step 1: 写失败测试**

`tests/test_templates.py`:
```python
import pytest
from consensus_engine.templates import build_proposal_prompt, build_review_prompt, build_synthesis_prompt


class TestBuildProposalPrompt:
    def test_contains_task_and_content(self):
        system, user = build_proposal_prompt(
            task="设计登录模块",
            content="现有 Flask 应用",
            scene="planning",
        )
        assert "设计登录模块" in user
        assert "现有 Flask 应用" in user
        assert "planning" in user

    def test_system_prompt_is_expert(self):
        system, _ = build_proposal_prompt("t", "c", "review")
        assert "专家" in system or "expert" in system.lower()


class TestBuildReviewPrompt:
    def test_contains_proposals(self):
        proposals = {"modelA": "方案A内容", "modelB": "方案B内容"}
        system, user = build_review_prompt(
            task="设计登录模块",
            proposals=proposals,
        )
        assert "方案A内容" in user
        assert "方案B内容" in user
        assert "modelA" in user

    def test_system_prompt_is_reviewer(self):
        system, _ = build_review_prompt("t", {"a": "b"})
        assert "评审" in system or "review" in system.lower()


class TestBuildSynthesisPrompt:
    def test_contains_proposals_and_reviews(self):
        proposals = {"modelA": "方案A"}
        reviews = {"modelB": "评审意见B"}
        system, user = build_synthesis_prompt(
            task="设计登录模块",
            proposals=proposals,
            reviews=reviews,
        )
        assert "方案A" in user
        assert "评审意见B" in user

    def test_system_prompt_is_judge(self):
        system, _ = build_synthesis_prompt("t", {"a": "b"}, {"c": "d"})
        assert "裁判" in system or "judge" in system.lower()
```

**Step 2: 运行测试确认失败**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_templates.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 templates.py**

`consensus_engine/templates.py`:
```python
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
```

**Step 4: 运行测试确认通过**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_templates.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add consensus_engine/templates.py tests/test_templates.py
git commit -m "feat: add prompt templates for three debate phases"
```

---

### Task 5: Markdown 写入器（writer.py）

**Files:**
- Create: `consensus_engine/writer.py`
- Create: `tests/test_writer.py`

**Step 1: 写失败测试**

`tests/test_writer.py`:
```python
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
        # 文件名格式：YYYYMMDD_HHMM_plan.md
        assert "_plan.md" in path.name
        assert len(path.stem.split("_")[0]) == 8  # YYYYMMDD
```

**Step 2: 运行测试确认失败**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_writer.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 writer.py**

`consensus_engine/writer.py`:
```python
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
```

**Step 4: 运行测试确认通过**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_writer.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add consensus_engine/writer.py tests/test_writer.py
git commit -m "feat: add markdown writer with auto-archiving"
```

---

### Task 6: 三阶段博弈编排器（orchestrator.py）

**Files:**
- Create: `consensus_engine/orchestrator.py`
- Create: `tests/test_orchestrator.py`

**Step 1: 写失败测试**

`tests/test_orchestrator.py`:
```python
import pytest
from unittest.mock import AsyncMock, patch
from consensus_engine.config import ModelConfig
from consensus_engine.orchestrator import run_debate, DebateResult


@pytest.fixture
def judge_config():
    return ModelConfig(
        name="judge-model",
        endpoint="https://api.test.com/v1/chat/completions",
        api_key="sk-j",
        model="judge-v1",
        role="judge",
    )


@pytest.fixture
def participant_configs():
    return [
        ModelConfig(
            name=f"model-{i}",
            endpoint=f"https://api.test{i}.com/v1/chat/completions",
            api_key=f"sk-{i}",
            model=f"test-v{i}",
        )
        for i in range(2)
    ]


@pytest.fixture
def all_configs(judge_config, participant_configs):
    return [judge_config] + participant_configs


class TestRunDebate:
    @pytest.mark.asyncio
    async def test_full_flow_returns_result(self, all_configs):
        with patch("consensus_engine.orchestrator.ModelClient") as MockClient:
            instance = AsyncMock()
            instance.chat.return_value = "mock response"
            instance.config = all_configs[0]
            MockClient.return_value = instance

            result = await run_debate(
                configs=all_configs,
                task="测试任务",
                content="测试上下文",
                scene="planning",
            )

            assert isinstance(result, DebateResult)
            assert result.final_plan == "mock response"
            assert len(result.models_participated) > 0
            assert result.models_failed == []

    @pytest.mark.asyncio
    async def test_partial_failure_continues(self, all_configs):
        call_count = 0

        async def side_effect(system, user):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("model timeout")
            return "mock response"

        with patch("consensus_engine.orchestrator.ModelClient") as MockClient:
            instance = AsyncMock()
            instance.chat.side_effect = side_effect
            instance.config = all_configs[0]
            MockClient.return_value = instance

            result = await run_debate(
                configs=all_configs,
                task="测试任务",
                content="测试上下文",
                scene="planning",
            )
            # 即使部分失败也应返回结果
            assert isinstance(result, DebateResult)

    @pytest.mark.asyncio
    async def test_review_mode_parameter(self, all_configs):
        with patch("consensus_engine.orchestrator.ModelClient") as MockClient:
            instance = AsyncMock()
            instance.chat.return_value = "mock response"
            instance.config = all_configs[0]
            MockClient.return_value = instance

            result = await run_debate(
                configs=all_configs,
                task="t",
                content="c",
                scene="review",
                review_mode="full",
            )
            assert isinstance(result, DebateResult)
```

**Step 2: 运行测试确认失败**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 orchestrator.py**

`consensus_engine/orchestrator.py`:
```python
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
    client: ModelClient, system: str, user: str
) -> tuple[str, str | None]:
    """安全调用模型，失败返回 (name, None)。"""
    try:
        result = await client.chat(system, user)
        return client.config.name, result
    except Exception as e:
        print(
            f"[consensus-engine] {client.config.name} 失败：{e}",
            file=sys.stderr,
        )
        return client.config.name, None


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
        _safe_chat(clients[c.name], system_p, user_p) for c in all_debaters
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
        # 每个模型评审其他每个模型的提案
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
            review_tasks.append(_safe_chat(client, system_r, user_r))

        results_r = await asyncio.gather(*review_tasks)
        for name, result in results_r:
            if result is None:
                if name not in failed:
                    failed.append(name)
            else:
                reviews[name] = result
    else:
        # summarized: 每个模型看到所有提案的汇总
        system_r, user_r = build_review_prompt(task, proposals)
        review_tasks = [
            _safe_chat(clients[name], system_r, user_r)
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
    if judge_config.name in failed:
        raise RuntimeError("Judge 模型在之前阶段已失败，无法进行汇总")

    system_s, user_s = build_synthesis_prompt(task, proposals, reviews)
    judge_client = clients[judge_config.name]
    _, synthesis = await _safe_chat(judge_client, system_s, user_s)

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
```

**Step 4: 运行测试确认通过**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_orchestrator.py -v`
Expected: 全部 PASS

**Step 5: Commit**

```bash
git add consensus_engine/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add three-phase debate orchestrator"
```

---

### Task 7: FastMCP 服务器入口（server.py）

**Files:**
- Create: `consensus_engine/server.py`
- Create: `tests/test_server.py`

**Step 1: 写失败测试**

`tests/test_server.py`:
```python
import json
import pytest
from unittest.mock import patch, AsyncMock
from consensus_engine.server import create_app


VALID_CONFIGS = json.dumps([
    {
        "name": "judge",
        "endpoint": "https://api.test.com/v1/chat/completions",
        "api_key": "sk-j",
        "model": "j-v1",
        "role": "judge",
    },
    {
        "name": "model-a",
        "endpoint": "https://api.a.com/v1/chat/completions",
        "api_key": "sk-a",
        "model": "a-v1",
    },
])


class TestCreateApp:
    def test_returns_mcp_instance(self, monkeypatch, tmp_path):
        monkeypatch.setenv("LOCAL_MODEL_CONFIGS", VALID_CONFIGS)
        monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))
        app = create_app()
        assert app is not None
```

**Step 2: 运行测试确认失败**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_server.py -v`
Expected: FAIL — `ModuleNotFoundError`

**Step 3: 实现 server.py**

`consensus_engine/server.py`:
```python
"""FastMCP 服务器入口。"""

import json
import sys
from enum import Enum
from typing import Literal

from fastmcp import FastMCP

from consensus_engine.config import load_model_configs, load_project_root
from consensus_engine.orchestrator import run_debate
from consensus_engine.writer import write_consensus


def create_app() -> FastMCP:
    """创建并配置 FastMCP 应用实例。"""
    configs = load_model_configs()
    project_root = load_project_root()

    model_names = [c.name for c in configs]
    judge_name = next(c.name for c in configs if c.role == "judge")
    print(
        f"[consensus-engine] 已加载 {len(configs)} 个模型：{model_names}，Judge：{judge_name}",
        file=sys.stderr,
    )

    mcp = FastMCP("consensus-engine")

    @mcp.tool()
    async def run_consensus_debate(
        task: str,
        content: str,
        scene: Literal["planning", "review", "arch", "debug"],
        review_mode: Literal["summarized", "full"] = "summarized",
    ) -> dict:
        """运行多模型共识博弈。

        并发调用多个 AI 模型进行三阶段博弈（提案→评审→汇总），
        输出共识方案并自动存档到本地 docs/ 目录。

        Args:
            task: 核心任务描述
            content: 相关代码或上下文
            scene: 场景类型 (planning/review/arch/debug)
            review_mode: 评审模式 (summarized/full)，默认 summarized
        """
        result = await run_debate(
            configs=configs,
            task=task,
            content=content,
            scene=scene,
            review_mode=review_mode,
        )

        filepath = write_consensus(
            project_root=project_root,
            scene=scene,
            task=task,
            models=result.models_participated,
            final_plan=result.final_plan,
            proposals=result.proposals,
            reviews=result.reviews,
        )

        relative_path = filepath.relative_to(project_root)
        print(
            f"[Done] 共识结论已保存至 {relative_path}",
            file=sys.stderr,
        )

        return {
            "final_plan": result.final_plan,
            "file_path": str(relative_path),
            "models_participated": result.models_participated,
            "models_failed": result.models_failed,
        }

    return mcp


app = create_app()


def main():
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
```

**Step 4: 运行测试确认通过**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/test_server.py -v`
Expected: 全部 PASS

**Step 5: 补充 `consensus_engine/__main__.py`**

`consensus_engine/__main__.py`:
```python
"""支持 python -m consensus_engine.server 启动。"""
from consensus_engine.server import main

main()
```

**Step 6: Commit**

```bash
git add consensus_engine/server.py consensus_engine/__main__.py tests/test_server.py
git commit -m "feat: add FastMCP server with run_consensus_debate tool"
```

---

### Task 8: 全量测试 + 部署文档

**Files:**
- Modify: `pyproject.toml` (添加 entry point)

**Step 1: 运行全量测试**

Run: `cd /Users/leone/AI/fake-verdent && python -m pytest tests/ -v --tb=short`
Expected: 全部 PASS

**Step 2: 添加 pyproject.toml entry point**

在 `pyproject.toml` 中添加：
```toml
[project.scripts]
consensus-engine = "consensus_engine.server:main"
```

**Step 3: 验证 MCP 启动命令**

Run: `cd /Users/leone/AI/fake-verdent && LOCAL_MODEL_CONFIGS='[{"name":"test","endpoint":"http://localhost","api_key":"x","model":"m","role":"judge"},{"name":"t2","endpoint":"http://localhost","api_key":"y","model":"m2"}]' PROJECT_ROOT=/tmp timeout 2 python -m consensus_engine.server 2>&1 || true`
Expected: stderr 输出模型加载信息，然后因无 stdin 输入超时退出

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add entry point and verify full test suite"
```

---

## 部署说明

完成所有 Task 后，用户通过以下命令注入 MCP：

```bash
claude mcp add consensus-engine \
  -e LOCAL_MODEL_CONFIGS='[{"name":"deepseek","endpoint":"https://api.deepseek.com/v1/chat/completions","api_key":"sk-xxx","model":"deepseek-chat","role":"judge"},{"name":"qwen","endpoint":"https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions","api_key":"sk-yyy","model":"qwen-plus"}]' \
  -e PROJECT_ROOT="$(pwd)" \
  -- python -m consensus_engine.server
```
