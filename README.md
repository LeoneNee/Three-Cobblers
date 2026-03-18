# Consensus-Engine MCP

多模型博弈共识引擎，通过并发调用多个 AI 模型进行辩论，生成高确定性的执行方案。

## 安装

```bash
pip install -e .
```

## 配置

### 环境变量（推荐）

```bash
export MCP_MODELS='[
  {"name": "deepseek-v3", "url": "https://api.deepseek.com/v1/chat/completions", "key": "sk-xxx"},
  {"name": "qwen-max", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "key": "sk-xxx"}
]'
export LOG_LEVEL=INFO
```

### 配置文件（备选）

创建 `config.json`:

```json
[
  {"name": "deepseek-v3", "url": "https://api.deepseek.com/v1/chat/completions", "key": "sk-xxx", "provider": "openai"},
  {"name": "qwen-max", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "key": "sk-xxx", "provider": "openai"}
]
```

## 运行

```bash
# SSE/HTTP 模式
consensus-engine --transport sse --port 8000

# stdio 模式
consensus-engine --transport stdio
```

## 使用场景

- `planning`: 任务拆解、依赖分析
- `review`: 代码规范、Bug审计
- `arch`: 技术选型、架构设计
- `debug`: 问题定位、根因分析
