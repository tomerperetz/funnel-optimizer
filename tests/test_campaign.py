"""Tests for campaign pipeline with mocked Meta API."""

from unittest.mock import patch

from rich.console import Console

from funnel_optimizer.models import Brief, Content
from funnel_optimizer.pipeline.content import add_brief, add_content, approve_content


def _setup_approved_content(db):
    """Create a brief with approved content in the DB."""
    add_brief(Brief(name="Test", project_type="Bathroom", geo="DFW", budget_cents=5000), db)
    add_content(Content(brief_id=1, headline="Transform Your Bath", primary_text="Get a free quote"), db)
    approve_content(1, db)


def test_create_campaign_from_content(db, mock_meta_client):
    """Creating a campaign should create all Meta objects and save to DB."""
    _setup_approved_content(db)
    console = Console(quiet=True)

    with patch("funnel_optimizer.pipeline.campaign.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.campaign.get_settings"):

        from funnel_optimizer.pipeline.campaign import create_campaign_from_content
        create_campaign_from_content(1, console, conn=db)

    row = db.execute("SELECT * FROM campaigns WHERE content_id = 1").fetchone()
    assert row is not None
    assert row["meta_campaign_id"] == "camp_123"
    assert row["meta_adset_id"] == "adset_789"
    assert row["meta_ad_id"] == "ad_202"
    assert row["meta_form_id"] == "form_456"
    assert row["status"] == "paused"

    mock_meta_client.create_campaign.assert_called_once()
    mock_meta_client.create_lead_form.assert_called_once()
    mock_meta_client.create_adset.assert_called_once()
    mock_meta_client.create_creative.assert_called_once()
    mock_meta_client.create_ad.assert_called_once()


def test_create_campaign_unapproved_content(db):
    """Should reject unapproved content."""
    add_brief(Brief(name="Test", project_type="Bath", geo="DFW", budget_cents=0), db)
    add_content(Content(brief_id=1, headline="H", primary_text="P"), db)
    console = Console(quiet=True)

    from funnel_optimizer.pipeline.campaign import create_campaign_from_content
    create_campaign_from_content(1, console, conn=db)

    count = db.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    assert count == 0


def test_create_campaign_meta_error(db, mock_meta_client):
    """Meta API error should save error status in DB."""
    _setup_approved_content(db)
    mock_meta_client.create_campaign.side_effect = Exception("API Error: #200")
    console = Console(quiet=True)

    with patch("funnel_optimizer.pipeline.campaign.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.campaign.get_settings"):

        from funnel_optimizer.pipeline.campaign import create_campaign_from_content
        create_campaign_from_content(1, console, conn=db)

    row = db.execute("SELECT * FROM campaigns WHERE content_id = 1").fetchone()
    assert row is not None
    assert row["status"] == "error"
    assert "API Error" in row["error_message"]
