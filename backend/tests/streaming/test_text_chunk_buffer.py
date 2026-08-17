import asyncio

from app.streaming.text_chunk_buffer import TextChunkBuffer, chunk_text_stream


def test_does_not_flush_before_boundary_char():
    buf = TextChunkBuffer(min_chunk_length=10)
    assert buf.push("Mer") is None
    assert buf.push("ha") is None
    assert buf.push("ba") is None


def test_does_not_flush_at_boundary_char_below_min_length():
    buf = TextChunkBuffer(min_chunk_length=10)
    buf.push("Merhaba")
    assert buf.push("!") is None  # "Merhaba!" = 8 karakter, eşik 10


def test_flushes_once_boundary_and_min_length_both_satisfied():
    buf = TextChunkBuffer(min_chunk_length=10)
    buf.push("Merhaba")
    buf.push("!")
    result = buf.push(" Naber?")
    assert result == "Merhaba! Naber?"


def test_buffer_resets_after_flush():
    buf = TextChunkBuffer(min_chunk_length=10)
    buf.push("Merhaba!")
    buf.push(" Naber?")  # flush olur
    assert buf.push("x") is None


def test_comma_boundary_flushes_when_length_met():
    buf = TextChunkBuffer(min_chunk_length=5)
    assert buf.push("Evet,") == "Evet,"


def test_flush_returns_pending_text_regardless_of_boundary():
    buf = TextChunkBuffer(min_chunk_length=10)
    buf.push("kısa")
    assert buf.flush() == "kısa"


def test_flush_on_empty_buffer_returns_none():
    buf = TextChunkBuffer()
    assert buf.flush() is None


def test_flush_after_drain_returns_none():
    buf = TextChunkBuffer(min_chunk_length=10)
    buf.push("kısa")
    buf.flush()
    assert buf.flush() is None


def test_default_min_chunk_length_with_realistic_turkish_sentence():
    buf = TextChunkBuffer()  # varsayılan eşik: 30
    assert buf.push("Merhaba,") is None
    result = buf.push(" bugün hava çok güzel.")
    assert result == "Merhaba, bugün hava çok güzel."


async def _to_async_iter(items: list[str]):
    for item in items:
        yield item


def test_chunk_text_stream_yields_chunks_and_final_flush():
    async def scenario():
        tokens = ["Mer", "haba", "!", " Naber", "?", " son parça"]
        return [
            chunk
            async for chunk in chunk_text_stream(_to_async_iter(tokens), min_chunk_length=10)
        ]

    chunks = asyncio.run(scenario())
    assert chunks == ["Merhaba! Naber?", " son parça"]


def test_chunk_text_stream_yields_nothing_for_empty_input():
    async def scenario():
        return [chunk async for chunk in chunk_text_stream(_to_async_iter([]))]

    assert asyncio.run(scenario()) == []
