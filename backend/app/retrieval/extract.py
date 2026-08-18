from __future__ import annotations

import io

import docx
from pypdf import PdfReader

SUPPORTED_CONTENT_TYPES: dict[str, str] = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


class UnsupportedDocumentType(ValueError):
    """content_type, desteklenen belge türlerinden biri değilse fırlatılır."""


def extract_text(data: bytes, content_type: str) -> str:
    """Ham dosya baytlarından düz metin çıkarır. Desteklenen türler: PDF, TXT, DOCX."""
    kind = SUPPORTED_CONTENT_TYPES.get(content_type)
    if kind is None:
        raise UnsupportedDocumentType(f"Desteklenmeyen dosya türü: {content_type!r}")

    if kind == "txt":
        return data.decode("utf-8", errors="replace")

    if kind == "pdf":
        reader = PdfReader(io.BytesIO(data))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(pages)

    # kind == "docx"
    document = docx.Document(io.BytesIO(data))
    paragraphs = [p.text for p in document.paragraphs]
    return "\n".join(paragraphs)
