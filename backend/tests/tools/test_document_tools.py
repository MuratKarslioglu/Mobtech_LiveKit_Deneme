import asyncio
from unittest.mock import AsyncMock

from app.retrieval.store import SearchResult
from app.tools import document_tools


def test_search_documents_is_registered_as_function_tool():
    assert document_tools.search_documents.info.name == "search_documents"
    assert document_tools.search_documents.info.description


def test_search_documents_returns_message_when_no_results(monkeypatch):
    fake_retriever = AsyncMock()
    fake_retriever.search.return_value = []
    monkeypatch.setattr(document_tools, "get_retriever", lambda settings: fake_retriever)

    result = asyncio.run(document_tools.search_documents(query="test"))

    assert "bulunamadı" in result


def test_search_documents_formats_results(monkeypatch):
    fake_retriever = AsyncMock()
    fake_retriever.search.return_value = [
        SearchResult(
            document_id="1", filename="rapor.pdf", chunk_index=0, text="önemli bilgi", distance=0.1
        )
    ]
    monkeypatch.setattr(document_tools, "get_retriever", lambda settings: fake_retriever)

    result = asyncio.run(document_tools.search_documents(query="test"))

    assert "rapor.pdf" in result
    assert "önemli bilgi" in result
