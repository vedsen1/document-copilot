from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.retrieval.retriever import search_hybrid


async def retrieve_for_query(session: AsyncSession, query: str, k: int = 5):
    """Wrapper used by app.api.chat to surface retrieval candidates.

    Uses the backend.retrieval implementation.
    """
    result = await search_hybrid(session, query, embed_vector=None, k=k)
    return [
        {
            "chunk_id": str(p.chunk_id),
            "document_id": str(p.document_id),
            "section": p.section,
            "text": p.text[:1000],
            "rank": p.rank,
        }
        for p in result.passages
    ]
