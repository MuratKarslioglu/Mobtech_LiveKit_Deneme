from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


class ConfigError(RuntimeError):
    """Zorunlu bir ortam değişkeni eksik ya da boş olduğunda fırlatılır."""


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise ConfigError(
            f"Zorunlu ortam değişkeni eksik: {name}. "
            f".env dosyanı kontrol et (örnek için .env.example'a bak)."
        )
    return value


def _optional(name: str, default: str) -> str:
    return os.getenv(name, default).strip() or default


def _optional_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(
            f"Ortam değişkeni {name} bir tam sayı olmalı, alınan değer: {raw!r}."
        ) from exc


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str

    # Tek Azure OpenAI kaynağı, dört ayrı deployment (chat/STT/TTS/embedding), aynı endpoint/key.
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_llm_deployment: str
    azure_openai_stt_deployment: str
    azure_openai_tts_deployment: str
    azure_openai_embedding_deployment: str
    azure_openai_embedding_dimensions: int

    interim_response_threshold_ms: int

    # Belge retriever'ı (SQLite + sqlite-vec) ve yüklenen dosyalar için yol.
    documents_dir: str
    documents_db_path: str
    # Belge API'sinin (app/api.py) CORS için izin verdiği frontend origin'i.
    frontend_origin: str

    app_language: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        livekit_url=_require("LIVEKIT_URL"),
        livekit_api_key=_require("LIVEKIT_API_KEY"),
        livekit_api_secret=_require("LIVEKIT_API_SECRET"),
        azure_openai_endpoint=_require("AZURE_OPENAI_ENDPOINT"),
        azure_openai_api_key=_require("AZURE_OPENAI_API_KEY"),
        azure_openai_llm_deployment=_require("AZURE_OPENAI_LLM_DEPLOYMENT"),
        azure_openai_stt_deployment=_require("AZURE_OPENAI_STT_DEPLOYMENT"),
        azure_openai_tts_deployment=_require("AZURE_OPENAI_TTS_DEPLOYMENT"),
        azure_openai_embedding_deployment=_require("AZURE_OPENAI_EMBEDDING_DEPLOYMENT"),
        # text-embedding-3-small/large boyutu; Azure'daki deployment'a göre
        # değişebileceğinden env üzerinden ezilebilir bırakıldı.
        azure_openai_embedding_dimensions=_optional_int("AZURE_OPENAI_EMBEDDING_DIMENSIONS", 1536),
        azure_openai_api_version=_optional("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        documents_dir=_optional("DOCUMENTS_DIR", "data/uploads"),
        documents_db_path=_optional("DOCUMENTS_DB_PATH", "data/documents.db"),
        frontend_origin=_optional("FRONTEND_ORIGIN", "http://localhost:3000"),
        # Bir tool/LLM işlemi bu süreden (ms) uzun sürerse ara mesaj söylenir.
        # LiveKit'in `session.say()` çağrısı interim mesajı ve asıl cevabı aynı
        # FIFO kuyrukta sıralıyor (öncelik parametresi yok), bu yüzden eşik
        # tipik LLM TTFT'sinin (~1.2-1.5sn) belirgin üstünde tutuluyor — normal
        # turlarda hiç tetiklenmesin diye.
        interim_response_threshold_ms=_optional_int("INTERIM_RESPONSE_THRESHOLD_MS", 2500),
        app_language=_optional("APP_LANGUAGE", "tr"),
        log_level=_optional("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
