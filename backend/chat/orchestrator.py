from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.retrieval.retriever import search_hybrid


async def retrieve_for_query(session: AsyncSession, query: str, k: int = 5):
    """Convenience wrapper to run retrieval and return simplified results."""
    # Note: embedding generation is Phase 6; for now we run full-text only.
    result = await search_hybrid(session, query, embed_vector=None, k=k)
    # Map to simple dicts for callers
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

