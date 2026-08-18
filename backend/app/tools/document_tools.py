from __future__ import annotations

from livekit.agents import function_tool

from ..config import settings
from ..models.tool_config import ToolConfig
from ..retrieval.retriever import get_retriever
from .registry import register_tool


@function_tool()
async def search_documents(query: str) -> str:
    """Kullanıcının yüklediği belgeler (PDF/TXT/DOCX) arasında anlamsal arama
    yapar ve en ilgili parçaları döndürür. Kullanıcı yüklenen belgelerin
    içeriğiyle ilgili bir şey sorduğunda bu tool'u çağır.

    Args:
        query: Belgelerde aranacak konu veya soru
    """
    retriever = get_retriever(settings)
    results = await retriever.search(query)
    if not results:
        return "Yüklenmiş belgeler arasında bu konuyla ilgili bir sonuç bulunamadı."

    parts = [f"[{result.filename}]\n{result.text}" for result in results]
    return "\n\n".join(parts)


register_tool(
    search_documents,
    ToolConfig(
        name="search_documents",
        expected_latency="medium",
        interim_message="İlgili belgeleri inceliyorum.",
    ),
)
