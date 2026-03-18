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
