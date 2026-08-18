from __future__ import annotations

import sqlite3
import struct
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import sqlite_vec


@dataclass(frozen=True)
class DocumentRecord:
    id: str
    filename: str
    content_type: str
    status: str  # "processing" | "ready" | "error"
    error_message: str | None
    chunk_count: int
    uploaded_at: float


@dataclass(frozen=True)
class SearchResult:
    document_id: str
    filename: str
    chunk_index: int
    text: str
    distance: float


def _serialize(vector: list[float]) -> bytes:
    return struct.pack(f"{len(vector)}f", *vector)


class VectorStore:
    """SQLite (+ sqlite-vec) üzerinde belge/chunk/embedding saklayan store.

    Belge API'si (yükleme) ve LiveKit agent worker'ı (arama) aynı sqlite
    dosyasını ayrı süreçlerden kullanır; WAL modu eşzamanlı okuma/yazımı
    güvenli hale getirir.
    """

    def __init__(self, db_path: str, embedding_dimensions: int) -> None:
        self._db_path = db_path
        self._dimensions = embedding_dimensions
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        con = sqlite3.connect(self._db_path)
        con.enable_load_extension(True)
        sqlite_vec.load(con)
        con.enable_load_extension(False)
        con.execute("PRAGMA journal_mode=WAL")
        return con

    def _init_schema(self) -> None:
        with self._connect() as con:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    uploaded_at REAL NOT NULL
                )
                """
            )
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS chunks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    document_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    text TEXT NOT NULL
                )
                """
            )
            con.execute(
                f"""
                CREATE VIRTUAL TABLE IF NOT EXISTS vec_chunks USING vec0(
                    chunk_id INTEGER PRIMARY KEY,
                    embedding FLOAT[{self._dimensions}]
                )
                """
            )

    def create_document(self, filename: str, content_type: str) -> DocumentRecord:
        doc_id = str(uuid.uuid4())
        uploaded_at = time.time()
        with self._connect() as con:
            con.execute(
                "INSERT INTO documents (id, filename, content_type, status, chunk_count, uploaded_at) "
                "VALUES (?, ?, ?, 'processing', 0, ?)",
                (doc_id, filename, content_type, uploaded_at),
            )
        return DocumentRecord(
            id=doc_id,
            filename=filename,
            content_type=content_type,
            status="processing",
            error_message=None,
            chunk_count=0,
            uploaded_at=uploaded_at,
        )

    def add_chunks(self, document_id: str, chunks: list[str], embeddings: list[list[float]]) -> None:
        with self._connect() as con:
            for index, (text, vector) in enumerate(zip(chunks, embeddings)):
                cursor = con.execute(
                    "INSERT INTO chunks (document_id, chunk_index, text) VALUES (?, ?, ?)",
                    (document_id, index, text),
                )
                chunk_id = cursor.lastrowid
                con.execute(
                    "INSERT INTO vec_chunks (chunk_id, embedding) VALUES (?, ?)",
                    (chunk_id, _serialize(vector)),
                )
            con.execute(
                "UPDATE documents SET status = 'ready', chunk_count = ? WHERE id = ?",
                (len(chunks), document_id),
            )

    def mark_error(self, document_id: str, message: str) -> None:
        with self._connect() as con:
            con.execute(
                "UPDATE documents SET status = 'error', error_message = ? WHERE id = ?",
                (message, document_id),
            )

    def list_documents(self) -> list[DocumentRecord]:
        with self._connect() as con:
            rows = con.execute(
                "SELECT id, filename, content_type, status, error_message, chunk_count, uploaded_at "
                "FROM documents ORDER BY uploaded_at DESC"
            ).fetchall()
        return [_row_to_document(row) for row in rows]

    def get_document(self, document_id: str) -> DocumentRecord | None:
        with self._connect() as con:
            row = con.execute(
                "SELECT id, filename, content_type, status, error_message, chunk_count, uploaded_at "
                "FROM documents WHERE id = ?",
                (document_id,),
            ).fetchone()
        return _row_to_document(row) if row is not None else None

    def delete_document(self, document_id: str) -> bool:
        with self._connect() as con:
            chunk_ids = [
                row[0]
                for row in con.execute(
                    "SELECT id FROM chunks WHERE document_id = ?", (document_id,)
                ).fetchall()
            ]
            for chunk_id in chunk_ids:
                con.execute("DELETE FROM vec_chunks WHERE chunk_id = ?", (chunk_id,))
            con.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            cursor = con.execute("DELETE FROM documents WHERE id = ?", (document_id,))
            return cursor.rowcount > 0

    def search(self, query_embedding: list[float], top_k: int) -> list[SearchResult]:
        with self._connect() as con:
            rows = con.execute(
                """
                SELECT d.id, d.filename, c.chunk_index, c.text, v.distance
                FROM vec_chunks v
                JOIN chunks c ON c.id = v.chunk_id
                JOIN documents d ON d.id = c.document_id
                WHERE v.embedding MATCH ? AND k = ?
                ORDER BY v.distance
                """,
                (_serialize(query_embedding), top_k),
            ).fetchall()
        return [
            SearchResult(
                document_id=row[0], filename=row[1], chunk_index=row[2], text=row[3], distance=row[4]
            )
            for row in rows
        ]


def _row_to_document(row: tuple) -> DocumentRecord:
    return DocumentRecord(
        id=row[0],
        filename=row[1],
        content_type=row[2],
        status=row[3],
        error_message=row[4],
        chunk_count=row[5],
        uploaded_at=row[6],
    )
