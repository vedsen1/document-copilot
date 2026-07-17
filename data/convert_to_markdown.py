"""
Convert SEC 10-K HTML filings -> Markdown using docling.

Reads downloads/manifest.json, converts each .htm file, and writes the result
to the matching path under markdown/, keeping the same year/ structure.
A manifest.json is written to markdown/ on completion.

Usage (from repo root):
    uv run --project backend data/convert_to_markdown.py

Skip already-converted files with --skip-existing (default: overwrite).
Process specific tickers only with --tickers AAPL MSFT.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent
DOWNLOADS_DIR = DATA_DIR / "downloads"
MARKDOWN_DIR = DATA_DIR / "markdown"
DOWNLOADS_MANIFEST = DOWNLOADS_DIR / "manifest.json"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip files that already have a corresponding .md output.",
    )
    p.add_argument(
        "--tickers",
        nargs="+",
        metavar="TICKER",
        help="Only process filings for these tickers (e.g. AAPL MSFT).",
    )
    return p.parse_args()


def load_manifest() -> dict:
    if not DOWNLOADS_MANIFEST.exists():
        sys.exit(
            f"Manifest not found: {DOWNLOADS_MANIFEST}\n"
            "Run data/download.py first."
        )
    with DOWNLOADS_MANIFEST.open(encoding="utf-8") as f:
        return json.load(f)


def output_path(local_path: str) -> Path:
    """Map a downloads/ local_path (e.g. '2024\aapl_...htm') to markdown/<year>/<stem>.md."""
    rel = Path(local_path)
    return MARKDOWN_DIR / rel.parent / (rel.stem + ".md")


def convert_filing(html_path: Path, md_path: Path, converter, input_format) -> bool:
    """Convert one HTML file to Markdown. Returns True on success."""
    if not html_path.exists():
        print(f"  [SKIP] Source file missing: {html_path}")
        return False

    try:
        raw = html_path.read_bytes()
        try:
            html_content = raw.decode("utf-8")
        except UnicodeDecodeError:
            html_content = raw.decode("latin-1")

        result = converter.convert_string(
            html_content,
            format=input_format,
            name=html_path.name,
        )
        markdown = result.document.export_to_markdown()

        md_path.parent.mkdir(parents=True, exist_ok=True)
        md_path.write_text(markdown, encoding="utf-8")
        return True
    except Exception as exc:
        print(f"  [ERROR] {html_path.name}: {exc}")
        return False


def main() -> None:
    args = parse_args()

    try:
        # pyrefly: ignore [missing-import]
        from docling.datamodel.base_models import InputFormat
        # pyrefly: ignore [missing-import]
        from docling.document_converter import DocumentConverter
    except ImportError:
        sys.exit(
            "docling is not importable.\n"
            "Run this script via:  uv run --project backend data/convert_to_markdown.py"
        )

    manifest = load_manifest()
    filings = manifest["filings"]

    if args.tickers:
        tickers_upper = {t.upper() for t in args.tickers}
        filings = [f for f in filings if f["ticker"] in tickers_upper]
        if not filings:
            sys.exit(f"No filings found for tickers: {args.tickers}")

    MARKDOWN_DIR.mkdir(parents=True, exist_ok=True)

    print("Initialising docling DocumentConverter...")
    converter = DocumentConverter()

    results: list[dict] = []
    converted = skipped = failed = 0
    total = len(filings)

    for i, filing in enumerate(filings, 1):
        local_path = filing["local_path"]
        html_path = DOWNLOADS_DIR / Path(local_path)
        md_path = output_path(local_path)

        print(
            f"[{i}/{total}] {filing['ticker']} {filing['filing_date']}"
            f"  ->  {md_path.relative_to(DATA_DIR)}"
        )

        if args.skip_existing and md_path.exists():
            print("  [SKIP] Already converted.")
            skipped += 1
            results.append({**filing, "markdown_path": str(md_path.relative_to(MARKDOWN_DIR))})
            continue

        t0 = time.monotonic()
        ok = convert_filing(html_path, md_path, converter, InputFormat.HTML)
        elapsed = time.monotonic() - t0

        if ok:
            converted += 1
            size_kb = md_path.stat().st_size // 1024
            print(f"  [OK] {size_kb} KB  ({elapsed:.1f}s)")
            results.append({**filing, "markdown_path": str(md_path.relative_to(MARKDOWN_DIR))})
        else:
            failed += 1

    out_manifest = {
        "source": manifest.get("source", "SEC EDGAR"),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "form": manifest.get("form", "10-K"),
        "converted_count": converted,
        "skipped_count": skipped,
        "failed_count": failed,
        "filings": results,
    }
    manifest_path = MARKDOWN_DIR / "manifest.json"
    manifest_path.write_text(json.dumps(out_manifest, indent=2) + "\n", encoding="utf-8")

    print()
    print(f"Done. converted={converted}  skipped={skipped}  failed={failed}")
    print(f"Manifest: {manifest_path}")


if __name__ == "__main__":
    main()
