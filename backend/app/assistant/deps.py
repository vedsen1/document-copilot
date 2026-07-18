"""Runtime dependencies for the document agent."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from uuid import UUID

from app.retrieval.types import RetrievedPassage

if TYPE_CHECKING:
    from app.retrieval.retriever import DocumentRetriever

StatusCallback = Callable[[str, str], None]


@dataclass
class TurnRegistry:
    """Tracks every chunk retrieved during a turn — the citation allowlist."""

    passages_by_chunk_id: dict[UUID, RetrievedPassage] = field(default_factory=dict)

    def register(self, passage: RetrievedPassage) -> None:
        self.passages_by_chunk_id[passage.chunk_id] = passage
        # Handle both old and new RetrievedPassage models
        if hasattr(passage, 'neighbors'):
            for neighbor in passage.neighbors:
                self.passages_by_chunk_id[neighbor.chunk_id] = neighbor

    def register_many(self, passages: list[RetrievedPassage]) -> None:
        for passage in passages:
            self.register(passage)


@dataclass
class DocumentAgentDeps:
    retriever: "DocumentRetriever"
    registry: TurnRegistry
    thread_id: UUID
    user_id: UUID
    on_status: StatusCallback | None = None

    def emit_status(self, stage: str, message: str) -> None:
        if self.on_status is not None:
            self.on_status(stage, message)
