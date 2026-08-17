from __future__ import annotations

from collections.abc import AsyncIterable, AsyncIterator

_BOUNDARY_CHARS = frozenset(".!?,;")
DEFAULT_MIN_CHUNK_LENGTH = 30


class TextChunkBuffer:
    """LLM'den parça parça (token/delta) gelen metni, TTS'e göndermeye uygun
    doğal cümle/phrase parçalarına böler (bkz. V2 dokümanı bölüm 6).

    Parçalar tek tek TTS'e gönderilmez ("Mer", "ha", "ba" gibi) — bunun yerine
    bir noktalama sınırına ulaşılana VE birikmiş metin `min_chunk_length`'i
    aşana kadar buffer'lanır, ikisi de sağlanınca tek parça halinde flush edilir.
    """

    def __init__(self, *, min_chunk_length: int = DEFAULT_MIN_CHUNK_LENGTH) -> None:
        self._min_chunk_length = min_chunk_length
        self._buffer = ""

    def push(self, token: str) -> str | None:
        """Yeni bir metin parçası ekler; flush edilecek bir chunk oluştuysa
        onu döndürür, oluşmadıysa `None` döner."""
        self._buffer += token

        stripped = self._buffer.strip()
        if not stripped:
            return None

        if stripped[-1] in _BOUNDARY_CHARS and len(stripped) >= self._min_chunk_length:
            return self._drain()

        return None

    def flush(self) -> str | None:
        """Stream bittiğinde bekleyen her şeyi (boyut/noktalama şartı
        aranmadan) döndürür; buffer boşsa `None` döner."""
        if not self._buffer.strip():
            self._buffer = ""
            return None
        return self._drain()

    def _drain(self) -> str:
        chunk = self._buffer
        self._buffer = ""
        return chunk


async def chunk_text_stream(
    text: AsyncIterable[str], *, min_chunk_length: int = DEFAULT_MIN_CHUNK_LENGTH
) -> AsyncIterator[str]:
    """Bir `Agent.tts_node` override'ında kullanılmak üzere: gelen token
    stream'ini `TextChunkBuffer` üzerinden geçirip TTS'e uygun parçalar
    halinde yeniden yayınlar."""
    buffer = TextChunkBuffer(min_chunk_length=min_chunk_length)
    async for token in text:
        chunk = buffer.push(token)
        if chunk is not None:
            yield chunk

    tail = buffer.flush()
    if tail is not None:
        yield tail
