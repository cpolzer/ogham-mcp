# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development setup
uv sync --extra all        # Install all extras (postgres, mistral, voyage, gemini)
uv sync --extra dev        # Install test/lint deps only

# Testing
uv run pytest              # Run all tests (skips integration tests by default)
uv run pytest -m "not integration and not postgres_integration"  # Skip live DB tests
uv run pytest tests/test_tools.py  # Run a single test file
uv run pytest tests/test_extraction.py::test_name  # Run a specific test

# Linting
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# CLI (dev)
uv run ogham --help
uv run ogham health
uv run ogham serve --transport sse

# Generate OpenAPI spec
uv run ogham openapi
```

**Integration test markers:**
- `integration` — tests that hit real Supabase + embedding provider
- `postgres_integration` — tests that hit real Postgres

Deselect with `-m "not integration"` or set env vars to run them.

## Architecture

Ogham is an MCP server that provides persistent, searchable memory across AI clients. It exposes MCP tools to store/search/manage memories backed by a vector-enabled Postgres database (Supabase or bare Postgres).

### Request path

```
MCP client
  → tools/memory.py      (MCP tool definitions, input validation)
  → service.py           (orchestration: embed → score → store/search)
  → database.py          (thin facade, delegates to backend singleton)
  → backends/gateway.py  (selects backend based on DATABASE_BACKEND env)
  → backends/supabase.py | backends/postgres.py  (actual SQL/RPC calls)
```

### Key modules

- **`service.py`** — the core intelligence. `store_memory_enriched` runs the full store pipeline (validation → extraction → embedding → importance scoring → store → auto-link). `search_memories_enriched` runs hybrid retrieval + multi-pass re-ranking (temporal, MMR, entity threading, bridge retrieval).
- **`extraction.py`** — parses dates, recurrence patterns, temporal intent, importance scores, and entity salience from raw content without calling an LLM.
- **`database.py`** — module-level functions that delegate to a singleton backend (`get_backend()`). All code outside `backends/` calls this module, not the backend directly.
- **`backends/protocol.py`** — the `DatabaseBackend` Protocol all backends must satisfy.
- **`backends/supabase.py`** — backend via PostgREST (Supabase's HTTP API).
- **`backends/postgres.py`** — backend via `psycopg` connection pool (Neon, self-hosted).
- **`embeddings.py`** — multi-provider embedding (ollama, openai, mistral, voyage, gemini) with batching.
- **`embedding_cache.py`** — in-process LRU cache keyed on content hash.
- **`compression.py`** — rule-based sentence scoring for gist extraction (no LLM).
- **`hooks.py`** — Claude Code lifecycle hooks: `session_start` (recall), `post_tool` (inscribe), `pre_compact`/`post_compact`. Includes secret masking and dedup logic.
- **`config.py`** — pydantic-settings `Settings` wrapped in a lazy proxy so `ogham init` can run before any config exists.
- **`server.py`** — MCP server entry point; runs `fastmcp` in stdio or SSE mode.
- **`cli.py`** — Typer CLI; `ogham` entry point. `ogham-serve` maps to `server.py:main`.

### Database schema

Three schema variants in `sql/`:
- `schema.sql` — Supabase (uses `pgvector` + pg functions callable via PostgREST RPC)
- `schema_postgres.sql` — Neon / self-hosted Postgres
- `schema_selfhost_supabase.sql` — self-hosted Supabase

The critical column is `embedding vector(512)` (default). If using Mistral (1024 dims) you must alter the column before first use.

### Backend selection

`DATABASE_BACKEND=supabase` (default) → `backends/supabase.py`
`DATABASE_BACKEND=postgres` → `backends/postgres.py`

Both implement the same `DatabaseBackend` Protocol. `backends/gateway.py` instantiates the right one and caches it as a module-level singleton in `database.py`.

### Embedding providers

Set via `EMBEDDING_PROVIDER` (default: `ollama`). Each provider has different default dims and optimal similarity thresholds — see `config.py::PROVIDER_DEFAULT_DIMS` and the README configuration table.

### Transport modes

- **stdio** (default) — each MCP client spawns its own process
- **SSE** (`OGHAM_TRANSPORT=sse`) — persistent server on port 8742, all clients share one process and one connection pool
