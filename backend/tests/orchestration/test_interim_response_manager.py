import asyncio

from app.orchestration.interim_response_manager import (
    DEFAULT_INTERIM_MESSAGE,
    InterimResponseManager,
)

THRESHOLD_S = 0.03
WAIT_S = 0.15


def _manager(threshold_s: float = THRESHOLD_S) -> tuple[InterimResponseManager, list[str]]:
    spoken: list[str] = []
    manager = InterimResponseManager(threshold_s=threshold_s, speak=spoken.append)
    return manager, spoken


def test_speaks_after_threshold_elapses():
    async def scenario():
        manager, spoken = _manager()
        manager.start("test mesajı")
        await asyncio.sleep(WAIT_S)
        assert spoken == ["test mesajı"]

    asyncio.run(scenario())


def test_cancel_before_threshold_prevents_speak():
    async def scenario():
        manager, spoken = _manager()
        manager.start("test mesajı")
        manager.cancel()
        await asyncio.sleep(WAIT_S)
        assert spoken == []

    asyncio.run(scenario())


def test_default_message_used_when_none_given():
    async def scenario():
        manager, spoken = _manager()
        manager.start()
        await asyncio.sleep(WAIT_S)
        assert spoken == [DEFAULT_INTERIM_MESSAGE]

    asyncio.run(scenario())


def test_is_pending_reflects_timer_state():
    async def scenario():
        manager, _ = _manager()
        assert manager.is_pending is False

        manager.start()
        assert manager.is_pending is True

        manager.cancel()
        assert manager.is_pending is False

    asyncio.run(scenario())


def test_starting_again_replaces_previous_timer():
    async def scenario():
        manager, spoken = _manager()
        manager.start("ilk mesaj")
        manager.start("ikinci mesaj")
        await asyncio.sleep(WAIT_S)
        assert spoken == ["ikinci mesaj"]

    asyncio.run(scenario())


def test_cancel_without_a_pending_timer_is_a_no_op():
    manager, spoken = _manager()
    manager.cancel()
    assert spoken == []
    assert manager.is_pending is False
