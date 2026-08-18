from __future__ import annotations

import asyncio
import logging
from functools import lru_cache

from ..config import Settings
from .chunking import chunk_text
from .embeddings import Embedder
from .extract import UnsupportedDocumentType, extract_text
from .store import DocumentRecord, SearchResult, VectorStore

logger = logging.getLogger("voice-agent.retriever")

DEFAULT_TOP_K = 5


class Retriever:
    """Belge yükleme (ayrıştır -> parçala -> embed'le -> sakla) ve arama
    (embed'le -> en yakın komşuları getir) akışlarını birleştiren üst katman.

    Store'a erişim senkron (sqlite3) olduğundan, event loop'u bloklamamak
    için `asyncio.to_thread` ile ayrı thread'e devrediliyor.
    """

    def __init__(self, store: VectorStore, embedder: Embedder) -> None:
        self._store = store
        self._embedder = embedder

    async def ingest(self, data: bytes, *, filename: str, content_type: str) -> DocumentRecord:
        document = await asyncio.to_thread(self._store.create_document, filename, content_type)
        try:
            text = extract_text(data, content_type)
            chunks = chunk_text(text)
            if not chunks:
                await asyncio.to_thread(
                    self._store.mark_error, document.id, "Belge içeriği boş görünüyor."
                )
                return await asyncio.to_thread(self._store.get_document, document.id)  # type: ignore[return-value]

            embeddings = await self._embedder.embed(chunks)
            await asyncio.to_thread(self._store.add_chunks, document.id, chunks, embeddings)
        except UnsupportedDocumentType as exc:
            await asyncio.to_thread(self._store.mark_error, document.id, str(exc))
        except Exception as exc:  # noqa: BLE001 - hata durumunu kullanıcıya döndürüyoruz
            logger.exception("[RETRIEVER] Belge işlenemedi: %s", filename)
            await asyncio.to_thread(self._store.mark_error, document.id, str(exc))

        refreshed = await asyncio.to_thread(self._store.get_document, document.id)
        return refreshed if refreshed is not None else document

    async def search(self, query: str, top_k: int = DEFAULT_TOP_K) -> list[SearchResult]:
        if not query.strip():
            return []
        embeddings = await self._embedder.embed([query])
        return await asyncio.to_thread(self._store.search, embeddings[0], top_k)

    async def list_documents(self) -> list[DocumentRecord]:
        return await asyncio.to_thread(self._store.list_documents)

    async def delete(self, document_id: str) -> bool:
        return await asyncio.to_thread(self._store.delete_document, document_id)


@lru_cache(maxsize=1)
def get_retriever(settings: Settings) -> Retriever:
    """Süreç başına tek bir `Retriever` (ve dolayısıyla tek bir sqlite
    bağlantı havuzu / embedding client'ı) — hem belge API'si hem de agent
    worker'ı bu fonksiyonu çağırır."""
    store = VectorStore(settings.documents_db_path, settings.azure_openai_embedding_dimensions)
    embedder = Embedder(settings)
    return Retriever(store, embedder)
