from __future__ import annotations

from openai import AsyncAzureOpenAI

from ..config import Settings

# Tek istekte gönderilecek maksimum metin sayısı — Azure OpenAI embeddings
# endpoint'inin istek başına input limitini aşmamak için parti halinde gönderilir.
EMBED_BATCH_SIZE = 64


class Embedder:
    """Azure OpenAI embedding deployment'ına ince bir sarmalayıcı."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncAzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            api_key=settings.azure_openai_api_key,
            api_version=settings.azure_openai_api_version,
        )
        self._deployment = settings.azure_openai_embedding_deployment
        self._dimensions = settings.azure_openai_embedding_dimensions

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Her metin için bir embedding vektörü döner (girdiyle aynı sırada)."""
        if not texts:
            return []

        vectors: list[list[float]] = []
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch = texts[i : i + EMBED_BATCH_SIZE]
            response = await self._client.embeddings.create(
                model=self._deployment,
                input=batch,
                dimensions=self._dimensions,
            )
            vectors.extend(item.embedding for item in response.data)
        return vectors
