from __future__ import annotations

import asyncio
from typing import Any


class CancellationManager:
    """Aktif LLM generation / TTS playback / tool execution görevlerinin
    `asyncio.Task` referanslarını tutar; barge-in anında hepsini güvenli
    şekilde iptal eder (bkz. V2 dokümanı bölüm 8 ve 13).

    `ResponseOrchestrator` üzerinden `agent.py`'ye bağlı (`user_state_changed`
    → `cancel_current_response`); ancak LiveKit'in `AgentSession`'ı LLM/TTS
    generation task'larını hâlâ kendi içinde yönettiği için burada izlenen
    gerçek bir task yok — `cancel_all()` bugün güvenli bir no-op'tur (interim
    zamanlayıcı zaten `ResponseOrchestrator` tarafından ayrıca iptal ediliyor).
    `Agent.llm_node` kendi generation task'larını oluşturup `track()` ile
    kaydettiğinde gerçek LLM/TTS cancellation da buradan yönetilecek.
    """

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[Any]] = {}

    def track(self, name: str, task: asyncio.Task[Any]) -> None:
        self._tasks[name] = task

    def untrack(self, name: str) -> None:
        self._tasks.pop(name, None)

    def cancel_all(self) -> None:
        for task in self._tasks.values():
            if not task.done():
                task.cancel()
        self._tasks.clear()

    @property
    def active_names(self) -> list[str]:
        return [name for name, task in self._tasks.items() if not task.done()]
