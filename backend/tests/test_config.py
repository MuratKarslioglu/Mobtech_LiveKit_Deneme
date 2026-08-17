import pytest

from app.config import ConfigError, load_settings


def test_load_settings_raises_when_required_var_missing(monkeypatch):
    monkeypatch.delenv("LIVEKIT_URL", raising=False)
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_API_KEY", "key")

    with pytest.raises(ConfigError):
        load_settings()


def test_load_settings_succeeds_with_required_vars(monkeypatch):
    monkeypatch.setenv("LIVEKIT_URL", "wss://example.livekit.cloud")
    monkeypatch.setenv("LIVEKIT_API_KEY", "key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "secret")
    monkeypatch.setenv("GOOGLE_API_KEY", "key")
    monkeypatch.delenv("WHISPER_MODEL", raising=False)

    settings = load_settings()

    assert settings.livekit_url == "wss://example.livekit.cloud"
    assert settings.whisper_model == "large-v3-turbo"  # varsayılan değer
    assert settings.app_language == "tr"  # varsayılan değer
