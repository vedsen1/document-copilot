from __future__ import annotations

from typing import List, Dict, Any
from sqlalchemy import text


async def search_pgvector(session, query: str, candidate_k: int = 50, filters: Dict[str, Any] | None = None) -> List[Dict]:
    """Run a pgvector HNSW KNN search using cosine ops.

    Returns list of dicts: {'chunk_id': uuid, 'document_id': uuid, 'score': float}
    """
    sql = (
        "SELECT id, document_id, 1 - (embedding <#> :q) AS score "
        "FROM document_chunks "
        "WHERE embedding IS NOT NULL "
    )
    if filters and "ticker" in filters:
        sql += "AND document_id IN (SELECT id FROM source_documents WHERE ticker = :ticker) "

    sql += "ORDER BY embedding <#> :q LIMIT :k"

    # We pass the query vector in as 'q' — caller should embed the query
    # If caller passes a precomputed vector, they should bind accordingly.
    # For Phase 5 we expect the caller to supply embedding as binary/array;
    # here we use a placeholder param and assume the DB client can map it.

    result = await session.execute(
        text(sql),
        {"q": query, "k": candidate_k, "ticker": filters.get("ticker") if filters else None},
    )
    rows = result.fetchall()
    out = []
    for row in rows:
        out.append({"chunk_id": row[0], "document_id": row[1], "score": float(row[2]) if row[2] is not None else 0.0})
    return out

