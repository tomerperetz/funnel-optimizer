"""Tests for campaign init pipeline."""

import json
from pathlib import Path

import pytest

from funnel_optimizer.models import CampaignConfig
from funnel_optimizer.pipeline.init_campaign import (
    create_brief_from_config,
    create_content_variants,
    dollars_to_cents,
    find_or_create_customer,
    generate_campaign_plan_report,
    init_campaign,
)


SAMPLE_CONFIG = {
    "customer": {"name": "Ace Plumbing", "website_url": "https://aceplumbing.com"},
    "service": {"category": "plumbing", "avg_ticket_dollars": 350},
    "geo": {"type": "city", "value": "Dallas, TX", "location_type": "living_in"},
    "budget": {
        "daily_dollars": 50,
        "monthly_cap_dollars": 1500,
        "target_cpl_dollars": 25,
        "bid_strategy": "lowest_cost",
    },
    "schedule": {
        "operating_days": ["Mon", "Tue", "Wed", "Thu", "Fri"],
        "operating_hours": {"start": "08:00", "end": "18:00", "timezone": "America/Chicago"},
    },
    "creative": {
        "value_propositions": ["24/7 Emergency Plumbing", "Licensed & Insured Plumbers"],
        "cta": "GET_QUOTE",
        "brand_voice": "professional",
        "language": "en",
    },
    "lead_form": {"questions": ["full_name", "phone_number", "email"]},
    "targeting": {"age_min": 25, "age_max": 65},
    "experiment": {"num_variants": 2, "primary_metric": "cpl", "min_effect_pct": 25},
    "context": {},
    "_meta": {"form_version": "1.0", "generated_by": "test"},
}


def test_dollars_to_cents():
    assert dollars_to_cents(50.0) == 5000
    assert dollars_to_cents(25.99) == 2599
    assert dollars_to_cents(0) == 0
    assert dollars_to_cents(0.01) == 1


def test_campaign_config_validation():
    config = CampaignConfig.model_validate(SAMPLE_CONFIG)
    assert config.customer.name == "Ace Plumbing"
    assert config.budget.daily_dollars == 50
    assert config.creative.cta == "GET_QUOTE"
    assert len(config.creative.value_propositions) == 2


def test_campaign_config_rejects_single_vp():
    bad = {**SAMPLE_CONFIG, "creative": {**SAMPLE_CONFIG["creative"], "value_propositions": ["Only one"]}}
    with pytest.raises(Exception, match="At least 2 value propositions"):
        CampaignConfig.model_validate(bad)


def test_find_or_create_customer_creates_new(db):
    config = CampaignConfig.model_validate(SAMPLE_CONFIG)
    customer_id = find_or_create_customer(config, db)
    assert customer_id == 1

    row = db.execute("SELECT * FROM customers WHERE id = ?", (customer_id,)).fetchone()
    assert row["name"] == "Ace Plumbing"
    assert row["meta_page_id"] == "pending"


def test_find_or_create_customer_finds_existing(db, sample_customer):
    # sample_customer is "Test Client"
    config_data = {**SAMPLE_CONFIG, "customer": {"name": "Test Client"}}
    config = CampaignConfig.model_validate(config_data)
    customer_id = find_or_create_customer(config, db)
    assert customer_id == sample_customer["id"]


def test_find_or_create_customer_case_insensitive(db, sample_customer):
    config_data = {**SAMPLE_CONFIG, "customer": {"name": "test client"}}
    config = CampaignConfig.model_validate(config_data)
    customer_id = find_or_create_customer(config, db)
    assert customer_id == sample_customer["id"]


def test_create_brief_from_config(db, sample_customer):
    config = CampaignConfig.model_validate(SAMPLE_CONFIG)
    brief_id = create_brief_from_config(sample_customer["id"], config, db)
    assert brief_id == 1

    row = db.execute("SELECT * FROM briefs WHERE id = ?", (brief_id,)).fetchone()
    assert row["project_type"] == "plumbing"
    assert row["geo"] == "Dallas, TX"
    assert row["budget_cents"] == 5000
    assert row["config_json"] is not None
    # Verify stored config round-trips
    stored = json.loads(row["config_json"])
    assert stored["customer"]["name"] == "Ace Plumbing"


def test_create_content_variants(db, sample_customer):
    config = CampaignConfig.model_validate(SAMPLE_CONFIG)
    db.execute(
        "INSERT INTO briefs (customer_id, name, project_type, geo, budget_cents) VALUES (?, ?, ?, ?, ?)",
        (sample_customer["id"], "test", "plumbing", "Dallas", 5000),
    )
    db.commit()

    content_ids = create_content_variants(1, config, db)
    assert len(content_ids) == 2

    rows = db.execute("SELECT * FROM content ORDER BY id").fetchall()
    assert rows[0]["headline"] == "24/7 Emergency Plumbing"
    assert rows[1]["headline"] == "Licensed & Insured Plumbers"
    assert rows[0]["cta"] == "GET_QUOTE"
    assert rows[0]["status"] == "draft"

    # Check targeting JSON
    targeting = json.loads(rows[0]["targeting_json"])
    assert targeting["geo_value"] == "Dallas, TX"
    assert targeting["age_min"] == 25


def test_init_campaign_full(db, tmp_path):
    """End-to-end: config file -> DB records + report."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(SAMPLE_CONFIG))

    result = init_campaign(str(config_file), db)

    assert result.customer_id >= 1
    assert result.brief_id >= 1
    assert len(result.content_ids) == 2
    assert Path(result.report_path).exists()
    assert result.config.customer.name == "Ace Plumbing"

    # Verify DB state
    customer = db.execute("SELECT * FROM customers WHERE id = ?", (result.customer_id,)).fetchone()
    assert customer["name"] == "Ace Plumbing"

    brief = db.execute("SELECT * FROM briefs WHERE id = ?", (result.brief_id,)).fetchone()
    assert brief["budget_cents"] == 5000

    content = db.execute("SELECT * FROM content WHERE brief_id = ?", (result.brief_id,)).fetchall()
    assert len(content) == 2

    # Report contains key info
    report_html = Path(result.report_path).read_text()
    assert "Ace Plumbing" in report_html
    assert "plumbing" in report_html
    assert "Dallas" in report_html
