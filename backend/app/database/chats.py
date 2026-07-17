"""Chat persistence helpers — threads, messages, user upsert.

All functions take an open ``AsyncSession`` and return SQLAlchemy model
instances.  No business logic lives here; callers own validation and
authorization.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models.chat_message import ChatMessage
from app.database.models.chat_thread import ChatThread
from app.database.models.user import User


# ---------------------------------------------------------------------------
# User sync
# ---------------------------------------------------------------------------


async def upsert_user(session: AsyncSession, user_id: str, email: str) -> User:
    """Keep the local ``users`` table in sync with Supabase Auth.

    Called on every authenticated request so the FK from chat_threads is
    always satisfiable.  One cheap INSERT … ON CONFLICT DO UPDATE.
    """
    uid = uuid.UUID(user_id)
    user = await session.get(User, uid)
    if user is None:
        user = User(id=uid, email=email)
        session.add(user)
    elif user.email != email:
        user.email = email
    return user


# ---------------------------------------------------------------------------
# Threads
# ---------------------------------------------------------------------------


async def list_threads(session: AsyncSession, user_id: str) -> list[ChatThread]:
    uid = uuid.UUID(user_id)
    result = await session.execute(
        select(ChatThread)
        .where(ChatThread.user_id == uid)
        .order_by(ChatThread.updated_at.desc())
    )
    return list(result.scalars().all())


async def create_thread(
    session: AsyncSession,
    user_id: str,
    title: str = "New chat",
) -> ChatThread:
    thread = ChatThread(user_id=uuid.UUID(user_id), title=title)
    session.add(thread)
    await session.flush()   # populate generated fields (id, timestamps)
    return thread


async def get_thread(session: AsyncSession, thread_id: str) -> ChatThread | None:
    return await session.get(ChatThread, uuid.UUID(thread_id))


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------


async def list_messages(
    session: AsyncSession, thread_id: str
) -> list[ChatMessage]:
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.thread_id == uuid.UUID(thread_id))
        .order_by(ChatMessage.created_at)
    )
    return list(result.scalars().all())


async def create_message(
    session: AsyncSession,
    thread_id: str,
    role: str,
    content: str,
) -> ChatMessage:
    msg = ChatMessage(
        thread_id=uuid.UUID(thread_id),
        role=role,
        content=content,
    )
    session.add(msg)
    await session.flush()
    return msg
