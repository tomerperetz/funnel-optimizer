---
name: pipeline-patterns
description: Config, error handling, logging, CLI, testing, and file organization conventions for the Funnel Optimizer product
---

# Pipeline Patterns Skill

## Product Context

Funnel Optimizer is a standalone SaaS product for lead gen call centers (any service vertical). Deployed serverless. Operators manage multiple end-client customers via web dashboard. Code should be production-grade. The web interface and multi-customer support are coming — write code that doesn't fight that direction. No hardcoded verticals, project types, or geos.

## Config Loading

```python
from funnel_optimizer.config import get_settings
settings = get_settings()  # Reads .env, FO_ prefix
```

## Error Handling

Pipeline operations catch exceptions, log them, and store in DB. This pattern serves both human debugging and future AI agent learning:

```python
try:
    result = client.create_campaign(...)
except Exception as e:
    logger.exception("Failed to create campaign")
    conn.execute("UPDATE campaigns SET status='error', error_message=? WHERE id=?", (str(e), id))
    conn.commit()
```

## Logging

```python
import logging
logger = logging.getLogger(__name__)
```

All pipeline modules use standard Python logging.

## Connection Ownership

Functions that receive a `conn` parameter don't close it. Functions that open their own connection close it. This pattern enables both standalone CLI usage and future connection pooling:

```python
def do_something(conn: sqlite3.Connection | None = None) -> None:
    own_conn = conn is None
    if conn is None:
        conn = get_connection()
    try:
        # ... work ...
    finally:
        if own_conn:
            conn.close()
```

## CLI Conventions

The CLI is a dev/ops tool, not the user-facing interface. Call center operators will use a web UI.

- Typer app with subcommand groups: `db`, `content`, `campaign`, `leads`
- Rich console for formatted output (tables, colors)
- Lazy imports for pipeline modules (imported inside command functions)
- Exit code 1 on errors via `raise typer.Exit(1)`

## Pipeline Function Design

Pipeline functions should be **callable from both CLI and web API**:
- Accept data as parameters (not from stdin/prompts)
- Return results (don't just print)
- Accept optional `conn` for connection management
- Use `Console` for CLI output, but don't depend on it for logic

## Testing Strategy

```python
@pytest.fixture
def db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    yield conn
    conn.close()
```

- Pass `conn=db` directly to pipeline functions
- Mock MetaAdsClient, not get_connection
- Test idempotency for all collection operations

## File Organization

- `clients/` — Thin API wrappers (HTTP only, no business logic)
- `pipeline/` — Business logic (reads DB, calls clients, writes DB)
- `models.py` — Pydantic models (validation, serialization)
- `db.py` — Connection + DDL (no business logic)
- `config.py` — Settings (no business logic)
- `cli.py` — CLI interface (dev/ops tool, calls pipeline modules)
- Future: `api/` — Web API endpoints (FastAPI, calls same pipeline modules)

## Key Design Decisions

1. **DB is the integration layer** — blocks read/write DB, never call each other
2. **Campaigns always PAUSED** — explicit activation required (safety for humans and agents)
3. **Idempotent collection** — safe to run repeatedly
4. **Money in cents** — no floating point for money
5. **Errors stored in DB** — for human debugging and agent learning
6. **Pipeline functions are framework-agnostic** — work from CLI, web API, or agent orchestrator
