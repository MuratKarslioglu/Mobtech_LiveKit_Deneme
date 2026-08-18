"""Azure OpenAI LLM provider'ının kurulum/wiring'ini doğrulayan smoke test'ler.
Gerçek bir Azure bağlantısı açmaz.
"""

from dataclasses import replace

from app.config import Settings
from app.providers.llm import build_llm


def _settings(**overrides) -> Settings:
    base = Settings(
        livekit_url="wss://example.livekit.cloud",
        livekit_api_key="key",
        livekit_api_secret="secret",
        azure_openai_endpoint="https://example.services.ai.azure.com",
        azure_openai_api_key="fake-key",
        azure_openai_api_version="2024-08-01-preview",
        azure_openai_llm_deployment="gpt-5-mini",
        azure_openai_stt_deployment="gpt-4o-mini-transcribe",
        azure_openai_tts_deployment="tts",
        azure_openai_embedding_deployment="text-embedding-3-small",
        azure_openai_embedding_dimensions=1536,
        documents_dir="data/uploads",
        documents_db_path="data/documents.db",
        frontend_origin="http://localhost:3000",
        interim_response_threshold_ms=1000,
        app_language="tr",
        log_level="INFO",
    )
    return replace(base, **overrides)


def test_build_llm_uses_configured_deployment():
    result = build_llm(_settings())
    assert result.model == "gpt-5-mini"
