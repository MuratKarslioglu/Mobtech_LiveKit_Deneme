import asyncio

from app.retrieval.retriever import Retriever
from app.retrieval.store import VectorStore


class FakeEmbedder:
    """Gerçek Azure çağrısı yapmadan, metni basit bir bag-of-words vektörüne
    eşleyen sahte embedder. Testlerde ağ bağımlılığını ortadan kaldırır."""

    def __init__(self, dimensions: int = 8) -> None:
        self.dimensions = dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [self._vector(text) for text in texts]

    def _vector(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for word in text.lower().split():
            vector[hash(word) % self.dimensions] += 1.0
        return vector


def _make_retriever(tmp_path) -> Retriever:
    store = VectorStore(str(tmp_path / "test.db"), embedding_dimensions=8)
    return Retriever(store, FakeEmbedder(dimensions=8))


def test_ingest_marks_document_ready_and_creates_chunks(tmp_path):
    retriever = _make_retriever(tmp_path)

    document = asyncio.run(
        retriever.ingest(b"merhaba dunya bu bir test dosyasidir", filename="t.txt", content_type="text/plain")
    )

    assert document.status == "ready"
    assert document.chunk_count == 1


def test_ingest_marks_error_for_unsupported_type(tmp_path):
    retriever = _make_retriever(tmp_path)

    document = asyncio.run(retriever.ingest(b"data", filename="t.zip", content_type="application/zip"))

    assert document.status == "error"
    assert document.error_message


def test_ingest_marks_error_for_empty_content(tmp_path):
    retriever = _make_retriever(tmp_path)

    document = asyncio.run(retriever.ingest(b"   ", filename="bos.txt", content_type="text/plain"))

    assert document.status == "error"


def test_search_finds_relevant_chunk(tmp_path):
    retriever = _make_retriever(tmp_path)
    asyncio.run(
        retriever.ingest(
            b"kedi kopek balik hayvanlardir. araba tren ucak tasitlardir.",
            filename="hayvanlar.txt",
            content_type="text/plain",
        )
    )

    results = asyncio.run(retriever.search("kedi kopek", top_k=1))

    assert len(results) == 1
    assert "kedi" in results[0].text


def test_search_returns_empty_list_for_blank_query(tmp_path):
    retriever = _make_retriever(tmp_path)
    assert asyncio.run(retriever.search("   ")) == []


def test_list_and_delete(tmp_path):
    retriever = _make_retriever(tmp_path)
    document = asyncio.run(
        retriever.ingest(b"merhaba dunya", filename="t.txt", content_type="text/plain")
    )

    documents = asyncio.run(retriever.list_documents())
    assert any(d.id == document.id for d in documents)

    deleted = asyncio.run(retriever.delete(document.id))
    assert deleted is True

    documents_after = asyncio.run(retriever.list_documents())
    assert all(d.id != document.id for d in documents_after)
