from __future__ import annotations

from livekit.plugins import google

from ..config import Settings


def build_tts(settings: Settings) -> google.beta.GeminiTTS:
    """Gemini TTS ile Türkçe metni sese çeviren TTS örneği.

    Dil parametresi bilerek verilmiyor: Gemini TTS girdi metninin dilini
    kendisi otomatik algılıyor (Türkçe dahil).
    """
    return google.beta.GeminiTTS(
        model=settings.gemini_tts_model,
        voice_name="Kore",
        instructions="Doğal, sıcak ve anlaşılır bir tonda, normal konuşma hızında seslendir.",
    )
