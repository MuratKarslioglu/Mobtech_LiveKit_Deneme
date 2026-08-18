from app.retrieval.store import VectorStore


def _make_store(tmp_path):
    return VectorStore(str(tmp_path / "test.db"), embedding_dimensions=4)


def test_create_document_starts_in_processing_state(tmp_path):
    store = _make_store(tmp_path)
    document = store.create_document("dosya.txt", "text/plain")
    assert document.status == "processing"
    assert document.chunk_count == 0


def test_add_chunks_marks_document_ready(tmp_path):
    store = _make_store(tmp_path)
    document = store.create_document("dosya.txt", "text/plain")

    store.add_chunks(document.id, ["parça bir", "parça iki"], [[1, 0, 0, 0], [0, 1, 0, 0]])

    refreshed = store.get_document(document.id)
    assert refreshed.status == "ready"
    assert refreshed.chunk_count == 2


def test_mark_error_sets_status_and_message(tmp_path):
    store = _make_store(tmp_path)
    document = store.create_document("dosya.txt", "text/plain")

    store.mark_error(document.id, "ayrıştırma hatası")

    refreshed = store.get_document(document.id)
    assert refreshed.status == "error"
    assert refreshed.error_message == "ayrıştırma hatası"


def test_search_returns_closest_chunk_first(tmp_path):
    store = _make_store(tmp_path)
    document = store.create_document("dosya.txt", "text/plain")
    store.add_chunks(
        document.id,
        ["elma", "muz", "araba"],
        [[1, 0, 0, 0], [0.9, 0.1, 0, 0], [0, 0, 1, 0]],
    )

    results = store.search([1, 0, 0, 0], top_k=2)

    assert [r.text for r in results] == ["elma", "muz"]


def test_delete_document_removes_document_and_chunks(tmp_path):
    store = _make_store(tmp_path)
    document = store.create_document("dosya.txt", "text/plain")
    store.add_chunks(document.id, ["parça"], [[1, 0, 0, 0]])

    assert store.delete_document(document.id) is True
    assert store.get_document(document.id) is None
    assert store.search([1, 0, 0, 0], top_k=5) == []


def test_delete_document_returns_false_for_unknown_id(tmp_path):
    store = _make_store(tmp_path)
    assert store.delete_document("does-not-exist") is False


def test_list_documents_orders_newest_first(tmp_path):
    store = _make_store(tmp_path)
    first = store.create_document("ilk.txt", "text/plain")
    second = store.create_document("ikinci.txt", "text/plain")

    documents = store.list_documents()

    assert [d.id for d in documents] == [second.id, first.id]
