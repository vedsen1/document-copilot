# Backend Tests

All commands below are run from the `backend/` directory.

## Unit tests (no DB required)

Fast, fully isolated — safe to run on every change.

```bash
uv run pytest
```

This runs `tests/test_fusion.py`, `tests/test_pgvector_search.py`, and
`tests/test_fulltext_search.py` — 23 tests covering fusion ranking and query
assembly for both search backends.

## Integration tests (live DB + OpenAI required)

Requires a populated corpus and valid credentials in `.env`.

```bash
uv run pytest -m integration -v
```

Tests in `tests/test_retrieval_integration.py` exercise the full hybrid
retrieval stack against real data:

| Test | What it checks |
|------|----------------|
| `test_fulltext_only_returns_passages` | Full-text fallback (no embedding) returns results |
| `test_hybrid_search_returns_ranked_passages` | pgvector + full-text + RRF returns ranked passages |
| `test_hybrid_search_respects_k_limit` | Result count never exceeds requested `k` |
| `test_hybrid_search_nvidia_data_center` | NVDA data center query surfaces relevant chunks |
| `test_empty_corpus_query_returns_result_object` | No match → empty result, not an exception |

## Verification script (live DB + OpenAI required)

Runs all 10 example analyst questions from the client brief and writes a
markdown report you can review manually.

```bash
# writes to tests/verification_report.md by default
uv run python tests/verify_retrieval.py

# custom output path or passage count
uv run python tests/verify_retrieval.py --output /tmp/report.md --top-k 10
```

The report shows the top-k retrieved passages per question (chunk ID, document
ID, section, and a 300-char text snippet). Use it to spot-check retrieval
quality and mark passages as relevant or not.

## Prerequisites for integration tests and verification

- `DATABASE_URL` in `backend/.env` pointing to your Supabase direct connection
- `OPENAI_API_KEY` in `backend/.env`
- Ingested corpus — run the ingest pipeline first:
  ```bash
  uv run python ingest/chunk_and_embed.py
  ```
