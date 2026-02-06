"""Lead and metrics collection — idempotent ingestion from Meta."""

import json
import logging
import sqlite3

from rich.console import Console

from funnel_optimizer.clients.meta_ads import MetaAdsClient
from funnel_optimizer.config import get_settings
from funnel_optimizer.db import get_connection

logger = logging.getLogger(__name__)


def _get_campaigns(campaign_id: int | None, conn: sqlite3.Connection) -> list[dict]:
    """Get campaigns to collect from, including customer token. Filters to those with form/campaign IDs."""
    base_query = """
        SELECT ca.*, cu.meta_page_access_token
        FROM campaigns ca
        JOIN content co ON ca.content_id = co.id
        JOIN briefs b ON co.brief_id = b.id
        JOIN customers cu ON b.customer_id = cu.id
        WHERE ca.meta_form_id IS NOT NULL
    """
    if campaign_id is not None:
        rows = conn.execute(
            base_query + " AND ca.id = ?",
            (campaign_id,),
        ).fetchall()
    else:
        rows = conn.execute(
            base_query + " AND ca.status IN ('active', 'paused')"
        ).fetchall()
    return [dict(r) for r in rows]


def collect_leads(
    campaign_id: int | None, console: Console, conn: sqlite3.Connection | None = None
) -> None:
    """Collect leads from Meta for campaigns. Idempotent via INSERT OR IGNORE."""
    own_conn = conn is None
    if conn is None:
        conn = get_connection()
    campaigns = _get_campaigns(campaign_id, conn)
    if not campaigns:
        console.print("[dim]No campaigns with lead forms to collect from.[/dim]")
        if own_conn:
            conn.close()
        return

    settings = get_settings()
    total_new = 0

    for camp in campaigns:
        access_token = camp.get("meta_page_access_token")
        if not access_token:
            console.print(f"  [yellow]Campaign #{camp['id']}: No access token, skipping[/yellow]")
            continue

        try:
            client = MetaAdsClient(settings, access_token=access_token)
            leads = client.get_leads(camp["meta_form_id"])
            new_count = 0
            for lead in leads:
                cur = conn.execute(
                    """INSERT OR IGNORE INTO leads
                       (campaign_id, meta_lead_id, full_name, email, phone, form_data_json)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        camp["id"],
                        lead["id"],
                        lead.get("full_name", ""),
                        lead.get("email", ""),
                        lead.get("phone", ""),
                        json.dumps(lead.get("form_data", {})),
                    ),
                )
                if cur.rowcount > 0:
                    new_count += 1
            conn.commit()
            total_new += new_count
            console.print(
                f"  Campaign #{camp['id']}: {new_count} new lead(s) "
                f"(of {len(leads)} total from Meta)"
            )
        except Exception as e:
            logger.exception("Failed collecting leads for campaign %d", camp["id"])
            console.print(f"  [red]Campaign #{camp['id']}: {e}[/red]")

    console.print(f"[green]Collected {total_new} new lead(s) total[/green]")
    if own_conn:
        conn.close()


def collect_metrics(
    campaign_id: int | None, console: Console, conn: sqlite3.Connection | None = None
) -> None:
    """Collect daily metrics from Meta. Upserts via ON CONFLICT."""
    own_conn = conn is None
    if conn is None:
        conn = get_connection()
    campaigns = _get_campaigns(campaign_id, conn)
    if not campaigns:
        console.print("[dim]No campaigns to collect metrics for.[/dim]")
        if own_conn:
            conn.close()
        return

    settings = get_settings()
    total_days = 0

    for camp in campaigns:
        if not camp.get("meta_campaign_id"):
            continue

        access_token = camp.get("meta_page_access_token")
        if not access_token:
            console.print(f"  [yellow]Campaign #{camp['id']}: No access token, skipping[/yellow]")
            continue

        try:
            client = MetaAdsClient(settings, access_token=access_token)
            insights = client.get_campaign_insights(camp["meta_campaign_id"])
            for day in insights:
                conn.execute(
                    """INSERT INTO campaign_metrics
                       (campaign_id, date, impressions, clicks, spend_cents, leads_count, cpl_cents)
                       VALUES (?, ?, ?, ?, ?, ?, ?)
                       ON CONFLICT(campaign_id, date) DO UPDATE SET
                           impressions = excluded.impressions,
                           clicks = excluded.clicks,
                           spend_cents = excluded.spend_cents,
                           leads_count = excluded.leads_count,
                           cpl_cents = excluded.cpl_cents,
                           updated_at = CURRENT_TIMESTAMP""",
                    (
                        camp["id"],
                        day["date"],
                        day["impressions"],
                        day["clicks"],
                        day["spend_cents"],
                        day["leads_count"],
                        day["cpl_cents"],
                    ),
                )
            conn.commit()
            total_days += len(insights)
            console.print(f"  Campaign #{camp['id']}: {len(insights)} day(s) of metrics")
        except Exception as e:
            logger.exception("Failed collecting metrics for campaign %d", camp["id"])
            console.print(f"  [red]Campaign #{camp['id']}: {e}[/red]")

    console.print(f"[green]Collected {total_days} day(s) of metrics total[/green]")
    if own_conn:
        conn.close()
