import asyncio

from app.orchestration.cancellation_manager import CancellationManager


async def _never_ending() -> None:
    await asyncio.sleep(10)


def test_cancel_all_cancels_tracked_tasks():
    async def scenario():
        manager = CancellationManager()
        task = asyncio.create_task(_never_ending())
        manager.track("llm", task)

        manager.cancel_all()
        try:
            await task
        except asyncio.CancelledError:
            pass

        assert task.cancelled()
        assert manager.active_names == []

    asyncio.run(scenario())


def test_cancel_all_is_a_no_op_when_nothing_tracked():
    manager = CancellationManager()
    manager.cancel_all()
    assert manager.active_names == []


def test_untrack_removes_task_without_cancelling_it():
    async def scenario():
        manager = CancellationManager()
        task = asyncio.create_task(_never_ending())
        manager.track("tts", task)
        manager.untrack("tts")

        assert manager.active_names == []
        assert not task.cancelled()

        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    asyncio.run(scenario())


def test_active_names_excludes_completed_tasks():
    async def scenario():
        manager = CancellationManager()

        async def quick() -> None:
            return None

        task = asyncio.create_task(quick())
        manager.track("quick", task)
        await task

        assert manager.active_names == []

    asyncio.run(scenario())
