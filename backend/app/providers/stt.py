from __future__ import annotations

from livekit.plugins import openai

from ..config import Settings


def build_stt(settings: Settings) -> openai.STT:
    """Azure OpenAI (Azure AI Foundry) üzerindeki bir transcribe deployment'ına
    (örn. "gpt-4o-mini-transcribe") bağlanan STT örneği."""
    return openai.STT.with_azure(
        language=settings.app_language,
        model=settings.azure_openai_stt_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_stt_deployment,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
    )
