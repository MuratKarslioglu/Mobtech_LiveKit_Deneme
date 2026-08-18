from __future__ import annotations

# Kelime tabanlı, sabit boyutlu kaydırmalı pencere: cümle/paragraf sınırı
# aramadan basit ve deterministik. Örtüşme (overlap), bir cümlenin tam
# ortadan bölünüp bağlamının iki parçaya dağılmasını azaltır.
CHUNK_SIZE_WORDS = 220
CHUNK_OVERLAP_WORDS = 40


def chunk_text(
    text: str,
    *,
    chunk_size_words: int = CHUNK_SIZE_WORDS,
    overlap_words: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
    """Metni, aralarında `overlap_words` kelime örtüşen `chunk_size_words`
    kelimelik parçalara böler. Boş/whitespace-only metin için boş liste döner."""
    words = text.split()
    if not words:
        return []

    step = chunk_size_words - overlap_words
    chunks: list[str] = []
    start = 0
    while start < len(words):
        chunk_words = words[start : start + chunk_size_words]
        chunks.append(" ".join(chunk_words))
        if start + chunk_size_words >= len(words):
            break
        start += step
    return chunks
