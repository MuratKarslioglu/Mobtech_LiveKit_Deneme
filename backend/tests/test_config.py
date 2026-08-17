import pytest

from app.config import ConfigError, load_settings


def _set_required_env(monkeypatch):
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.services.ai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "key")
    monkeypatch.setenv("AZURE_OPENAI_LLM_DEPLOYMENT", "gpt-5-mini")
    monkeypatch.setenv("AZURE_OPENAI_STT_DEPLOYMENT", "gpt-4o-mini-transcribe")
    monkeypatch.setenv("AZURE_OPENAI_TTS_DEPLOYMENT", "tts")


def test_load_settings_raises_when_required_var_missing(monkeypatch):
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    _set_required_env(monkeypatch)

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_succeeds_with_required_vars(monkeypatch):
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    _set_required_env(monkeypatch)
    monkeypatch.delenv("AZURE_OPENAI_API_VERSION", raising=False)

    settings = load_settings()

    assert settings.livekit_url == "wss://example.livekit.cloud"
    assert settings.azure_openai_api_version == "2024-08-01-preview"  # varsayılan değer
    assert settings.app_language == "tr"  # varsayılan değer


def test_load_settings_raises_config_error_on_invalid_int(monkeypatch):
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    _set_required_env(monkeypatch)
    monkeypatch.setenv("INTERIM_RESPONSE_THRESHOLD_MS", "not-a-number")

    with pytest.raises(ConfigError):
        load_settings()
