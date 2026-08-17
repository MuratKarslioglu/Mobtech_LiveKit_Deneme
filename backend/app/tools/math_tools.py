from __future__ import annotations

from livekit.agents import function_tool

from ..models.tool_config import ToolConfig
from .registry import register_tool


@function_tool()
async def add_numbers(a: float, b: float) -> float:
    """İki sayının toplamını hesaplar.

    Args:
        a: Toplanacak ilk sayı
        b: Toplanacak ikinci sayı
    """
    return a + b


register_tool(
    add_numbers,
    ToolConfig(
        name="add_numbers",
        expected_latency="fast",
        interim_message="Hesaplamayı yapıyorum.",
    ),
)
