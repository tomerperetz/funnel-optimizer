"""Tests for lead and metrics collection with mocked Meta API."""

from unittest.mock import patch

from rich.console import Console


def _setup_campaign(db, sample_customer):
    """Create a campaign in DB with Meta IDs."""
    db.execute("INSERT INTO briefs (customer_id, name, project_type, geo, budget_cents) VALUES (1, 'B', 'Bath', 'DFW', 5000)")
    db.execute("INSERT INTO content (brief_id, headline, primary_text, status) VALUES (1, 'H', 'P', 'approved')")
    db.execute(
        """INSERT INTO campaigns (content_id, meta_campaign_id, meta_adset_id, meta_ad_id, meta_form_id, status)
           VALUES (1, 'camp_123', 'adset_789', 'ad_202', 'form_456', 'active')"""
    )
    db.commit()


def test_collect_leads(db, mock_meta_client, sample_customer):
    """Should insert new leads and skip duplicates."""
    _setup_campaign(db, sample_customer)
    console = Console(quiet=True)

    with patch("funnel_optimizer.pipeline.leads.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.leads.get_settings"):

        from funnel_optimizer.pipeline.leads import collect_leads
        collect_leads(None, console, conn=db)

    count = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    assert count == 2

    # Run again — should be idempotent
    with patch("funnel_optimizer.pipeline.leads.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.leads.get_settings"):

        collect_leads(None, console, conn=db)

    count_after = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    assert count_after == 2  # No duplicates


def test_collect_metrics(db, mock_meta_client, sample_customer):
    """Should insert metrics and upsert on re-run."""
    _setup_campaign(db, sample_customer)
    console = Console(quiet=True)

    with patch("funnel_optimizer.pipeline.leads.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.leads.get_settings"):

        from funnel_optimizer.pipeline.leads import collect_metrics
        collect_metrics(None, console, conn=db)

    count = db.execute("SELECT COUNT(*) FROM campaign_metrics").fetchone()[0]
    assert count == 2

    # Run again — should upsert, not duplicate
    with patch("funnel_optimizer.pipeline.leads.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.leads.get_settings"):

        collect_metrics(None, console, conn=db)

    count_after = db.execute("SELECT COUNT(*) FROM campaign_metrics").fetchone()[0]
    assert count_after == 2

    row = db.execute("SELECT * FROM campaign_metrics WHERE date = '2025-01-15'").fetchone()
    assert row["impressions"] == 1000
    assert row["spend_cents"] == 2500


def test_collect_leads_specific_campaign(db, mock_meta_client, sample_customer):
    """Should only collect from the specified campaign."""
    _setup_campaign(db, sample_customer)
    console = Console(quiet=True)

    with patch("funnel_optimizer.pipeline.leads.MetaAdsClient", return_value=mock_meta_client), \
         patch("funnel_optimizer.pipeline.leads.get_settings"):

        from funnel_optimizer.pipeline.leads import collect_leads
        collect_leads(1, console, conn=db)

    count = db.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    assert count == 2
