from __future__ import annotations

from typing import List
from sqlalchemy.ext.asyncio import AsyncSession
from .fusion import reciprocal_rank_fusion
from .types import RetrievedPassage, RetrieverResult


async def search_hybrid(
    session: AsyncSession,
    query: str,
    embed_vector=None,
    k: int = 10,
    candidate_k: int = 50,
    expand_neighbors: int = 0,
):
    """Run hybrid retrieval: full-text + pgvector -> RRF -> return top-k passages.

    - `embed_vector`: if provided, passed to pgvector KNN search; otherwise pgvector
       step is skipped.
    """
    from .fulltext_search import search_fulltext
    from .pgvector_search import search_pgvector

    # run full-text
    ft_candidates = await search_fulltext(session, query, candidate_k)
    ft_ids = [str(r["chunk_id"]) for r in ft_candidates]

    pv_ids = []
    if embed_vector is not None:
        pv_candidates = await search_pgvector(session, embed_vector, candidate_k)
        pv_ids = [str(r["chunk_id"]) for r in pv_candidates]
    # fuse ranks
    rank_lists = [lst for lst in (pv_ids, ft_ids) if lst]
    fused = reciprocal_rank_fusion(rank_lists)

    # Fetch top-K chunks details from DB in ranked order
    top_ids = fused[:k]
    if not top_ids:
        # fallback to ft candidates
        top_ids = ft_ids[:k]

    # Query DB for chunk details in order
    from sqlalchemy import text

    # Build ordered query using VALUES to preserve order
    if not top_ids:
        return RetrieverResult(query=query, passages=[])

    vals = ", ".join([f"(:id{i}, {idx})" for i, idx in enumerate(range(len(top_ids)))])
    params = {f"id{i}": top_ids[i] for i in range(len(top_ids))}

    sql = text(
        f"WITH wanted(id, ord) AS (VALUES {vals}) "
        "SELECT dc.id, dc.document_id, dc.text, dc.section, w.ord "
        "FROM wanted w JOIN document_chunks dc ON dc.id = w.id "
        "ORDER BY w.ord"
    )

    result = await session.execute(sql, params)
    rows = result.fetchall()

    passages: List[RetrievedPassage] = []
    for rank, row in enumerate(rows, start=1):
        passages.append(
            RetrievedPassage(
                chunk_id=row[0],
                document_id=row[1],
                text=row[2],
                section=row[3],
                score=0.0,
                rank=rank,
                metadata={},
            )
        )

    return RetrieverResult(query=query, passages=passages)

