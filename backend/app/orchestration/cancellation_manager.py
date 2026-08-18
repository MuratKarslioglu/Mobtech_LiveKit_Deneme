from __future__ import annotations

import asyncio
from typing import Any


class CancellationManager:
    """Aktif görevlerin `asyncio.Task` referanslarını tutar; barge-in anında
    hepsini iptal eder. LiveKit'in `AgentSession`'ı LLM/TTS generation
    task'larını hâlâ kendi içinde yönettiği için burada izlenen gerçek bir
    task yok — `cancel_all()` bugün güvenli bir no-op'tur.
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
