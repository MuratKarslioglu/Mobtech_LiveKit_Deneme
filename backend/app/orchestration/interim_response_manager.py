from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger("voice-agent")

DEFAULT_INTERIM_MESSAGE = "Bir saniye, düşünüyorum."


class InterimResponseManager:
    """Bir işlem `threshold_s` saniyeden uzun sürerse `speak(message)`'ı
    çağırır; `cancel()` bu süreden önce çağrılırsa hiçbir şey söylenmez.

    `speak`, LiveKit `AgentSession.say()` gibi senkron bir çağrı olacak
    şekilde tasarlandı — kendisi zaten arka planda konuşmayı zamanlıyor.
    """

    def __init__(self, *, threshold_s: float, speak: Callable[[str], None]) -> None:
        self._threshold_s = threshold_s
        self._speak = speak
        self._task: asyncio.Task[None] | None = None

    def start(self, message: str = DEFAULT_INTERIM_MESSAGE) -> None:
        """Zamanlayıcıyı (yeniden) başlatır. Zaten bekleyen bir zamanlayıcı
        varsa önce iptal edilir."""
        self.cancel()
        self._task = asyncio.create_task(self._wait_and_speak(message))

    def cancel(self) -> None:
        """Gerçek cevap hazır olduğunda çağrılır — zamanlayıcı henüz
        tetiklenmediyse sessizce iptal edilir."""
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _wait_and_speak(self, message: str) -> None:
        try:
            await asyncio.sleep(self._threshold_s)
        except asyncio.CancelledError:
            return
        try:
            self._speak(message)
        except Exception:
            logger.exception("[INTERIM] speak callback'i patladı (message=%r)", message)

    @property
    def is_pending(self) -> bool:
        return self._task is not None and not self._task.done()
