from app.retrieval.chunking import chunk_text


def test_chunk_text_returns_empty_list_for_blank_text():
    assert chunk_text("   \n  ") == []


def test_chunk_text_returns_single_chunk_for_short_text():
    text = "kısa bir test metni"
    chunks = chunk_text(text, chunk_size_words=10, overlap_words=2)
    assert chunks == [text]


def test_chunk_text_splits_with_overlap():
    words = [f"kelime{i}" for i in range(25)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size_words=10, overlap_words=3)

    assert len(chunks) == 4
    # Her chunk en fazla 10 kelime içerir.
    assert all(len(chunk.split()) <= 10 for chunk in chunks)
    # İkinci chunk, ilkinin son 3 kelimesiyle başlar (overlap).
    assert chunks[0].split()[-3:] == chunks[1].split()[:3]


def test_chunk_text_covers_all_words():
    words = [f"w{i}" for i in range(50)]
    text = " ".join(words)

    chunks = chunk_text(text, chunk_size_words=20, overlap_words=5)

    covered = set()
    for chunk in chunks:
        covered.update(chunk.split())
    assert covered == set(words)
