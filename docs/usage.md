# Consensus-Engine MCP 使用指南

## 快速开始

### 1. 安装

```bash
# 克隆项目
git clone <repository-url>
cd fake-verdent

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -e .
```

### 2. 配置

Consensus-Engine MCP 支持两种配置方式：环境变量（推荐）和配置文件。

#### 方式一：环境变量（推荐）

```bash
export MCP_MODELS='[
  {"name": "deepseek-v3", "url": "https://api.deepseek.com/v1/chat/completions", "key": "sk-your-api-key"},
  {"name": "qwen-max", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "key": "sk-your-api-key"},
  {"name": "llama3-70b", "url": "https://api.openai.com/v1/chat/completions", "key": "sk-your-api-key", "provider": "openai"}
]'
export LOG_LEVEL=INFO
```

#### 方式二：配置文件

创建 `config.json` 文件：

```json
[
  {
    "name": "deepseek-v3",
    "url": "https://api.deepseek.com/v1/chat/completions",
    "key": "sk-your-api-key",
    "provider": "openai",
    "timeout": 60,
    "max_retries": 2
  },
  {
    "name": "qwen-max",
    "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
    "key": "sk-your-api-key",
    "provider": "openai"
  },
  {
    "name": "llama3-70b",
    "url": "https://api.openai.com/v1/chat/completions",
    "key": "sk-your-api-key",
    "provider": "openai"
  }
]
```

参考 `config.example.json` 获取完整示例。

### 3. 运行

#### 作为 MCP 服务器运行

```bash
# SSE/HTTP 模式（默认端口 8000）
consensus-engine --transport sse --port 8000

# stdio 模式（用于 Claude Desktop）
consensus-engine --transport stdio
```

#### 作为 Python 模块使用

```python
import asyncio
from consensus_engine.config import ConfigManager
from consensus_engine.orchestrator import DebateOrchestrator, ConsensusInput
from consensus_engine.writer import ResultWriter

async def main():
    # 加载配置
    config_manager = ConfigManager()
    models = config_manager.get_models()

    # 创建编排器
    orchestrator = DebateOrchestrator(models, scene="planning")

    # 运行辩论
    input_data = ConsensusInput(
        task="设计一个微服务架构的电商平台",
        scene="planning",
        content="需要支持高并发、可扩展、容错能力强"
    )
    output = await orchestrator.run_debate(input_data)

    # 写入结果
    writer = ResultWriter()
    output_path = writer.write(
        scene=input_data.scene,
        task=input_data.task,
        output=output
    )
    print(f"结果已保存到: {output_path}")

asyncio.run(main())
```

## Claude Desktop 配置

在 Claude Desktop 的配置文件中添加：

### macOS

```json
{
  "mcpServers": {
    "consensus-engine": {
      "command": "/path/to/venv/bin/consensus-engine",
      "args": ["--transport", "stdio"],
      "env": {
        "MCP_MODELS": "[{\"name\": \"deepseek-v3\", \"url\": \"https://api.deepseek.com/v1/chat/completions\", \"key\": \"sk-your-api-key\"}, {\"name\": \"qwen-max\", \"url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions\", \"key\": \"sk-your-api-key\"}]",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

配置文件位置：`~/Library/Application Support/Claude/claude_desktop_config.json`

### Windows

```json
{
  "mcpServers": {
    "consensus-engine": {
      "command": "C:\\path\\to\\venv\\Scripts\\consensus-engine.exe",
      "args": ["--transport", "stdio"],
      "env": {
        "MCP_MODELS": "[{\"name\": \"deepseek-v3\", \"url\": \"https://api.deepseek.com/v1/chat/completions\", \"key\": \"sk-your-api-key\"}, {\"name\": \"qwen-max\", \"url\": \"https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions\", \"key\": \"sk-your-api-key\"}]",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

配置文件位置：`%APPDATA%\Claude\claude_desktop_config.json`

## 使用场景

Consensus-Engine MCP 支持四种场景，每种场景都有专门的提示词模板：

### 1. Planning（任务规划）

**适用场景**：任务拆解、依赖分析、项目规划

**示例**：
```
任务：开发一个用户认证系统
场景：planning
上下文：需要支持OAuth2.0、JWT、多因素认证
```

**输出**：结构化的任务分解、优先级排序、资源评估

### 2. Review（代码审查）

**适用场景**：代码规范审查、Bug审计、性能优化

**示例**：
```
任务：审查以下Python代码的性能问题
场景：review
上下文：[代码内容]
```

**输出**：正确性、可读性、可维护性、性能、安全性维度的审查报告

### 3. Architecture（架构设计）

**适用场景**：技术选型、系统架构设计、技术方案评审

**示例**：
```
任务：设计一个高并发的消息推送系统
场景：arch
上下文：预期用户量100万，消息峰值10万/秒
```

**输出**：模块化设计、可扩展性方案、技术栈选型、架构图

### 4. Debug（问题调试）

**适用场景**：问题定位、根因分析、故障排查

**示例**：
```
任务：数据库连接池耗尽问题
场景：debug
上下文：[错误日志、环境信息]
```

**输出**：问题复现步骤、根因分析、解决方案、预防措施

## 输出目录映射

共识结果按场景类型组织到不同的目录：

| 场景 | 输出目录 | 说明 |
|------|---------|------|
| planning | `docs/plans/` | 任务规划方案 |
| review | `docs/reviews/` | 代码审查报告 |
| arch | `docs/architecture/` | 架构设计文档 |
| debug | `docs/debugging/` | 调试分析报告 |

输出文件命名格式：`{timestamp}-{scene}-{task}.md`

例如：`20240318-143022-planning-design-ecommerce-platform.md`

## MCP 工具说明

### `run_consensus`

运行多模型辩论并生成共识结果。

**参数**：
- `task`（必需）：待讨论的任务或问题
- `scene`（可选）：场景类型，默认 "planning"
  - 可选值：`planning`、`review`、`arch`、`debug`
- `content`（可选）：额外的上下文信息

**返回**：
- `final_consensus`：最终共识答案
- `debate_summary`：讨论摘要
- `rounds_executed`：执行轮数
- `models_participated`：参与模型列表
- `total_duration_ms`：总耗时（毫秒）
- `output_file`：输出文件路径

### `get_supported_scenes`

获取所有支持的场景列表。

**返回**：场景名称列表

## 最佳实践

1. **模型选择**：至少配置 2 个模型（建议 3-5 个），最后一个模型将作为 judge
2. **API 密钥安全**：使用环境变量存储 API 密钥，不要提交到版本控制
3. **超时设置**：根据模型响应速度调整 `timeout` 参数（默认 60 秒）
4. **重试机制**：网络不稳定时增加 `max_retries` 参数（默认 2 次）
5. **日志级别**：开发时使用 `DEBUG`，生产环境使用 `INFO` 或 `WARNING`

## 故障排除

### 问题：无法加载模型配置

**解决方案**：
- 检查环境变量 `MCP_MODELS` 是否正确设置
- 确认 JSON 格式正确，可以使用在线 JSON 验证工具
- 查看配置文件路径是否正确（默认 `config.json`）

### 问题：模型调用失败

**解决方案**：
- 验证 API 密钥是否有效
- 检查网络连接和 API 端点 URL
- 增加超时时间：`"timeout": 120`
- 查看日志输出：设置 `LOG_LEVEL=DEBUG`

### 问题：Claude Desktop 无法连接

**解决方案**：
- 确认命令路径使用绝对路径
- 检查 stdio 模式是否正确启动
- 查看 Claude Desktop 日志文件
- 确保环境变量在配置中正确设置

## 示例代码

完整的使用示例请参考 `examples/test_debate.py`。

运行示例：
```bash
python examples/test_debate.py
```

## 技术支持

- GitHub Issues：<repository-url>/issues
- 文档：<repository-url>/blob/main/docs/usage.md
