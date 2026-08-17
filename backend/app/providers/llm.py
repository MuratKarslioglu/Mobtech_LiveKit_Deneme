from __future__ import annotations

from livekit.plugins import google

from ..config import Settings


def build_llm(settings: Settings) -> google.LLM:
    """Gemini Developer API'ye kendi GOOGLE_API_KEY'imizle bağlanan LLM örneği.

    max_output_tokens ve temperature, sesli asistan için kısa/öz cevaplar
    hedefiyle bilinçli olarak düşük tutuluyor (bkz. app/prompts/system.py).
    """
    return google.LLM(
        model=settings.gemini_llm_model,
        temperature=0.6,
        max_output_tokens=200,
    )
