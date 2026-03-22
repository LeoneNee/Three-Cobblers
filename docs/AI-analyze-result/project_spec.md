# 项目规格：Three-Cobblers (三个臭皮匠)

> 本文档为 AI 基于代码分析自动生成的初稿，上传到 AI-PM 平台后将通过脑暴对话进一步完善。

## 1. 项目目标

Three-Cobblers 的核心目标是构建一个**多模型共识博弈引擎**，通过 MCP（Model Context Protocol）协议为 Claude Code 等 AI 开发工具提供"专家委员会"式的决策能力。

项目希望解决单一 LLM 在复杂决策场景（架构设计、代码评审、bug 定位等）中的偏差和幻觉问题。通过让多个 AI 模型进行结构化的三阶段辩论（提案 → 交叉评审 → 汇总），产出比单模型更可靠、更全面的共识方案。

项目名称"三个臭皮匠"源自中国谚语"三个臭皮匠赛过诸葛亮"，寓意多个普通模型的集体智慧可以超越单一强模型的决策质量。

## 2. 目标用户

- **主要用户**：使用 Claude Code 的开发者——需要在开发过程中对架构设计、代码评审、技术方案等进行多角度评估的专业开发人员
- **次要用户**：其他支持 MCP 协议的 AI 开发工具用户，以及需要部署远程共识服务的团队负责人

## 3. 核心功能模块

### 3.1 模型配置管理
- **描述**：通过 `LOCAL_MODEL_CONFIGS` 环境变量注入多模型配置，支持 OpenAI 和 Anthropic 两种 API 协议
- **关键文件**：`consensus_engine/config.py`
- **当前状态**：已实现

### 3.2 三阶段博弈编排
- **描述**：核心博弈流程引擎，包括提案（Proposal）、交叉评审（Cross-Review）、汇总（Synthesis）三个阶段
- **关键文件**：`consensus_engine/orchestrator.py`
- **当前状态**：已实现（单轮博弈）

### 3.3 多协议模型客户端
- **描述**：异步 HTTP 客户端，支持 OpenAI Chat Completion 和 Anthropic Messages 两种协议
- **关键文件**：`consensus_engine/client.py`
- **当前状态**：已实现

### 3.4 Prompt 模板系统
- **描述**：为三个博弈阶段提供结构化的 system/user prompt 模板
- **关键文件**：`consensus_engine/templates.py`
- **当前状态**：已实现（基础版本，scene 参数未差异化）

### 3.5 MCP 服务器
- **描述**：基于 FastMCP 的服务器，暴露 `run_consensus_debate` 工具，支持 stdio 和 SSE 传输
- **关键文件**：`consensus_engine/server.py`
- **当前状态**：已实现

### 3.6 结果存档（Markdown 写入）
- **描述**：将博弈结论生成 Markdown 文档并写入 `docs/` 目录
- **关键文件**：`consensus_engine/writer.py`
- **当前状态**：已实现代码，但 server.py 中未调用（存档交由调用方处理）

### 3.7 评审模式
- **描述**：支持 `summarized`（统一评审所有提案）和 `full`（排除自己的提案进行交叉评审）两种模式
- **关键文件**：`consensus_engine/orchestrator.py`
- **当前状态**：已实现

## 4. 技术约束

- **语言与框架**：Python 3.10+，FastMCP >=2.0.0，httpx >=0.27.0
- **数据库**：无（纯计算服务，状态不持久化）
- **部署方式**：
  - 本地 stdio 模式（通过 claude mcp add 集成）
  - 远程 SSE 模式（通过 systemd 服务部署，端口 38517）
- **第三方依赖**：
  - 运行时：fastmcp, httpx
  - 开发：pytest, pytest-asyncio, respx
  - 构建：hatchling

## 5. 非功能需求（推断）

- **性能**：Phase 1 和 Phase 2 的模型调用均为并发执行（asyncio.gather），单轮博弈延迟取决于最慢的模型响应（超时 300s）
- **安全性**：API Key 通过环境变量注入，不落盘、不出现在代码或配置文件中；服务端不做认证（适合内网部署）
- **可扩展性**：支持 2-5 个模型参与，理论上可扩展模型数量；单轮博弈架构可扩展为多轮迭代
- **容错性**：单模型失败不影响整体流程，最少 2 个模型成功即可继续

## 6. 待澄清事项

- **writer.py 的定位**：PRD 要求自动存档，但当前实现中 server.py 未调用 writer.py，存档逻辑交由 MCP 调用方（如 Claude Code）处理。是否需要在服务端恢复自动存档？
- **多轮博弈**：当前仅支持单轮博弈（提案→评审→汇总各 1 次），是否有计划支持多轮迭代直到达成更高质量共识？
- **场景差异化 Prompt**：`scene` 参数（planning/review/arch/debug）目前未影响 Prompt 内容，是否需要根据场景定制不同的提问策略？
- **远程部署安全**：SSE 模式默认绑定 0.0.0.0 且无认证，公网部署是否需要添加 API Key 或 JWT 认证？
- **成本控制**：是否需要 token 用量统计和预算限制机制？
- **并发限制**：多用户同时调用时是否需要队列或限流？
