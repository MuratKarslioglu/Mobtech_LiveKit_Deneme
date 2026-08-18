"""Belge yükleme/listeleme/silme API'si.

LiveKit agent worker'ından (`app/agent.py`) ayrı bir süreç olarak çalışır:

    uvicorn app.api:app --port 8000 --reload

Frontend, bu servise doğrudan değil `frontend/app/api/documents` proxy
route'ları üzerinden erişir (bkz. o dosyalardaki not).
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .retrieval.extract import SUPPORTED_CONTENT_TYPES
from .retrieval.retriever import get_retriever
from .retrieval.store import DocumentRecord

logger = logging.getLogger("voice-agent.documents-api")

app = FastAPI(title="Belge API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _serialize(document: DocumentRecord) -> dict:
    return {
        "id": document.id,
        "filename": document.filename,
        "content_type": document.content_type,
        "status": document.status,
        "error_message": document.error_message,
        "chunk_count": document.chunk_count,
        "uploaded_at": document.uploaded_at,
    }


@app.get("/documents")
async def list_documents() -> dict:
    retriever = get_retriever(settings)
    documents = await retriever.list_documents()
    return {"documents": [_serialize(doc) for doc in documents]}


@app.post("/documents", status_code=201)
async def upload_document(file: UploadFile = File(...)) -> dict:
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Desteklenmeyen dosya türü: {file.content_type}. "
            f"Desteklenenler: PDF, TXT, DOCX.",
        )

    data = await file.read()
    retriever = get_retriever(settings)
    document = await retriever.ingest(data, filename=file.filename or "belge", content_type=file.content_type)
    logger.info("[DOCUMENTS] yüklendi: %s status=%s", document.filename, document.status)
    return _serialize(document)


@app.delete("/documents/{document_id}", status_code=204)
async def delete_document(document_id: str) -> None:
    retriever = get_retriever(settings)
    deleted = await retriever.delete(document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Belge bulunamadı.")
