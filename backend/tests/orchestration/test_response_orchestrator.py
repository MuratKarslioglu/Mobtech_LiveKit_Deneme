import asyncio

from app.orchestration.cancellation_manager import CancellationManager
from app.orchestration.interim_response_manager import (
    DEFAULT_INTERIM_MESSAGE,
    InterimResponseManager,
)
from app.orchestration.response_orchestrator import ResponseOrchestrator
from app.tools.registry import all_tools

THRESHOLD_S = 0.03
WAIT_S = 0.15


def _orchestrator(threshold_s: float = THRESHOLD_S):
    spoken: list[str] = []
    cancellation_manager = CancellationManager()
    orchestrator = ResponseOrchestrator(
        interim_manager=InterimResponseManager(threshold_s=threshold_s, speak=spoken.append),
        cancellation_manager=cancellation_manager,
    )
    return orchestrator, spoken, cancellation_manager


def test_start_turn_marks_turn_active():
    orchestrator, _, _ = _orchestrator()
    assert orchestrator.turn_active is False

    orchestrator.start_turn()
    assert orchestrator.turn_active is True


def test_execute_tool_uses_registered_interim_message():
    async def scenario():
        all_tools()  # tool modüllerini (add_numbers dahil) registry'ye kaydettirir
        orchestrator, spoken, _ = _orchestrator()

        orchestrator.execute_tool("add_numbers")
        await asyncio.sleep(WAIT_S)

        assert spoken == ["Hesaplamayı yapıyorum."]

    asyncio.run(scenario())


def test_execute_tool_falls_back_to_default_message_for_unknown_tool():
    async def scenario():
        orchestrator, spoken, _ = _orchestrator()

        orchestrator.execute_tool("does_not_exist")
        await asyncio.sleep(WAIT_S)

        assert spoken == [DEFAULT_INTERIM_MESSAGE]

    asyncio.run(scenario())


def test_process_request_cancels_pending_interim_timer():
    async def scenario():
        orchestrator, spoken, _ = _orchestrator()

        orchestrator.start_interim_timer()
        orchestrator.process_request()
        await asyncio.sleep(WAIT_S)

        assert spoken == []

    asyncio.run(scenario())


def test_cancel_current_response_cancels_interim_timer_and_tracked_tasks():
    async def scenario():
        orchestrator, spoken, cancellation_manager = _orchestrator()
        orchestrator.start_interim_timer()

        async def never_ending() -> None:
            await asyncio.sleep(10)

        task = asyncio.create_task(never_ending())
        cancellation_manager.track("tts", task)

        orchestrator.cancel_current_response()
        try:
            await task
        except asyncio.CancelledError:
            pass
        await asyncio.sleep(WAIT_S)

        assert spoken == []
        assert task.cancelled()

    asyncio.run(scenario())


def test_finish_turn_resets_turn_active_and_cancels_pending_timer():
    async def scenario():
        orchestrator, spoken, _ = _orchestrator()
        orchestrator.start_turn()
        orchestrator.start_interim_timer()

        orchestrator.finish_turn()

        assert orchestrator.turn_active is False
        await asyncio.sleep(WAIT_S)
        assert spoken == []

    asyncio.run(scenario())
