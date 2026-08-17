from __future__ import annotations

from livekit.plugins import openai

from ..config import Settings


def build_llm(settings: Settings) -> openai.LLM:
    """Azure OpenAI (Azure AI Foundry) chat deployment'ına bağlanan LLM örneği.

    `reasoning_effort="minimal"`: gpt-5-mini gibi reasoning modellerinde
    gereksiz iç muhakemeyi atlayıp gecikmeyi belirgin şekilde düşürüyor
    (canlı ölçümde ortalama ~2.2sn -> ~1.2sn TTFT). Sesli asistan için
    öncelik hızlı/kısa cevap, derin muhakeme değil.
    """
    return openai.LLM.with_azure(
        model=settings.azure_openai_llm_deployment,
        azure_endpoint=settings.azure_openai_endpoint,
        azure_deployment=settings.azure_openai_llm_deployment,
        api_version=settings.azure_openai_api_version,
        api_key=settings.azure_openai_api_key,
        reasoning_effort="minimal",
        temperature=0.6,
        max_completion_tokens=200,
    )
