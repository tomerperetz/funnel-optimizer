"""CRUD operations for customers, briefs, and content."""

import json
import sqlite3
from pathlib import Path

from funnel_optimizer.db import get_connection
from funnel_optimizer.models import Brief, Content, Customer


# --- Customers ---


def add_customer(customer: Customer, conn: sqlite3.Connection | None = None) -> int:
    """Insert a customer and return its ID."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.execute(
        "INSERT INTO customers (name, meta_page_id, meta_page_name, status) VALUES (?, ?, ?, ?)",
        (customer.name, customer.meta_page_id, customer.meta_page_name, customer.status),
    )
    conn.commit()
    row_id = cur.lastrowid
    if close:
        conn.close()
    return row_id


def list_customers(conn: sqlite3.Connection | None = None) -> list[Customer]:
    """Return all customers."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    rows = conn.execute("SELECT * FROM customers ORDER BY id").fetchall()
    result = [Customer(**dict(r)) for r in rows]
    if close:
        conn.close()
    return result


def get_customer(customer_id: int, conn: sqlite3.Connection | None = None) -> Customer | None:
    """Return a customer by ID."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    row = conn.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    result = Customer(**dict(row)) if row else None
    if close:
        conn.close()
    return result


# --- Briefs ---


def add_brief(brief: Brief, conn: sqlite3.Connection | None = None) -> int:
    """Insert a brief and return its ID."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.execute(
        "INSERT INTO briefs (customer_id, name, project_type, geo, budget_cents, status) VALUES (?, ?, ?, ?, ?, ?)",
        (brief.customer_id, brief.name, brief.project_type, brief.geo, brief.budget_cents, brief.status),
    )
    conn.commit()
    row_id = cur.lastrowid
    if close:
        conn.close()
    return row_id


def list_briefs(conn: sqlite3.Connection | None = None) -> list[Brief]:
    """Return all briefs."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    rows = conn.execute("SELECT * FROM briefs ORDER BY id").fetchall()
    result = [Brief(**dict(r)) for r in rows]
    if close:
        conn.close()
    return result


def get_brief(brief_id: int, conn: sqlite3.Connection | None = None) -> Brief | None:
    """Return a brief by ID."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    row = conn.execute("SELECT * FROM briefs WHERE id = ?", (brief_id,)).fetchone()
    result = Brief(**dict(row)) if row else None
    if close:
        conn.close()
    return result


# --- Content ---


def add_content(content: Content, conn: sqlite3.Connection | None = None) -> int:
    """Insert content and return its ID."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.execute(
        """INSERT INTO content (brief_id, headline, primary_text, image_url, cta, targeting_json, status)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            content.brief_id,
            content.headline,
            content.primary_text,
            content.image_url,
            content.cta,
            content.targeting_json,
            content.status,
        ),
    )
    conn.commit()
    row_id = cur.lastrowid
    if close:
        conn.close()
    return row_id


def list_content(brief_id: int | None = None, conn: sqlite3.Connection | None = None) -> list[Content]:
    """Return content, optionally filtered by brief_id."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    if brief_id is not None:
        rows = conn.execute("SELECT * FROM content WHERE brief_id = ? ORDER BY id", (brief_id,)).fetchall()
    else:
        rows = conn.execute("SELECT * FROM content ORDER BY id").fetchall()
    result = [Content(**dict(r)) for r in rows]
    if close:
        conn.close()
    return result


def get_content(content_id: int, conn: sqlite3.Connection | None = None) -> Content | None:
    """Return content by ID."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    row = conn.execute("SELECT * FROM content WHERE id = ?", (content_id,)).fetchone()
    result = Content(**dict(row)) if row else None
    if close:
        conn.close()
    return result


def approve_content(content_id: int, conn: sqlite3.Connection | None = None) -> bool:
    """Mark content as approved. Returns True if found."""
    close = conn is None
    if conn is None:
        conn = get_connection()
    cur = conn.execute(
        "UPDATE content SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (content_id,),
    )
    conn.commit()
    changed = cur.rowcount > 0
    if close:
        conn.close()
    return changed


def load_from_json(file_path: str, conn: sqlite3.Connection | None = None) -> dict[str, int]:
    """Load briefs and content from a JSON file. Returns counts of inserted items."""
    close = conn is None
    if conn is None:
        conn = get_connection()

    data = json.loads(Path(file_path).read_text())
    briefs_added = 0
    content_added = 0

    for item in data if isinstance(data, list) else [data]:
        brief = Brief(
            customer_id=item["customer_id"],
            name=item["name"],
            project_type=item["project_type"],
            geo=item["geo"],
            budget_cents=item.get("budget_cents", 0),
            status=item.get("status", "draft"),
        )
        brief_id = add_brief(brief, conn)
        briefs_added += 1

        for c in item.get("content", []):
            content = Content(
                brief_id=brief_id,
                headline=c["headline"],
                primary_text=c["primary_text"],
                image_url=c.get("image_url"),
                cta=c.get("cta", "LEARN_MORE"),
                targeting_json=json.dumps(c.get("targeting", {})),
                status=c.get("status", "draft"),
            )
            add_content(content, conn)
            content_added += 1

    if close:
        conn.close()
    return {"briefs": briefs_added, "content": content_added}
