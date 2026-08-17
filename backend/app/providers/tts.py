from __future__ import annotations

from livekit.plugins import openai

from ..config import Settings


def build_tts(settings: Settings) -> openai.TTS:
    """Azure OpenAI (Azure AI Foundry) üzerindeki TTS deployment'ına
    bağlanan TTS örneği."""
    return openai.TTS.with_azure(
        # `model=`, livekit-plugins-openai'de sadece bilgilendirici değil —
        # hangi HTTP stream formatının kullanılacağını da belirliyor:
        # "tts-1"/"tts-1-hd" → klasik audio-stream, "gpt-4o-mini-tts" →
        # SSE. Deployment'ın gerçek taban modeli tts-1 ailesi olduğu
        # doğrulandığı için burada elle "tts-1" veriliyor; asıl yönlendirme
        # `azure_deployment` ile yapılıyor.
        model="tts-1",
        # "ash" (kütüphanenin varsayılanı) bu deployment'ta desteklenmiyor;
        # deployment'ın izin verdiği sesler: nova, shimmer, echo, onyx,
        # fable, alloy.
        voice="alloy",
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_tts_deployment,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
    )
