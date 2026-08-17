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

    # Tek bir Azure OpenAI/Azure AI Foundry kaynağı, üç ayrı deployment:
    # chat (LLM), transcribe (STT) ve TTS. Aynı endpoint/key'i paylaşırlar.
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_llm_deployment: str
    azure_openai_stt_deployment: str
    azure_openai_tts_deployment: str

    interim_response_threshold_ms: int

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
        azure_openai_api_version=_optional("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"),
        # Bir tool/LLM işlemi bu süreden (ms) uzun sürerse kullanıcıya bir ara
        # mesaj söylenir (bkz. InterimResponseManager, V2 dokümanı bölüm 9.2).
        #
        # ÖNEMLİ: LiveKit'in AgentSession'ı, `session.say()` ile tetiklenen
        # interim mesajını ve asıl LLM cevabını AYNI önceliğe (SPEECH_PRIORITY_
        # NORMAL) sahip tek bir FIFO kuyrukta sıralıyor; asıl cevabın
        # SpeechHandle'ı, kullanıcının turu onaylandığı anda (LLM ilk token'ı
        # üretmeden ÖNCE) bu kuyruğa zaten giriyor. Yani interim mesajı ne
        # zaman tetiklenirse tetiklensin, kuyrukta asıl cevabın HER ZAMAN
        # arkasına düşer — "düşünüyorum" mesajının cevaptan sonra çalması bir
        # timing hatası değil, LiveKit SDK'sının genel `say()` API'sinin bir
        # sınırlaması (öncelik parametresi dışarı açılmıyor). Bu yüzden eşik,
        # bu deployment'ın tipik LLM TTFT'sinin (~1.2-1.5sn, bkz. providers/
        # llm.py) BELİRGİN ÜSTÜNDE tutuluyor — normal turlarda hiç
        # tetiklenmesin, yalnızca gerçekten anormal/yavaş durumlarda (örn.
        # yavaş bir tool çağrısı) devreye girsin diye.
        interim_response_threshold_ms=_optional_int("INTERIM_RESPONSE_THRESHOLD_MS", 2500),
        app_language=_optional("APP_LANGUAGE", "tr"),
        log_level=_optional("LOG_LEVEL", "INFO"),
    )


settings = load_settings()
