from __future__ import annotations

from typing import List, Dict
from sqlalchemy import text


async def search_fulltext(session, query: str, candidate_k: int = 50) -> List[Dict]:
    """Run Postgres full-text search over `search_vector`.

    Returns list of dicts: {'chunk_id': uuid, 'document_id': uuid, 'score': float}
    """
    # Use websearch_to_tsquery for user-friendly query parsing when available.
    sql = (
        "SELECT id, document_id, ts_rank_cd(search_vector, q) AS score "
        "FROM document_chunks, to_tsquery(:q) q "
        "WHERE search_vector @@ q "
        "ORDER BY score DESC LIMIT :k"
    )

    # If websearch_to_tsquery is available in the DB, callers can replace the query
    # assembly with that function. Keep this implementation simple for Phase 5.

    result = await session.execute(text(sql), {"q": query, "k": candidate_k})
    rows = result.fetchall()
    out = []
    for row in rows:
        out.append({"chunk_id": row[0], "document_id": row[1], "score": float(row[2]) if row[2] is not None else 0.0})
    return out

