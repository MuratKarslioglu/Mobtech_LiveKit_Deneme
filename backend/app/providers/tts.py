from __future__ import annotations

from livekit.plugins import openai

from ..config import Settings


def build_tts(settings: Settings) -> openai.TTS:
    """Azure OpenAI (Azure AI Foundry) üzerindeki TTS deployment'ına
    bağlanan TTS örneği."""
    return openai.TTS.with_azure(
        # `model=` burada sadece bilgi amaçlı değil, HTTP stream formatını da
        # belirliyor (tts-1 ailesi → audio-stream); asıl yönlendirme
        # `azure_deployment` ile yapılıyor.
        model="tts-1",
        # "ash" (kütüphane varsayılanı) bu deployment'ta desteklenmiyor;
        # izin verilen sesler: nova, shimmer, echo, onyx, fable, alloy.
        voice="alloy",
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_tts_deployment,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
    )
