from __future__ import annotations

from pydantic import BaseModel
from typing import Any
import uuid


class RetrievedPassage(BaseModel):
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    text: str
    section: str | None
    score: float
    rank: int
    metadata: dict[str, Any] = {}


class RetrieverResult(BaseModel):
    query: str
    passages: list[RetrievedPassage]

