"""Verification script — runs all 10 client-brief example queries against the
ingested corpus and produces a markdown report.

Usage
-----
    # from the backend/ directory
    uv run python tests/verify_retrieval.py

    # optionally save to a file (default: tests/verification_report.md)
    uv run python tests/verify_retrieval.py --output tests/verification_report.md

Prerequisites
-------------
- Active Supabase connection (DATABASE_URL in .env)
- OpenAI API key (OPENAI_API_KEY in .env)
- Ingested corpus (run ingest pipeline first)
"""
from __future__ import annotations

import argparse
import asyncio
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database.session import _SessionFactory
from app.retrieval.retriever import search_hybrid
from app.retrieval.types import RetrievedPassage


# ---------------------------------------------------------------------------
# Client-brief example questions (verbatim from docs/client-brief.md)
# ---------------------------------------------------------------------------

QUESTIONS: list[str] = [
    # Q1
    "Across Apple's 2021–2025 10-Ks, how did the revenue mix between iPhone, "
    "Services, Mac, iPad, and Wearables change, and which category appears to "
    "have contributed most to any mix shift?",
    # Q2
    "For Amazon, compare AWS operating income and margin against North America "
    "and International from 2021–2025. In which years did AWS appear to fund "
    "losses or weaker profitability elsewhere?",
    # Q3
    "How did NVIDIA describe demand drivers, customer concentration, and supply "
    "constraints for its Data Center business from fiscal 2021 through fiscal 2025?",
    # Q4
    "Across Microsoft's 2021–2025 filings, what changed in the way the company "
    "describes Azure, AI infrastructure, and cloud capacity constraints?",
    # Q5
    "For Alphabet, how did Google Search, YouTube ads, Google Network, "
    "subscriptions/platforms/devices, and Google Cloud revenue trends differ "
    "across the available 10-Ks?",
    # Q6
    "Which of the five companies added, removed, or materially changed "
    "risk-factor language related to AI, cloud infrastructure, export controls, "
    "supply chain concentration, or regulation between 2021 and 2025?",
    # Q7
    "For Apple and NVIDIA, what do the filings say about supplier concentration "
    "or dependence on third-party manufacturing, and did the wording become more "
    "or less urgent over time?",
    # Q8
    "Compare capital expenditures and purchase commitments for Microsoft, "
    "Alphabet, Amazon, and NVIDIA. What do the filings imply about the scale "
    "and timing of AI/cloud infrastructure investment?",
    # Q9
    "For each company, summarize the most important geographic revenue exposures "
    "disclosed in the latest 10-K, then identify any year-over-year changes that "
    "could matter to an analyst.",
    # Q10
    "If an analyst asks whether the filings prove that generative AI improved "
    "margins for any of these companies, what evidence exists in the corpus, and "
    "where should the bot refuse to infer beyond the filings?",
]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PassageSummary:
    rank: int
    chunk_id: str
    document_id: str
    section: str | None
    snippet: str  # first 300 chars of text


@dataclass
class QueryResult:
    question_number: int
    question: str
    passage_summaries: list[PassageSummary] = field(default_factory=list)
    error: str | None = None


# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------

async def _embed(client: AsyncOpenAI, text: str) -> list[float]:
    response = await client.embeddings.create(
        input=[text],
        model=settings.openai_embedding_model,
    )
    return response.data[0].embedding


async def verify_query(
    session: AsyncSession,
    client: AsyncOpenAI,
    question_number: int,
    question: str,
    k: int = 5,
) -> QueryResult:
    """Embed a question, run hybrid retrieval, and return a QueryResult."""
    try:
        vector = await _embed(client, question)
        result = await search_hybrid(
            session=session,
            query=question,
            embed_vector=vector,
            k=k,
            candidate_k=50,
        )
        summaries = [
            PassageSummary(
                rank=p.rank,
                chunk_id=str(p.chunk_id),
                document_id=str(p.document_id),
                section=p.section,
                snippet=textwrap.shorten(p.text, width=300, placeholder="…"),
            )
            for p in result.passages
        ]
        return QueryResult(
            question_number=question_number,
            question=question,
            passage_summaries=summaries,
        )
    except Exception as exc:  # noqa: BLE001
        return QueryResult(
            question_number=question_number,
            question=question,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def _render_markdown(results: list[QueryResult], elapsed_seconds: float) -> str:
    lines: list[str] = []

    lines.append("# Phase 5 Retrieval Verification Report")
    lines.append(f"\nGenerated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    lines.append(f"Total queries: {len(results)}")
    lines.append(f"Elapsed: {elapsed_seconds:.1f}s")
    lines.append(f"Embedding model: `{settings.openai_embedding_model}`")
    lines.append("\n---\n")

    ok_count = sum(1 for r in results if not r.error and r.passage_summaries)
    empty_count = sum(1 for r in results if not r.error and not r.passage_summaries)
    err_count = sum(1 for r in results if r.error)

    lines.append("## Summary\n")
    lines.append(f"| Status | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| ✅ Returned passages | {ok_count} |")
    lines.append(f"| ⚠️ No passages found | {empty_count} |")
    lines.append(f"| ❌ Error | {err_count} |")
    lines.append("\n---\n")

    for r in results:
        lines.append(f"## Q{r.question_number}")
        lines.append(f"\n> {r.question}\n")

        if r.error:
            lines.append(f"**❌ Error:** `{r.error}`\n")
            continue

        if not r.passage_summaries:
            lines.append("**⚠️ No passages returned for this query.**\n")
            continue

        lines.append(f"**Passages returned:** {len(r.passage_summaries)}\n")
        for p in r.passage_summaries:
            section_label = f"`{p.section}`" if p.section else "_no section_"
            lines.append(f"### Rank {p.rank} — section: {section_label}")
            lines.append(f"- **chunk_id:** `{p.chunk_id}`")
            lines.append(f"- **document_id:** `{p.document_id}`")
            lines.append(f"\n```\n{p.snippet}\n```\n")

    lines.append("---")
    lines.append("\n_Manual relevance review: mark each passage ✓ Relevant / ✗ Not relevant._\n")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main(output_path: Path, top_k: int) -> None:
    client = AsyncOpenAI(api_key=settings.openai_api_key)

    print(f"Running {len(QUESTIONS)} verification queries (top-{top_k} passages each)…\n")

    start = asyncio.get_event_loop().time()
    results: list[QueryResult] = []

    async with _SessionFactory() as session:
        for i, question in enumerate(QUESTIONS, start=1):
            print(f"  Q{i:02d} …", end=" ", flush=True)
            qr = await verify_query(session, client, i, question, k=top_k)
            count = len(qr.passage_summaries) if not qr.error else "ERR"
            print(f"{count} passage(s)")
            results.append(qr)

    elapsed = asyncio.get_event_loop().time() - start

    report = _render_markdown(results, elapsed)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")

    print(f"\nReport written to: {output_path}")
    print(f"Elapsed: {elapsed:.1f}s")

    # Surface any errors clearly
    errors = [r for r in results if r.error]
    if errors:
        print(f"\n⚠️  {len(errors)} query(ies) failed:")
        for r in errors:
            print(f"  Q{r.question_number}: {r.error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Verify Phase 5 retrieval against client-brief queries")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).parent / "verification_report.md",
        help="Path to write the markdown report (default: tests/verification_report.md)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of passages to retrieve per query (default: 5)",
    )
    args = parser.parse_args()

    # psycopg async requires SelectorEventLoop on Windows (ProactorEventLoop is incompatible)
    import sys
    import selectors
    if sys.platform == "win32":
        asyncio.run(
            main(output_path=args.output, top_k=args.top_k),
            loop_factory=lambda: asyncio.SelectorEventLoop(selectors.SelectSelector()),
        )
    else:
        asyncio.run(main(output_path=args.output, top_k=args.top_k))
