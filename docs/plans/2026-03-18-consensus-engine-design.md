# Consensus-Engine MCP 服务器设计文档

> 日期：2026-03-18 | 状态：已确认

## 1. 产品目标

构建一个通过 MCP 协议运行的"专家委员会"决策中枢，并发调用 2-5 个 OpenAI 兼容模型进行三阶段博弈，将共识结论自动持久化到本地项目 `docs/` 目录。

## 2. 技术栈

- **语言**：Python 3.10+
- **MCP 框架**：FastMCP
- **HTTP 客户端**：httpx (async)
- **模型接口**：统一 OpenAI Chat Completions 兼容格式

## 3. 整体架构

```
Claude Code (调用方)
  │ MCP stdio
  ▼
consensus-engine (FastMCP Server)
  ├── server.py          # 入口 + 环境变量解析
  ├── client.py          # 异步模型调用
  ├── orchestrator.py    # 三阶段博弈编排
  ├── writer.py          # Markdown 生成 + 文件写入
  └── templates.py       # Prompt 模板
```

## 4. 配置注入

### 4.1 LOCAL_MODEL_CONFIGS 环境变量

JSON 数组格式：

```json
[
  {
    "name": "deepseek",
    "endpoint": "https://api.deepseek.com/v1/chat/completions",
    "api_key": "sk-xxx",
    "model": "deepseek-chat",
    "role": "judge"
  },
  {
    "name": "qwen",
    "endpoint": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "api_key": "sk-yyy",
    "model": "qwen-plus"
  }
]
```

**验证规则：**
- 至少 2 个模型配置
- 恰好 1 个标记 `"role": "judge"`，未标记默认 `"participant"`
- `endpoint`、`api_key`、`model` 为必填字段

### 4.2 PROJECT_ROOT 环境变量

项目根目录绝对路径，缺失则 fallback 到 cwd 并 stderr 警告。

## 5. 三阶段博弈流程

### Phase 1 — Proposal（并发提案）

所有 participant 模型并发接收相同 prompt，生成独立提案。失败模型跳过并 stderr 记录。

### Phase 2 — Cross-Review（交叉评审）

两种策略，通过 `review_mode` 参数控制，默认 `summarized`：

- **summarized**（默认）：所有提案拼成摘要，每个 participant 并发评审
- **full**：每个模型逐一评审其他每个提案（调用量 N×(N-1)）

### Phase 3 — Synthesis（Judge 汇总）

仅由 Judge 模型执行，综合提案和评审意见，输出最终共识方案（Markdown）。

### 容错

任一阶段只要 ≥2 个模型成功（且含 Judge），流程继续。Judge 失败则报错返回。

## 6. 文件持久化

### 存档路径映射

| scene      | 目录              | 文件名示例                     |
|------------|-------------------|-------------------------------|
| `planning` | `docs/plans/`     | `20260318_2330_plan.md`       |
| `review`   | `docs/reviews/`   | `20260318_2330_review.md`     |
| `arch`     | `docs/archs/`     | `20260318_2330_arch.md`       |
| `debug`    | `docs/debugs/`    | `20260318_2330_debug.md`      |

### 生成的 Markdown 结构

```markdown
# 共识结论：{task}

> 场景：{scene} | 时间：{timestamp} | 参与模型：{model_list}

## 最终方案
{judge 输出的共识内容}

## 博弈摘要
### 提案阶段
- **{model_name}**: {提案摘要}
### 评审阶段
- **{model_name}**: {评审要点}
### 裁判总结
{judge 的综合逻辑}
```

## 7. MCP Tool 接口

### run_consensus_debate

**输入：**
- `task` (string): 核心任务描述
- `content` (string): 相关代码或上下文
- `scene` (enum): `planning` | `review` | `arch` | `debug`
- `review_mode` (enum, 可选): `summarized` | `full`，默认 `summarized`

**输出 JSON：**
```json
{
  "final_plan": "（完整 Markdown 共识内容）",
  "file_path": "docs/plans/20260318_2330_plan.md",
  "models_participated": ["deepseek", "qwen", "moonshot"],
  "models_failed": []
}
```

## 8. 实时反馈

通过 stderr 输出各阶段状态：
- `[Phase 1/3] Requesting proposals from 3 models...`
- `[Phase 1/3] deepseek responded (245 tokens)`
- `[Phase 2/3] Cross-review in progress (summarized mode)...`
- `[Phase 3/3] Judge (deepseek) synthesizing final consensus...`
- `[Done] Consensus saved to docs/plans/20260318_2330_plan.md`

## 9. 部署方式

```bash
claude mcp add consensus-engine \
  -e LOCAL_MODEL_CONFIGS='[{"name":"deepseek","endpoint":"...","api_key":"sk-xxx","model":"deepseek-chat","role":"judge"},{"name":"qwen","endpoint":"...","api_key":"sk-yyy","model":"qwen-plus"}]' \
  -e PROJECT_ROOT=/path/to/project \
  -- python -m consensus_engine.server
```
