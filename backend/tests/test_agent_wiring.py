"""Agent modülünün ve provider fabrikalarının hatasız kurulabildiğini doğrulayan
minimum "smoke test"ler. Gerçek bir LiveKit/Gemini bağlantısı açmaz; sadece
importların ve nesne kurulumunun (wiring) bozulmadığını kontrol eder.
"""

from livekit.plugins import silero

from app.agent import entrypoint, server
from app.config import settings
from app.providers.llm import build_llm
from app.providers.tts import build_tts


def test_agent_server_is_defined():
    assert server is not None
    assert callable(entrypoint)


def test_build_llm_uses_configured_model():
    llm = build_llm(settings)
    assert llm.model == settings.gemini_llm_model


def test_build_tts_uses_configured_model():
    tts = build_tts(settings)
    assert tts.model == settings.gemini_tts_model


def test_silero_vad_plugin_importable():
    # Modelin kendisini indirip yüklemeden, plugin'in en azından doğru
    # şekilde import edildiğini doğruluyoruz.
    assert hasattr(silero, "VAD")
