# consensus_engine/config.py
import os
import sys
import json
from pathlib import Path
from typing import Literal
from pydantic import BaseModel, Field, ValidationError

class ModelConfig(BaseModel):
    """单个模型配置"""
    name: str = Field(..., description="模型标识名称")
    url: str = Field(..., description="API endpoint URL")
    key: str = Field(..., description="API密钥")
    provider: Literal["openai", "anthropic", "ollama"] = Field(
        default="openai", description="API提供商类型"
    )
    timeout: int = Field(default=60, description="请求超时时间(秒)")
    max_retries: int = Field(default=2, description="最大重试次数")

class ConfigManager:
    """模型配置管理器"""

    DEFAULT_CONFIG_PATH = "config.json"

    def __init__(self, config_path: str | None = None):
        self.config_path = Path(config_path) if config_path else Path(self.DEFAULT_CONFIG_PATH)

    def get_models(self) -> list[ModelConfig]:
        """加载模型配置，优先从环境变量，回退到配置文件"""
        # 1. 尝试从环境变量读取
        env_config = os.environ.get("MCP_MODELS")
        if env_config:
            try:
                data = json.loads(env_config)
                return [ModelConfig(**m) for m in data]
            except (json.JSONDecodeError, ValidationError) as e:
                self._print_error_and_exit(f"环境变量 MCP_MODELS 解析失败: {e}")

        # 2. 回退到配置文件
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text())
                return [ModelConfig(**m) for m in data]
            except (json.JSONDecodeError, ValidationError) as e:
                self._print_error_and_exit(f"配置文件 {self.config_path} 解析失败: {e}")

        # 3. 无配置可用
        self._print_config_guide_and_exit()

    def _print_error_and_exit(self, message: str):
        """打印错误信息并退出"""
        print(f"[Consensus-Engine] {message}", file=sys.stderr)
        sys.exit(1)

    def _print_config_guide_and_exit(self):
        """打印配置教程并退出"""
        print("""[Consensus-Engine] 缺少模型配置！

请通过以下方式之一配置模型：

方式1: 环境变量（推荐）
export MCP_MODELS='[
  {"name": "deepseek-v3", "url": "https://api.deepseek.com/v1/chat/completions", "key": "sk-xxx"},
  {"name": "qwen-max", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "key": "sk-xxx"}
]'

方式2: 配置文件
创建 config.json:
[
  {"name": "deepseek-v3", "url": "https://api.deepseek.com/v1/chat/completions", "key": "sk-xxx"},
  {"name": "qwen-max", "url": "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions", "key": "sk-xxx"}
]

参考: config.example.json
""", file=sys.stderr)
        sys.exit(1)
