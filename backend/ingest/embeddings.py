"""
OpenAI embedding helpers.

All public functions are async and accept an AsyncOpenAI client. Batching is
handled automatically to stay within the API's per-request item limit.

Usage:
    from ingest.embeddings import embed_all

    vectors = await embed_all(openai_client, texts, model)
"""
from __future__ import annotations


async def embed_batch(client, texts: list[str], model: str) -> list[list[float]]:
    """Embed one batch of texts; preserves input ordering via response index."""
    response = await client.embeddings.create(input=texts, model=model)
    return [item.embedding for item in sorted(response.data, key=lambda x: x.index)]


async def embed_all(
    client,
    texts: list[str],
    model: str,
    batch_size: int = 100,
) -> list[list[float]]:
    """
    Embed arbitrarily many texts by splitting into API-safe batches.

    OpenAI's embedding endpoint accepts up to 2 048 inputs per request;
    batch_size=100 is conservative and well within all tier limits.
    """
    results: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        vectors = await embed_batch(client, texts[i : i + batch_size], model)
        results.extend(vectors)
    return results
