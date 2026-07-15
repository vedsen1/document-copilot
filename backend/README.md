# Backend

FastAPI service for Document Copilot. Config lives in `app/config.py`; the app entrypoint is `app/main.py`.

## Setup

```bash
cd backend
cp .env.example .env   # fill in Supabase + OpenAI values
uv sync
```

## Run

```bash
uv run uvicorn app.main:app --reload
```

Health check: http://127.0.0.1:8000/health  
API docs: http://127.0.0.1:8000/docs

Or run directly:

```bash
uv run python app/main.py
```

## Migrations

```bash
uv run alembic upgrade head
```

Create a new migration after model changes:

```bash
uv run alembic revision --autogenerate -m "describe change"
```

## Tests & lint

```bash
uv run pytest
uv run ruff check .
```

More detail (Alembic, imports, Jupyter): [docs/guides/backend-setup.md](../docs/guides/backend-setup.md)
