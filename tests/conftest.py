"""Shared test fixtures."""

import sqlite3
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from funnel_optimizer.db import DDL


@pytest.fixture
def db(tmp_path):
    """In-memory-like SQLite database (on disk in tmp for path compatibility)."""
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    yield conn
    conn.close()


@pytest.fixture
def sample_customer(db):
    """Create a sample customer for tests."""
    db.execute(
        "INSERT INTO customers (name, meta_page_id, meta_page_name, meta_page_access_token, status) VALUES (?, ?, ?, ?, ?)",
        ("Test Client", "123456789", "Test Page", "test_token_abc123", "active"),
    )
    db.commit()
    return db.execute("SELECT * FROM customers WHERE id = 1").fetchone()


@pytest.fixture
def mock_meta_client():
    """Mocked MetaAdsClient that returns realistic fake IDs."""
    client = MagicMock()
    client.create_campaign.return_value = {"id": "camp_123"}
    client.create_lead_form.return_value = {"id": "form_456"}
    client.create_adset.return_value = {"id": "adset_789"}
    client.create_creative.return_value = {"id": "creative_101"}
    client.create_ad.return_value = {"id": "ad_202"}
    client.update_campaign_status.return_value = None
    client.update_adset_status.return_value = None
    client.get_leads.return_value = [
        {
            "id": "lead_001",
            "created_time": "2025-01-15T10:00:00+0000",
            "full_name": "John Doe",
            "email": "john@example.com",
            "phone": "12145551234",
            "form_data": {"full_name": "John Doe", "email": "john@example.com"},
        },
        {
            "id": "lead_002",
            "created_time": "2025-01-15T11:00:00+0000",
            "full_name": "Jane Smith",
            "email": "jane@example.com",
            "phone": "12145555678",
            "form_data": {"full_name": "Jane Smith", "email": "jane@example.com"},
        },
    ]
    client.get_campaign_insights.return_value = [
        {
            "date": "2025-01-15",
            "impressions": 1000,
            "clicks": 50,
            "spend_cents": 2500,
            "leads_count": 3,
            "cpl_cents": 833,
        },
        {
            "date": "2025-01-16",
            "impressions": 1200,
            "clicks": 60,
            "spend_cents": 3000,
            "leads_count": 4,
            "cpl_cents": 750,
        },
    ]
    return client
