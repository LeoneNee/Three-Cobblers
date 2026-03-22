# Three-Cobblers (三个臭皮匠)

多模型共识博弈 MCP Server —— 并发调用多个 AI 模型进行三阶段博弈（提案 → 交叉评审 → 汇总），输出共识方案。

## 工作原理

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  模型 A      │  │  模型 B      │  │  模型 C      │
│ (participant)│  │ (participant)│  │   (judge)    │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       ▼                ▼                ▼
  Phase 1: 各模型独立提案（并发）
       │                │                │
       ▼                ▼                ▼
  Phase 2: 交叉评审其他模型的提案（并发）
       │                │                │
       └────────────────┼────────────────┘
                        ▼
  Phase 3: Judge 汇总所有提案和评审，输出最终共识
```

## 快速开始

### 1. 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 配置模型

设置环境变量 `LOCAL_MODEL_CONFIGS`，JSON 数组格式，至少 2 个模型，其中恰好 1 个 judge：

```bash
export LOCAL_MODEL_CONFIGS='[
  {"name":"model-a", "endpoint":"https://api.example.com/v1/chat/completions", "api_key":"sk-xxx", "model":"model-a", "role":"participant", "protocol":"openai"},
  {"name":"model-b", "endpoint":"https://api.example.com/v1", "api_key":"sk-yyy", "model":"model-b", "role":"participant", "protocol":"anthropic"},
  {"name":"model-c", "endpoint":"https://api.example.com/v1", "api_key":"sk-zzz", "model":"model-c", "role":"judge", "protocol":"anthropic"}
]'
```

每个模型配置字段说明：

| 字段 | 必填 | 说明 |
|------|------|------|
| `name` | 是 | 模型名称（用于日志和结果标识） |
| `endpoint` | 是 | API 地址 |
| `api_key` | 是 | API 密钥 |
| `model` | 是 | 模型 ID |
| `role` | 否 | `participant`（默认）或 `judge` |
| `protocol` | 否 | `openai`（默认）或 `anthropic` |

**protocol 说明：**
- `openai`：endpoint 需要完整路径，如 `.../v1/chat/completions`
- `anthropic`：endpoint 写到 `.../v1` 即可，会自动拼接 `/messages`

### 3. 本地运行（stdio 模式）

```bash
python -m consensus_engine
```

### 4. 在 Claude Code 中使用

**方式一：stdio 本地模式**

```bash
claude mcp add consensus-engine -- python -m consensus_engine
```

需要设置环境变量，或通过 `--env` 传入 `LOCAL_MODEL_CONFIGS`。

**方式二：HTTP 远程模式（推荐）**

在服务器上部署后：

```json
{
  "mcpServers": {
    "consensus-engine": {
      "type": "http",
      "url": "http://175.24.134.13:38517",
      "headers": {
        "Authorization": "Bearer your-secret-api-key-here"
      }
    }
  }
}
```

**方式三：SSE 远程模式**

```bash
claude mcp add --transport sse consensus-engine http://your-server:38517/sse
```

如果服务器启用了 API Key 验证，需要在 `.kiro/settings/mcp.json` 中添加：

```json
{
  "mcpServers": {
    "consensus-engine": {
      "transport": "sse",
      "url": "http://your-server:38517/sse",
      "headers": {
        "Authorization": "Bearer your-secret-api-key-here"
      }
    }
  }
}
```

### 5. 在对话中使用

配置完成后，**无需任何特殊命令**，直接用自然语言对话即可触发：

```
你：帮我用共识博弈分析一下这段代码的架构设计
你：用多模型辩论评审一下这个方案的可行性
你：对这个 bug 进行共识博弈，找出根因和修复方案
```

Claude 会自动识别意图并调用 `run_consensus_debate` 工具，你会看到三个模型依次完成提案、评审、汇总的全过程。

**场景关键词对照：**

| 你的描述 | 对应 scene |
|---------|-----------|
| 架构设计、技术选型、方案对比 | `arch` |
| 代码评审、方案评审 | `review` |
| 需求分析、任务规划 | `planning` |
| 排查 bug、定位问题 | `debug` |

## 服务器部署

### 1. 克隆并安装

```bash
git clone https://github.com/LeoneNee/Three-Cobblers.git
cd Three-Cobblers
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### 2. 配置 systemd 服务

```bash
# 复制示例文件并填入真实 API Key
cp consensus-engine.service.example /etc/systemd/system/consensus-engine.service
# 编辑填入你的 API Key 和 MCP_API_KEY
sudo nano /etc/systemd/system/consensus-engine.service

# 启动服务
sudo systemctl daemon-reload
sudo systemctl enable consensus-engine
sudo systemctl start consensus-engine
```

### 3. 验证

**无验证模式（未设置 MCP_API_KEY）：**
```bash
curl -I http://localhost:38517/sse
# 应返回 HTTP/1.1 200 OK
```

**验证模式（已设置 MCP_API_KEY）：**
```bash
# 无 token 会返回 401
curl -I http://localhost:38517/sse

# 带正确 token 返回 200
curl -H "Authorization: Bearer your-secret-api-key-here" -I http://localhost:38517/sse
```

## MCP 工具接口

### run_consensus_debate

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `task` | string | 是 | 核心任务描述 |
| `content` | string | 是 | 相关代码或上下文 |
| `scene` | string | 是 | 场景类型：`planning` / `review` / `arch` / `debug` |
| `review_mode` | string | 否 | 评审模式：`summarized`（默认）/ `full` |

**评审模式说明：**

| 模式 | 行为 | 适用场景 |
|------|------|---------|
| `summarized` | 每个模型评审**所有提案**（含自己的），统一对比 | 快速评审，token 消耗少 |
| `full` | 每个模型只评审**其他模型**的提案，排除自己的 | 更客观的交叉评审，适合重要决策 |

> 当前为单轮博弈：提案 → 评审 → 汇总，共 3 个阶段各执行 1 次。

**返回字段：**

| 字段 | 说明 |
|------|------|
| `final_plan` | Judge 汇总的最终共识方案（Markdown） |
| `models_participated` | 成功参与的模型列表 |
| `models_failed` | 失败的模型列表 |
| `proposals` | 各模型的原始提案 |
| `reviews` | 各模型的交叉评审意见 |

## 开发

```bash
# 运行测试
pytest

# 项目结构
consensus_engine/
├── server.py        # FastMCP 服务器入口
├── orchestrator.py  # 三阶段博弈编排器
├── client.py        # 异步模型客户端（OpenAI/Anthropic 双协议）
├── config.py        # 配置解析
├── templates.py     # Prompt 模板
└── writer.py        # Markdown 文件生成
```

## License

MIT
