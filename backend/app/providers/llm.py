from __future__ import annotations

from livekit.plugins import openai

from ..config import Settings


def build_llm(settings: Settings) -> openai.LLM:
    """Azure OpenAI chat deployment'ına bağlanan LLM örneği.

    `reasoning_effort="minimal"`: reasoning modellerinde gereksiz iç
    muhakemeyi atlayıp TTFT'yi düşürüyor (~2.2sn -> ~1.2sn, canlı ölçüm).
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
