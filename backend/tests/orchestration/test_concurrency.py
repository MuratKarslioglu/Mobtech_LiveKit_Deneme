"""Eşzamanlı/art arda tur senaryolarını doğrulayan testler (V2 dokümanı
bölüm 23, Senaryo E: art arda hızlı konuşma turları)."""

import asyncio

from app.orchestration.cancellation_manager import CancellationManager
from app.orchestration.interim_response_manager import InterimResponseManager
from app.orchestration.response_orchestrator import ResponseOrchestrator

THRESHOLD_S = 0.03
WAIT_S = 0.15


def test_rapid_overlapping_turns_do_not_crash_or_leak_timers():
    async def scenario():
        spoken: list[str] = []
        orchestrator = ResponseOrchestrator(
            interim_manager=InterimResponseManager(threshold_s=THRESHOLD_S, speak=spoken.append),
            cancellation_manager=CancellationManager(),
        )

        async def simulate_turn(tool_name: str | None) -> None:
            orchestrator.start_turn()
            if tool_name:
                orchestrator.execute_tool(tool_name)
            else:
                orchestrator.start_interim_timer()
            await asyncio.sleep(0.01)
            orchestrator.process_request()
            orchestrator.finish_turn()

        # Art arda 5 tur, hiçbiri birbirini beklemeden (gerçek kullanıcının
        # hızlı hızlı konuşması senaryosu).
        await asyncio.gather(
            *(
                simulate_turn(name)
                for name in [None, "add_numbers", None, "add_numbers", None]
            )
        )

        # Hiçbir turun interim mesajı sızdırmadığını doğrula — hepsi
        # process_request ile zamanında iptal edildi.
        await asyncio.sleep(WAIT_S)
        assert spoken == []

    asyncio.run(scenario())


def test_barge_in_during_pending_interim_timer_cancels_cleanly():
    async def scenario():
        spoken: list[str] = []
        cancellation_manager = CancellationManager()
        orchestrator = ResponseOrchestrator(
            interim_manager=InterimResponseManager(threshold_s=THRESHOLD_S, speak=spoken.append),
            cancellation_manager=cancellation_manager,
        )

        async def never_ending() -> None:
            await asyncio.sleep(10)

        orchestrator.start_turn()
        orchestrator.start_interim_timer()
        cancellation_manager.track("tts", asyncio.create_task(never_ending()))

        # Barge-in, interim zamanlayıcı henüz tetiklenmeden hemen önce oluyor.
        await asyncio.sleep(THRESHOLD_S / 2)
        orchestrator.cancel_current_response()

        await asyncio.sleep(WAIT_S)
        assert spoken == []
        assert cancellation_manager.active_names == []

    asyncio.run(scenario())
