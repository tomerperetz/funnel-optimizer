"""Campaign creation and management — content to Meta campaign stack."""

import json
import logging
import sqlite3

from rich.console import Console
from rich.table import Table

from funnel_optimizer.clients.meta_ads import MetaAdsClient
from funnel_optimizer.config import get_settings
from funnel_optimizer.db import get_connection
from funnel_optimizer.pipeline.content import get_brief, get_content, get_customer

logger = logging.getLogger(__name__)


def _get_client(access_token: str) -> MetaAdsClient:
    """Get Meta API client with a customer's page token."""
    return MetaAdsClient(get_settings(), access_token=access_token)


def create_campaign_from_content(
    content_id: int, console: Console, conn: sqlite3.Connection | None = None
) -> None:
    """Create a full Meta campaign stack from approved content (always PAUSED)."""
    own_conn = conn is None
    if conn is None:
        conn = get_connection()

    content = get_content(content_id, conn)
    if not content:
        console.print(f"[red]Content #{content_id} not found[/red]")
        if own_conn:
            conn.close()
        return
    if content.status != "approved":
        console.print(f"[red]Content #{content_id} is '{content.status}', must be 'approved'[/red]")
        if own_conn:
            conn.close()
        return

    brief = get_brief(content.brief_id, conn)
    if not brief:
        console.print(f"[red]Brief #{content.brief_id} not found[/red]")
        if own_conn:
            conn.close()
        return

    customer = get_customer(brief.customer_id, conn)
    if not customer:
        console.print(f"[red]Customer #{brief.customer_id} not found[/red]")
        if own_conn:
            conn.close()
        return

    if not customer.meta_page_access_token:
        console.print(f"[red]Customer #{brief.customer_id} has no access token. Run: funnel auth start[/red]")
        if own_conn:
            conn.close()
        return

    settings = get_settings()
    # Use customer's page token for API calls
    client = MetaAdsClient(settings, access_token=customer.meta_page_access_token)
    import time
    timestamp = int(time.time())
    campaign_name = f"{customer.name} - {brief.project_type} - {brief.geo} - {brief.name} - {timestamp}"
    page_id = customer.meta_page_id

    try:
        meta_campaign = client.create_campaign(name=campaign_name)
        console.print(f"  Meta campaign: {meta_campaign['id']}")

        form = client.create_lead_form(name=f"{campaign_name} - Lead Form", page_id=page_id)
        console.print(f"  Lead form: {form['id']}")

        targeting = json.loads(content.targeting_json)
        adset = client.create_adset(
            campaign_id=meta_campaign["id"],
            name=f"{campaign_name} - AdSet",
            daily_budget_cents=brief.budget_cents,
            targeting=targeting,
            page_id=page_id,
        )
        console.print(f"  Ad set: {adset['id']}")

        # Upload image if provided
        image_hash = ""
        if content.image_url:
            console.print(f"  Uploading image...")
            if content.image_url.startswith(("http://", "https://")):
                image_hash = client.upload_image_from_url(content.image_url)
            else:
                image_hash = client.upload_image(content.image_url)
            console.print(f"  Image hash: {image_hash}")

        creative = client.create_creative(
            name=f"{campaign_name} - Creative",
            page_id=page_id,
            headline=content.headline,
            primary_text=content.primary_text,
            cta=content.cta,
            form_id=form["id"],
            image_hash=image_hash,
        )
        console.print(f"  Creative: {creative['id']}")

        ad = client.create_ad(
            adset_id=adset["id"],
            creative_id=creative["id"],
            name=f"{campaign_name} - Ad",
        )
        console.print(f"  Ad: {ad['id']}")

        conn.execute(
            """INSERT INTO campaigns
               (content_id, meta_campaign_id, meta_adset_id, meta_ad_id, meta_form_id, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (content_id, meta_campaign["id"], adset["id"], ad["id"], form["id"], "paused"),
        )
        conn.commit()
        campaign_row = conn.execute(
            "SELECT id FROM campaigns WHERE meta_campaign_id = ?", (meta_campaign["id"],)
        ).fetchone()
        console.print(f"[green]Campaign #{campaign_row['id']} created (PAUSED)[/green]")

    except Exception as e:
        error_msg = str(e)
        logger.exception("Failed to create campaign from content %d", content_id)
        conn.execute(
            """INSERT INTO campaigns (content_id, status, error_message)
               VALUES (?, 'error', ?)""",
            (content_id, error_msg),
        )
        conn.commit()
        console.print(f"[red]Campaign creation failed: {error_msg}[/red]")
    finally:
        if own_conn:
            conn.close()


def list_campaigns_cli(console: Console, conn: sqlite3.Connection | None = None) -> None:
    """Display all campaigns in a table."""
    own_conn = conn is None
    if conn is None:
        conn = get_connection()
    rows = conn.execute(
        """SELECT c.id, c.content_id, c.meta_campaign_id, c.status, c.error_message,
                  co.headline, b.name as brief_name
           FROM campaigns c
           JOIN content co ON c.content_id = co.id
           JOIN briefs b ON co.brief_id = b.id
           ORDER BY c.id"""
    ).fetchall()
    if own_conn:
        conn.close()

    if not rows:
        console.print("[dim]No campaigns yet.[/dim]")
        return

    table = Table(title="Campaigns")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Brief")
    table.add_column("Headline")
    table.add_column("Meta ID")
    table.add_column("Status")
    table.add_column("Error")

    for r in rows:
        status_style = {"active": "green", "paused": "yellow", "error": "red"}.get(r["status"], "dim")
        table.add_row(
            str(r["id"]),
            r["brief_name"],
            r["headline"],
            r["meta_campaign_id"] or "-",
            f"[{status_style}]{r['status']}[/{status_style}]",
            (r["error_message"] or "")[:40],
        )
    console.print(table)


def _update_campaign_status(
    campaign_id: int, target_status: str, console: Console, conn: sqlite3.Connection | None = None
) -> None:
    """Set campaign status on Meta and in DB."""
    own_conn = conn is None
    if conn is None:
        conn = get_connection()
    row = conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if not row:
        console.print(f"[red]Campaign #{campaign_id} not found[/red]")
        if own_conn:
            conn.close()
        return

    meta_campaign_id = row["meta_campaign_id"]
    if not meta_campaign_id:
        console.print(f"[red]Campaign #{campaign_id} has no Meta campaign ID[/red]")
        if own_conn:
            conn.close()
        return

    # Get customer token for this campaign
    customer_row = conn.execute(
        """SELECT cu.meta_page_access_token
           FROM campaigns ca
           JOIN content co ON ca.content_id = co.id
           JOIN briefs b ON co.brief_id = b.id
           JOIN customers cu ON b.customer_id = cu.id
           WHERE ca.id = ?""",
        (campaign_id,),
    ).fetchone()

    access_token = customer_row["meta_page_access_token"] if customer_row else None
    if not access_token:
        console.print(f"[red]No access token for campaign #{campaign_id}'s customer[/red]")
        if own_conn:
            conn.close()
        return

    meta_status = "ACTIVE" if target_status == "active" else "PAUSED"
    try:
        client = _get_client(access_token=access_token)
        client.update_campaign_status(meta_campaign_id, meta_status)
        if row["meta_adset_id"]:
            client.update_adset_status(row["meta_adset_id"], meta_status)
        conn.execute(
            "UPDATE campaigns SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (target_status, campaign_id),
        )
        conn.commit()
        console.print(f"[green]Campaign #{campaign_id} set to {target_status}[/green]")
    except Exception as e:
        console.print(f"[red]Failed to update campaign: {e}[/red]")
    finally:
        if own_conn:
            conn.close()


def activate_campaign(campaign_id: int, console: Console) -> None:
    _update_campaign_status(campaign_id, "active", console)


def pause_campaign(campaign_id: int, console: Console) -> None:
    _update_campaign_status(campaign_id, "paused", console)
