# 仓库分析报告：Three-Cobblers (三个臭皮匠)

> 生成时间：2026-03-20 11:08
> 本文档由代码分析技能自动生成。

## 1. 项目概览

- **仓库名称**：Three-Cobblers (consensus-engine)
- **总文件数**：22（不含 .git、__pycache__ 等）
- **总代码行数**：约 2,714 行（含文档和配置）
- **核心代码行数**：约 440 行（Python 源码）+ 约 350 行（测试代码）
- **涉及语言**：2 种（Python、Markdown）

## 2. README 内容

项目为**多模型共识博弈 MCP Server**，并发调用多个 AI 模型进行三阶段博弈（提案 → 交叉评审 → 汇总），输出共识方案。

核心工作流程：
1. Phase 1：各模型独立提案（并发）
2. Phase 2：交叉评审其他模型的提案（并发）
3. Phase 3：Judge 汇总所有提案和评审，输出最终共识

支持 stdio 和 SSE 两种传输模式，可通过 Claude Code 的 MCP 机制集成使用。

## 3. 语言分布

| 语言 | 文件数 | 代码行数 | 占比 |
| :--- | ---: | ---: | ---: |
| Python | 12 | ~790 | 55% |
| Markdown | 6 | ~1,706 | 40% |
| TOML | 1 | 26 | 2% |
| 其他（配置） | 3 | ~20 | 3% |

## 4. 目录结构

```
Three-Cobblers/
├── README.md                           # 项目说明文档
├── pyproject.toml                      # Python 项目配置
├── consensus-engine.service.example    # systemd 服务配置模板
├── .gitignore
├── consensus_engine/                   # 核心源码包
│   ├── __init__.py                     # 包初始化
│   ├── __main__.py                     # python -m 入口
│   ├── server.py                       # FastMCP 服务器入口
│   ├── orchestrator.py                 # 三阶段博弈编排器
│   ├── client.py                       # 异步模型客户端
│   ├── config.py                       # 配置解析
│   ├── templates.py                    # Prompt 模板
│   └── writer.py                       # Markdown 文件生成
├── tests/                              # 测试目录
│   ├── __init__.py
│   ├── test_config.py                  # 配置解析测试
│   ├── test_client.py                  # 客户端测试
│   ├── test_orchestrator.py            # 编排器测试
│   ├── test_server.py                  # 服务器测试
│   ├── test_templates.py              # 模板测试
│   └── test_writer.py                  # 写入器测试
└── docs/                               # 文档目录
    ├── prd.md                          # 产品需求文档
    ├── plans/                          # 设计与实现计划
    └── archs/                          # 架构文档
```

## 5. 关键配置文件

### pyproject.toml
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
```

### consensus-engine.service.example
systemd 服务配置模板，用于在服务器上以 SSE 模式部署。

## 6. 核心代码文件（按代码行数排序）

| 文件路径 | 语言 | 行数 |
| :--- | :--- | ---: |
| consensus_engine/orchestrator.py | Python | 139 |
| tests/test_orchestrator.py | Python | 97 |
| consensus_engine/client.py | Python | 82 |
| consensus_engine/server.py | Python | 79 |
| tests/test_config.py | Python | 77 |
| consensus_engine/writer.py | Python | 73 |
| consensus_engine/config.py | Python | 73 |
| consensus_engine/templates.py | Python | 62 |
| tests/test_writer.py | Python | 61 |
| tests/test_client.py | Python | 54 |
| tests/test_templates.py | Python | 51 |
| tests/test_server.py | Python | 29 |

## 7. 模块结构分析

| 模块/目录 | 文件数 | 代码行数 |
| :--- | ---: | ---: |
| consensus_engine/ (核心源码) | 7 | ~440 |
| tests/ (测试) | 7 | ~370 |
| docs/ (文档) | 4 | ~1,610 |
| 根目录 (配置/README) | 4 | ~240 |

## 8. 深度分析

### 8.1 项目概述

Three-Cobblers（三个臭皮匠）是一个**多模型共识博弈 MCP Server**。它的核心理念是"三个臭皮匠赛过诸葛亮"——通过让多个 AI 模型（通常 2-5 个廉价模型）进行结构化辩论，达成比单一模型更可靠的共识方案。

项目解决的核心问题：单一 LLM 的决策偏差和幻觉风险，通过多模型交叉验证提高输出质量。

### 8.2 技术架构

**架构模式**：单体 Python 应用，MCP（Model Context Protocol）服务端

**核心技术选型**：
- **FastMCP**（>=2.0.0）：MCP 协议服务器框架，支持 stdio 和 SSE 传输
- **httpx**（>=0.27.0）：异步 HTTP 客户端，用于并发调用多个 AI 模型 API
- **Python asyncio**：原生异步并发，Phase 1/2 阶段并行调用多模型

**传输模式**：
- `stdio`（默认）：本地集成模式，通过 `claude mcp add` 配置
- `sse`：远程部署模式，通过 systemd 服务运行，端口 38517

**配置注入**：通过 `LOCAL_MODEL_CONFIGS` 环境变量注入模型配置（JSON 数组），包含 API Key，不落盘。

### 8.3 功能模块分析

**1. 配置模块** (`config.py`)
- 从 `LOCAL_MODEL_CONFIGS` 环境变量解析模型配置
- 验证至少 2 个模型，且恰好 1 个 judge
- 支持 `openai` 和 `anthropic` 两种协议
- 数据结构使用 `@dataclass(frozen=True)` 确保不可变

**2. 客户端模块** (`client.py`)
- `ModelClient` 类封装单模型的异步 HTTP 调用
- 支持 OpenAI Chat Completion 和 Anthropic Messages 双协议
- 超时时间 300s，适应大模型较慢的推理速度
- Anthropic 协议自动拼接 `/messages` 路径

**3. 编排器模块** (`orchestrator.py`) — 核心模块
- `run_debate()` 函数实现三阶段博弈流程
- Phase 1：所有模型（含 Judge）并发生成提案
- Phase 2：交叉评审，支持 `summarized`（所有提案一起评）和 `full`（排除自己的提案）两种模式
- Phase 3：Judge 模型汇总所有提案和评审意见，输出最终共识
- `_safe_chat()` 容错包装，单模型失败不影响整体流程
- 最少需要 2 个模型成功提案才继续

**4. Prompt 模板模块** (`templates.py`)
- `build_proposal_prompt`：构建提案阶段 prompt
- `build_review_prompt`：构建交叉评审 prompt
- `build_synthesis_prompt`：构建汇总阶段 prompt
- 所有 prompt 使用中文编写，面向中文用户

**5. 写入器模块** (`writer.py`)
- `build_markdown()`：生成结构化的共识结论 Markdown
- `write_consensus()`：按场景写入对应子目录（plans/reviews/archs/debugs）
- 文件命名规范：`YYYYMMDD_HHMM_{suffix}.md`
- 注意：当前 `server.py` 中未调用 `writer.py`，存档功能交由调用方处理

**6. 服务器模块** (`server.py`)
- `create_app()` 创建 FastMCP 实例并注册 `run_consensus_debate` 工具
- 支持通过 `MCP_TRANSPORT` 环境变量切换 stdio/sse 模式
- 工具返回纯数据字典，不包含文件写入操作

### 8.4 API/接口设计

**MCP 工具**：`run_consensus_debate`

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task` | string | 是 | 核心任务描述 |
| `content` | string | 是 | 相关代码或上下文 |
| `scene` | Literal["planning","review","arch","debug"] | 是 | 场景类型 |
| `review_mode` | Literal["summarized","full"] | 否 | 评审模式，默认 summarized |

**返回结构**：
```json
{
  "final_plan": "最终共识方案（Markdown）",
  "models_participated": ["model-a", "model-b", "model-c"],
  "models_failed": [],
  "proposals": {"model-a": "...", "model-b": "..."},
  "reviews": {"model-a": "...", "model-b": "..."}
}
```

### 8.5 数据模型

项目无数据库依赖，核心数据结构：

- **`ModelConfig`** (`config.py:10`)：模型配置，frozen dataclass
  - name, endpoint, api_key, model, role, protocol

- **`DebateResult`** (`orchestrator.py:17`)：博弈结果
  - final_plan, models_participated, models_failed, proposals, reviews

### 8.6 代码质量评估

**优点**：
- 代码简洁，模块职责清晰，约 440 行核心代码完成完整功能
- 使用 dataclass 确保数据不可变性
- asyncio + httpx 并发调用模型，性能良好
- `_safe_chat()` 容错设计，单模型失败不影响整体
- 测试覆盖所有模块（6 个测试文件对应 6 个源码文件）
- 支持 OpenAI/Anthropic 双协议，灵活性高

**潜在问题**：
- `writer.py` 已实现但未在 `server.py` 中使用，存档逻辑交由调用方处理（PRD 与实现有偏差）
- `client.py` 每次请求都新建 `httpx.AsyncClient`，未复用连接池
- 没有重试机制，模型 API 偶发超时会直接失败
- `templates.py` 中的 prompt 较为简单，scene 参数未影响 prompt 内容差异化

### 8.7 改进建议

1. **连接池复用**：`ModelClient` 应在实例级维护 `httpx.AsyncClient`，避免每次请求都创建新连接
2. **重试机制**：对模型 API 调用添加指数退避重试（1-2 次）
3. **场景化 Prompt**：`templates.py` 应根据不同 scene 生成差异化的 prompt 指令
4. **流式输出**：支持 SSE 流式返回博弈进度，提升用户体验
5. **多轮博弈**：当前仅单轮，可扩展为多轮迭代直到达成共识
6. **token 统计**：记录每次博弈消耗的 token 数量，便于成本控制
