"""Tests for database operations."""

from funnel_optimizer.db import DDL


def test_init_creates_all_tables(db):
    """init_db should create all 6 tables."""
    tables = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    ).fetchall()
    names = [r["name"] for r in tables]
    assert "customers" in names
    assert "briefs" in names
    assert "content" in names
    assert "campaigns" in names
    assert "leads" in names
    assert "campaign_metrics" in names


def test_foreign_keys_enforced(db):
    """Foreign keys should be enabled."""
    row = db.execute("PRAGMA foreign_keys").fetchone()
    assert row[0] == 1


def test_leads_unique_constraint(db, sample_customer):
    """meta_lead_id should be unique — INSERT OR IGNORE should skip duplicates."""
    # Need a campaign first (FK)
    db.execute("INSERT INTO briefs (customer_id, name, project_type, geo, budget_cents) VALUES (1, 'b', 't', 'g', 0)")
    db.execute("INSERT INTO content (brief_id, headline, primary_text) VALUES (1, 'h', 'p')")
    db.execute("INSERT INTO campaigns (content_id, status) VALUES (1, 'active')")
    db.commit()

    db.execute(
        "INSERT INTO leads (campaign_id, meta_lead_id, full_name) VALUES (1, 'lead_x', 'Alice')"
    )
    db.commit()

    # Second insert with same meta_lead_id should be ignored
    db.execute(
        "INSERT OR IGNORE INTO leads (campaign_id, meta_lead_id, full_name) VALUES (1, 'lead_x', 'Bob')"
    )
    db.commit()

    count = db.execute("SELECT COUNT(*) FROM leads WHERE meta_lead_id = 'lead_x'").fetchone()[0]
    assert count == 1

    # Name should still be Alice (not overwritten)
    name = db.execute("SELECT full_name FROM leads WHERE meta_lead_id = 'lead_x'").fetchone()[0]
    assert name == "Alice"


def test_metrics_upsert(db, sample_customer):
    """ON CONFLICT(campaign_id, date) should update existing row."""
    db.execute("INSERT INTO briefs (customer_id, name, project_type, geo, budget_cents) VALUES (1, 'b', 't', 'g', 0)")
    db.execute("INSERT INTO content (brief_id, headline, primary_text) VALUES (1, 'h', 'p')")
    db.execute("INSERT INTO campaigns (content_id, status) VALUES (1, 'active')")
    db.commit()

    # First insert
    db.execute(
        """INSERT INTO campaign_metrics (campaign_id, date, impressions, clicks, spend_cents)
           VALUES (1, '2025-01-15', 100, 5, 500)"""
    )
    db.commit()

    # Upsert with new values
    db.execute(
        """INSERT INTO campaign_metrics (campaign_id, date, impressions, clicks, spend_cents)
           VALUES (1, '2025-01-15', 200, 10, 1000)
           ON CONFLICT(campaign_id, date) DO UPDATE SET
               impressions = excluded.impressions,
               clicks = excluded.clicks,
               spend_cents = excluded.spend_cents,
               updated_at = CURRENT_TIMESTAMP"""
    )
    db.commit()

    row = db.execute("SELECT * FROM campaign_metrics WHERE campaign_id = 1 AND date = '2025-01-15'").fetchone()
    assert row["impressions"] == 200
    assert row["clicks"] == 10
    assert row["spend_cents"] == 1000

    # Should still be just one row
    count = db.execute("SELECT COUNT(*) FROM campaign_metrics").fetchone()[0]
    assert count == 1
