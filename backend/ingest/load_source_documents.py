"""
Ingest source document metadata into the database.

Reads data/markdown/manifest.json, upserts one SourceDocument row per filing
(ticker, dates, accession number, raw markdown content, etc.).  Does NOT
create chunks or embeddings — run chunk_and_embed.py for that.

Usage (from repo root):
    uv run --project backend backend/ingest/load_source_documents.py
    uv run --project backend backend/ingest/load_source_documents.py --tickers AAPL MSFT
    uv run --project backend backend/ingest/load_source_documents.py --skip-existing
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import date
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
        "--skip-existing",
        action="store_true",
        help="Skip filings whose accession_number is already in source_documents.",
    )
    p.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Restrict to these tickers (e.g. AAPL MSFT).",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# DB helpers — imported by chunk_and_embed.py as well
# ---------------------------------------------------------------------------


async def get_existing_accessions(session) -> set[str]:
    """Return the set of accession_numbers already present in source_documents."""
    from sqlalchemy import text

    result = await session.execute(text("SELECT accession_number FROM source_documents"))
    return {row[0] for row in result.fetchall()}


async def upsert_source_document(session, filing: dict, markdown: str):
    """
    Insert or replace a SourceDocument row for the given filing.

    Deletes any existing row with the same accession_number first so the
    caller never needs to handle unique-constraint conflicts.  The CASCADE
    on document_chunks.document_id means a re-run also clears stale chunks.

    Returns the new row's UUID id.
    """
    from sqlalchemy import text

    from app.database.models.source_document import SourceDocument

    await session.execute(
        text("DELETE FROM source_documents WHERE accession_number = :acc"),
        {"acc": filing["accession_number"]},
    )

    doc = SourceDocument(
        ticker=filing["ticker"],
        cik=filing["cik"],
        form=filing["form"],
        filing_date=date.fromisoformat(filing["filing_date"]),
        report_date=(
            date.fromisoformat(filing["report_date"])
            if filing.get("report_date")
            else None
        ),
        accession_number=filing["accession_number"],
        source_url=filing["source_url"],
        markdown_content=markdown,
    )
    session.add(doc)
    await session.flush()  # populate doc.id without committing
    return doc.id


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def ingest(args: argparse.Namespace) -> None:
    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        sys.exit(
            "Required packages not importable.\n"
            "Run via:  uv run --project backend backend/ingest/load_source_documents.py"
        )

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from app.config import settings
    from app.database.models import __all__ as _  # ensures models are registered  # noqa: F401

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

    db_url = (
        settings.database_url
        .replace("postgresql://", "postgresql+psycopg://", 1)
        .replace("postgres://", "postgresql+psycopg://", 1)
    )
    engine = create_async_engine(db_url, pool_pre_ping=True)
    SessionFactory = async_sessionmaker(engine, expire_on_commit=False)

    async with SessionFactory() as session:
        async with session.begin():
            existing = await get_existing_accessions(session)

    total = len(filings)
    ingested = skipped = failed = 0

    for i, filing in enumerate(filings, 1):
        accession = filing["accession_number"]
        label = f"[{i}/{total}] {filing['ticker']} {filing['filing_date']}"

        if args.skip_existing and accession in existing:
            print(f"{label}  [SKIP] already in DB")
            skipped += 1
            continue

        md_path = MARKDOWN_DIR / Path(filing["markdown_path"])
        if not md_path.exists():
            print(f"{label}  [ERROR] markdown file missing: {md_path}")
            failed += 1
            continue

        markdown = md_path.read_text(encoding="utf-8")
        print(f"{label}  ", end="", flush=True)

        try:
            async with SessionFactory() as session:
                async with session.begin():
                    await upsert_source_document(session, filing, markdown)
            ingested += 1
            print("[OK]")
        except Exception as exc:
            failed += 1
            print(f"[ERROR] {exc}")

    await engine.dispose()
    print(f"\nDone.  ingested={ingested}  skipped={skipped}  failed={failed}")


def main() -> None:
    args = parse_args()
    # psycopg async is incompatible with Windows ProactorEventLoop
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(ingest(args))


if __name__ == "__main__":
    main()

