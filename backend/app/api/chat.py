"""Chat API — thread CRUD and streaming chat endpoint.

Routes
------
GET  /chat/threads                        list the authenticated user's threads
POST /chat/threads                        create a new thread
GET  /chat/threads/{thread_id}/messages   load message history for a thread
POST /chat/stream                         streaming chat turn (stubbed)

Authorization
-------------
Every route that touches a specific thread calls ``_require_thread`` which
returns 404 if the thread doesn't exist and 403 if it belongs to a different
user.  This keeps the ownership check in one place.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.dependencies import CurrentUser
from app.database import chats
from app.database.models.chat_thread import ChatThread
from app.database.session import get_session

router = APIRouter(prefix="/chat", tags=["chat"])

# Convenience type alias for the injected session
DB = Annotated[AsyncSession, Depends(get_session)]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ThreadOut(BaseModel):
    id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: uuid.UUID
    thread_id: uuid.UUID
    role: str
    content: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class CreateThreadIn(BaseModel):
    title: str = "New chat"


class AiSdkMessage(BaseModel):
    role: str
    content: str


class StreamIn(BaseModel):
    thread_id: uuid.UUID
    messages: list[AiSdkMessage]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _require_thread(
    session: AsyncSession,
    thread_id: str,
    user_id: str,
) -> ChatThread:
    """Return the thread or raise 404/403."""
    thread = await chats.get_thread(session, thread_id)
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
    if str(thread.user_id) != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Thread not found or access denied",
        )
    return thread


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/threads", response_model=list[ThreadOut])
async def list_threads(user: CurrentUser, db: DB) -> list[ThreadOut]:
    await chats.upsert_user(db, user.id, user.email or "")  # type: ignore[union-attr]
    threads = await chats.list_threads(db, user.id)  # type: ignore[union-attr]
    return [ThreadOut.model_validate(t) for t in threads]


@router.post("/threads", response_model=ThreadOut, status_code=status.HTTP_201_CREATED)
async def create_thread(body: CreateThreadIn, user: CurrentUser, db: DB) -> ThreadOut:
    await chats.upsert_user(db, user.id, user.email or "")  # type: ignore[union-attr]
    thread = await chats.create_thread(db, user.id, body.title)  # type: ignore[union-attr]
    return ThreadOut.model_validate(thread)


@router.get("/threads/{thread_id}/messages", response_model=list[MessageOut])
async def list_messages(
    thread_id: str, user: CurrentUser, db: DB
) -> list[MessageOut]:
    await _require_thread(db, thread_id, user.id)  # type: ignore[union-attr]
    messages = await chats.list_messages(db, thread_id)
    return [MessageOut.model_validate(m) for m in messages]


@router.post("/stream")
async def stream_chat(body: StreamIn, user: CurrentUser, db: DB) -> StreamingResponse:
    thread_id = str(body.thread_id)
    user_id: str = user.id  # type: ignore[union-attr]
    user_email: str = user.email or ""  # type: ignore[union-attr]

    await chats.upsert_user(db, user_id, user_email)
    await _require_thread(db, thread_id, user_id)

    # Persist the incoming user message (last message in the list).
    # The history is already in the DB; only the new turn needs saving.
    user_message = next(
        (m for m in reversed(body.messages) if m.role == "user"), None
    )
    if user_message:
        await chats.create_message(db, thread_id, "user", user_message.content)

    # Collect the stub reply so we can persist it after streaming.
    stub_parts = [
        "This is a stubbed assistant reply. ",
        "Real retrieval and LLM generation will be wired in Phase 6. ",
        "The streaming pipeline is working end-to-end.",
    ]
    full_reply = "".join(stub_parts)

    # Persist the assistant message now — before streaming starts — so it's
    # always saved even if the client disconnects mid-stream.
    await chats.create_message(db, thread_id, "assistant", full_reply)

    async def event_stream() -> AsyncGenerator[str, None]:
        for part in stub_parts:
            yield f"data: {part}\n\n"
            await asyncio.sleep(0.05)
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")
