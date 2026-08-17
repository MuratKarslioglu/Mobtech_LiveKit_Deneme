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


@dataclass(frozen=True)
class Settings:
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str

    google_api_key: str
    gemini_llm_model: str
    gemini_tts_model: str

    whisper_model: str
    whisper_device: str

    app_language: str
    log_level: str


def load_settings() -> Settings:
    return Settings(
        livekit_url=_require("LIVEKIT_URL"),
        livekit_api_key=_require("LIVEKIT_API_KEY"),
        livekit_api_secret=_require("LIVEKIT_API_SECRET"),
        google_api_key=_require("GOOGLE_API_KEY"),
        gemini_llm_model=_optional("GEMINI_LLM_MODEL", "gemini-3.5-flash"),
        gemini_tts_model=_optional("GEMINI_TTS_MODEL", "gemini-2.5-flash-preview-tts"),
        whisper_model=_optional("WHISPER_MODEL", "large-v3-turbo"),
        whisper_device=_optional("WHISPER_DEVICE", "auto"),
        app_language=_optional("APP_LANGUAGE", "tr"),
        log_level=_optional("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
