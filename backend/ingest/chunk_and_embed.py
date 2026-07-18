"""
Chunk, embed, and store 10-K filings in Supabase.

Reads data/markdown/manifest.json, converts each markdown file to a
DoclingDocument, splits it with HybridChunker (text-embedding-3-small
tokenizer, 512 tokens per chunk), generates embeddings via OpenAI, and
writes document_chunks rows.  SourceDocument rows are upserted automatically.

Usage (from repo root):
    # Validate the whole pipeline cheaply — 1 chunk, 1 filing, ~1 API call:
    uv run --project backend backend/ingest/chunk_and_embed.py --smoke-test

    # Single ticker:
    uv run --project backend backend/ingest/chunk_and_embed.py --tickers AAPL

    # Full corpus, skipping already-ingested filings:
    uv run --project backend backend/ingest/chunk_and_embed.py --skip-existing

    # Combined:
    uv run --project backend backend/ingest/chunk_and_embed.py --tickers MSFT NVDA --skip-existing
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
MARKDOWN_DIR = _REPO_ROOT / "data" / "markdown"
MANIFEST_PATH = MARKDOWN_DIR / "manifest.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--smoke-test",
        action="store_true",
        help=(
            "Embed only the first chunk of the first selected filing and write "
            "it to Supabase, then exit.  Use this to validate the pipeline "
            "end-to-end before spending credits on a full corpus run."
        ),
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip filings that already have chunks in document_chunks.",
    )
    p.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Restrict to these tickers (e.g. AAPL MSFT).",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------


async def _get_chunked_accessions(session) -> set[str]:
    """Return accession_numbers that already have at least one document_chunk."""
    from sqlalchemy import text

    result = await session.execute(
        text(
            "SELECT DISTINCT sd.accession_number "
            "FROM source_documents sd "
            "JOIN document_chunks dc ON dc.document_id = sd.id"
        )
    )
    return {row[0] for row in result.fetchall()}


async def _insert_chunks(
    session,
    doc_id,
    chunks: list[dict],
    embeddings: list[list[float]],
) -> None:
    from app.database.models.document_chunk import DocumentChunk

    for chunk, vector in zip(chunks, embeddings):
        session.add(
            DocumentChunk(
                document_id=doc_id,
                chunk_index=chunk["chunk_index"],
                text=chunk["text"],
                section=chunk.get("section"),
                # Approximate; exact count would require passing the tokenizer here
                token_count=len(chunk["text"]) // 4,
                embedding=vector,
                chunk_metadata=chunk.get("chunk_metadata", {}),
            )
        )


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------


async def run(args: argparse.Namespace) -> None:
    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        sys.exit(
            "Required packages not importable.\n"
            "Run via:  uv run --project backend backend/ingest/chunk_and_embed.py"
        )

    from openai import AsyncOpenAI
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.database.models import __all__ as _  # ensures models are registered  # noqa: F401
    from ingest.chunking import build_chunker, build_converter, chunk_document
    from ingest.embeddings import embed_all
    from ingest.load_source_documents import upsert_source_document

    if not MANIFEST_PATH.exists():
        sys.exit(
            f"Manifest not found: {MANIFEST_PATH}\n"
            "Run data/convert_to_markdown.py first."
        )

    with MANIFEST_PATH.open(encoding="utf-8") as f:
        manifest = json.load(f)

    filings = manifest["filings"]
    if args.tickers:
        tickers_upper = {t.upper() for t in args.tickers}
        filings = [f for f in filings if f["ticker"] in tickers_upper]
        if not filings:
            sys.exit(f"No filings found for tickers: {args.tickers}")

    if args.smoke_test:
        # Pick just the first filing; we will also truncate to 1 chunk below
        filings = filings[:1]

    db_url = (
        settings.database_url
        .replace("postgresql://", "postgresql+psycopg://", 1)
        .replace("postgres://", "postgresql+psycopg://", 1)
    )
    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)
    openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    embedding_model = settings.openai_embedding_model

    # Fetch already-chunked accessions once upfront
    async with SessionFactory() as session:
        async with session.begin():
            already_chunked = await _get_chunked_accessions(session)

    print("Initialising docling chunker and converter...")
    chunker = build_chunker()
    converter = build_converter()
    print("Ready.\n")

    total = len(filings)
    ingested = skipped = failed = 0

    for i, filing in enumerate(filings, 1):
        accession = filing["accession_number"]
        label = f"[{i}/{total}] {filing['ticker']} {filing['filing_date']}"

        if args.skip_existing and accession in already_chunked:
            print(f"{label}  [SKIP] already chunked")
            skipped += 1
            continue

        md_path = MARKDOWN_DIR / Path(filing["markdown_path"])
        if not md_path.exists():
            print(f"{label}  [ERROR] markdown file missing: {md_path}")
            failed += 1
            continue

        markdown = md_path.read_text(encoding="utf-8")

        # Chunk in a thread — convert_string is synchronous CPU work
        chunks = await asyncio.to_thread(chunk_document, markdown, chunker, converter)

        if not chunks:
            print(f"{label}  [WARN] no chunks produced, skipping")
            failed += 1
            continue

        if args.smoke_test:
            chunks = chunks[:1]  # only 1 API call

        print(f"{label}  {len(chunks)} chunk(s)  ", end="", flush=True)

        try:
            # embed_text carries the context-enriched version (heading path + body)
            embed_texts = [c["embed_text"] for c in chunks]
            embeddings = await embed_all(openai_client, embed_texts, embedding_model)

            async with SessionFactory() as session:
                async with session.begin():
                    # upsert_source_document deletes + re-inserts, cascading to
                    # any existing chunks for this filing via the FK cascade
                    doc_id = await upsert_source_document(session, filing, markdown)
                    await _insert_chunks(session, doc_id, chunks, embeddings)

            ingested += 1
            print("[OK]")

            if args.smoke_test:
                print(
                    f"\n✓ Smoke test passed.\n"
                    f"  doc_id      = {doc_id}\n"
                    f"  chunk_index = 0\n"
                    f"  section     = {chunks[0].get('section')!r}\n"
                    f"  headings    = {chunks[0]['chunk_metadata']['headings']}\n"
                    f"\n"
                    f"Check Supabase: document_chunks should have 1 row with a "
                    f"non-null embedding ({len(embeddings[0])} floats)."
                )

        except Exception as exc:
            failed += 1
            print(f"[ERROR] {exc}")

    await engine.dispose()

    if not args.smoke_test:
        print(f"\nDone.  ingested={ingested}  skipped={skipped}  failed={failed}")


def main() -> None:
    args = parse_args()
    # psycopg async is incompatible with Windows ProactorEventLoop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
