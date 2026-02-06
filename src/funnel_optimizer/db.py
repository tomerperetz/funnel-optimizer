"""SQLite database setup and connection management."""

import sqlite3
from pathlib import Path

from funnel_optimizer.config import get_settings

DDL = """
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    meta_page_id TEXT NOT NULL,
    meta_page_name TEXT,
    meta_page_access_token TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS briefs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL REFERENCES customers(id),
    name TEXT NOT NULL,
    project_type TEXT NOT NULL,
    geo TEXT NOT NULL,
    budget_cents INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    brief_id INTEGER NOT NULL REFERENCES briefs(id),
    headline TEXT NOT NULL,
    primary_text TEXT NOT NULL,
    image_url TEXT,
    cta TEXT NOT NULL DEFAULT 'LEARN_MORE',
    targeting_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'draft',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaigns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_id INTEGER NOT NULL REFERENCES content(id),
    meta_campaign_id TEXT,
    meta_adset_id TEXT,
    meta_ad_id TEXT,
    meta_form_id TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    meta_lead_id TEXT NOT NULL UNIQUE,
    full_name TEXT,
    email TEXT,
    phone TEXT,
    form_data_json TEXT NOT NULL DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS campaign_metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id INTEGER NOT NULL REFERENCES campaigns(id),
    date TEXT NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0,
    spend_cents INTEGER NOT NULL DEFAULT 0,
    leads_count INTEGER NOT NULL DEFAULT 0,
    cpl_cents INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(campaign_id, date)
);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    """Open a connection with row_factory set."""
    if db_path is None:
        db_path = get_settings().db_abs_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(db_path: Path | None = None) -> None:
    """Create all tables if they don't exist."""
    conn = get_connection(db_path)
    conn.executescript(DDL)
    _run_migrations(conn)
    conn.close()


def _run_migrations(conn: sqlite3.Connection) -> None:
    """Run any pending schema migrations."""
    # Migration: Add meta_page_access_token to customers if missing
    cursor = conn.execute("PRAGMA table_info(customers)")
    columns = [row[1] for row in cursor.fetchall()]
    if "meta_page_access_token" not in columns:
        conn.execute("ALTER TABLE customers ADD COLUMN meta_page_access_token TEXT")
        conn.commit()


def table_counts(db_path: Path | None = None) -> dict[str, int]:
    """Return row count for each table."""
    conn = get_connection(db_path)
    tables = ["customers", "briefs", "content", "campaigns", "leads", "campaign_metrics"]
    counts = {}
    for t in tables:
        row = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()  # noqa: S608
        counts[t] = row[0]
    conn.close()
    return counts
