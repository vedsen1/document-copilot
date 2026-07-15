"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-15

Creates:
  - pgvector extension
  - users
  - source_documents
  - document_chunks  (with vector(1536) embedding, generated tsvector, HNSW + GIN indexes)
  - chat_threads
  - chat_messages
  - message_citations
  - RLS policies (users see only their own chat_threads, chat_messages, message_citations)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # pgvector extension
    # ------------------------------------------------------------------
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ------------------------------------------------------------------
    # users
    # Mirrors the Supabase auth.users table via id (UUID from Supabase Auth).
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    # ------------------------------------------------------------------
    # source_documents
    # ------------------------------------------------------------------
    op.create_table(
        "source_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("ticker", sa.String(16), nullable=False),
        sa.Column("cik", sa.String(16), nullable=False),
        sa.Column("form", sa.String(16), nullable=False),
        sa.Column("filing_date", sa.Date, nullable=False),
        sa.Column("report_date", sa.Date, nullable=True),
        sa.Column("accession_number", sa.String(64), nullable=False, unique=True),
        sa.Column("source_url", sa.Text, nullable=False),
        sa.Column("markdown_content", sa.Text, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_source_documents_ticker", "source_documents", ["ticker"])

    # ------------------------------------------------------------------
    # document_chunks
    # embedding is vector(1536); search_vector is a generated tsvector.
    # Both require explicit DDL — autogenerate cannot produce these reliably.
    # ------------------------------------------------------------------
    op.create_table(
        "document_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("source_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("page", sa.String(64), nullable=True),
        sa.Column("section", sa.String(256), nullable=True),
        sa.Column("token_count", sa.Integer, nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        # vector(1536) — must be written as raw DDL; SQLAlchemy type renderer
        # does not render pgvector columns reliably across all Alembic versions.
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_document_chunks_document_chunk_index"
        ),
    )

    # Add the vector column and generated tsvector column with raw DDL.
    op.execute(
        "ALTER TABLE document_chunks ADD COLUMN embedding vector(1536)"
    )
    op.execute(
        """
        ALTER TABLE document_chunks
        ADD COLUMN search_vector tsvector
        GENERATED ALWAYS AS (to_tsvector('english', coalesce(text, ''))) STORED
        """
    )

    op.create_index("ix_document_chunks_document_id", "document_chunks", ["document_id"])

    # HNSW index for semantic (vector) search.
    op.execute(
        """
        CREATE INDEX ix_document_chunks_embedding_hnsw
        ON document_chunks
        USING hnsw (embedding vector_cosine_ops)
        """
    )

    # GIN index for full-text search.
    op.execute(
        """
        CREATE INDEX ix_document_chunks_search_vector_gin
        ON document_chunks
        USING gin (search_vector)
        """
    )

    # ------------------------------------------------------------------
    # chat_threads
    # ------------------------------------------------------------------
    op.create_table(
        "chat_threads",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "title", sa.String(256), nullable=False, server_default="New chat"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_threads_user_id", "chat_threads", ["user_id"])

    # ------------------------------------------------------------------
    # chat_messages
    # ------------------------------------------------------------------
    op.create_table(
        "chat_messages",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "thread_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_threads.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(32), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("message_data", postgresql.JSONB, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_chat_messages_thread_id", "chat_messages", ["thread_id"])
    op.create_index("ix_chat_messages_created_at", "chat_messages", ["created_at"])

    # ------------------------------------------------------------------
    # message_citations
    # ------------------------------------------------------------------
    op.create_table(
        "message_citations",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "message_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "chunk_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("document_chunks.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("citation_index", sa.Integer, nullable=False),
        sa.Column("excerpt", sa.Text, nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB,
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_message_citations_message_id", "message_citations", ["message_id"]
    )

    # ------------------------------------------------------------------
    # Row-Level Security
    # Analysts can only see their own chat data.
    # source_documents and document_chunks are corpus data — readable by all
    # authenticated users; writes are service-role only (no RLS needed here).
    # ------------------------------------------------------------------
    for table in ("chat_threads", "chat_messages", "message_citations"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")

    # chat_threads: owner is the row's user_id.
    op.execute(
        """
        CREATE POLICY chat_threads_owner
        ON chat_threads
        USING (user_id = (SELECT id FROM users WHERE email = current_setting('request.jwt.claims', true)::json->>'email' LIMIT 1))
        """
    )

    # chat_messages: accessible if the parent thread belongs to the current user.
    op.execute(
        """
        CREATE POLICY chat_messages_owner
        ON chat_messages
        USING (
            thread_id IN (
                SELECT id FROM chat_threads
                WHERE user_id = (SELECT id FROM users WHERE email = current_setting('request.jwt.claims', true)::json->>'email' LIMIT 1)
            )
        )
        """
    )

    # message_citations: accessible if the parent message's thread belongs to the current user.
    op.execute(
        """
        CREATE POLICY message_citations_owner
        ON message_citations
        USING (
            message_id IN (
                SELECT cm.id FROM chat_messages cm
                JOIN chat_threads ct ON ct.id = cm.thread_id
                WHERE ct.user_id = (SELECT id FROM users WHERE email = current_setting('request.jwt.claims', true)::json->>'email' LIMIT 1)
            )
        )
        """
    )


def downgrade() -> None:
    # Drop in reverse dependency order.
    op.drop_table("message_citations")
    op.drop_table("chat_messages")
    op.drop_table("chat_threads")
    op.drop_table("document_chunks")
    op.drop_table("source_documents")
    op.drop_table("users")
    op.execute("DROP EXTENSION IF EXISTS vector")
