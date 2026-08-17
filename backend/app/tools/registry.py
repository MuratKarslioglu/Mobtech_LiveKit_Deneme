from __future__ import annotations

from livekit.agents import llm

from ..models.tool_config import ToolConfig

_configs: dict[str, ToolConfig] = {}
_tools: list[llm.FunctionTool] = []


def register_tool(tool: llm.FunctionTool, config: ToolConfig) -> llm.FunctionTool:
    """Bir `@function_tool` fonksiyonunu, `ToolConfig` metadata'sıyla birlikte
    registry'ye kaydeder. Tool modülleri kendilerini import-time'da bu
    fonksiyonla kaydeder (bkz. `tools/math_tools.py`)."""
    _configs[config.name] = config
    _tools.append(tool)
    return tool


def tool_config(name: str) -> ToolConfig | None:
    return _configs.get(name)


def all_tools() -> list[llm.FunctionTool]:
    """Kayıtlı tüm tool'ları döndürür. Yeni bir tool modülü eklendiğinde
    burada import edilmesi yeterli — çağıran taraf (agent.py) tek tek
    tool modüllerini bilmek zorunda kalmaz."""
    from . import math_tools  # noqa: F401

    return list(_tools)
