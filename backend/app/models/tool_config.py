from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ExpectedLatency = Literal["fast", "medium", "slow"]


@dataclass(frozen=True)
class ToolConfig:
    """Bir tool'un davranışını tanımlayan metadata (V2 dokümanı bölüm 11).

    `expected_latency`/`interim_message`, Faz 3'teki InterimResponseManager
    tarafından "bu tool uzun sürerse hangi ara mesaj söylenmeli" kararı için
    kullanılacak.
    """

    name: str
    expected_latency: ExpectedLatency
    interim_message: str
