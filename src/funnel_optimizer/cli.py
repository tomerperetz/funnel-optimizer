"""CLI for the funnel optimizer pipeline."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from funnel_optimizer.db import init_db, table_counts, get_connection
from funnel_optimizer.models import Brief, Content
from funnel_optimizer.pipeline.content import (
    add_brief,
    add_content,
    approve_content,
    list_briefs,
    list_content,
    load_from_json,
)

app = typer.Typer(help="Funnel Optimizer — campaign pipeline CLI")
db_app = typer.Typer(help="Database management")
content_app = typer.Typer(help="Brief and content management")
campaign_app = typer.Typer(help="Meta campaign management")
leads_app = typer.Typer(help="Lead collection")

app.add_typer(db_app, name="db")
app.add_typer(content_app, name="content")
app.add_typer(campaign_app, name="campaign")
app.add_typer(leads_app, name="leads")

console = Console()


# --- Database ---


@db_app.command("init")
def db_init():
    """Create all database tables."""
    init_db()
    console.print("[green]Database initialized.[/green]")


@db_app.command("check-meta")
def db_check_meta():
    """Verify Meta API credentials by reading ad account info."""
    from funnel_optimizer.clients.meta_ads import MetaAdsClient
    from funnel_optimizer.config import get_settings
    try:
        settings = get_settings()
        if not settings.meta_access_token:
            console.print("[red]FO_META_ACCESS_TOKEN not set. Check your .env file.[/red]")
            raise typer.Exit(1)
        client = MetaAdsClient(settings)
        info = client.check_connection()
        console.print("[green]Meta API connection OK[/green]")
        for key, val in info.items():
            console.print(f"  {key}: {val}")
    except Exception as e:
        console.print(f"[red]Meta API connection failed: {e}[/red]")
        raise typer.Exit(1)


@db_app.command("status")
def db_status():
    """Show row counts per table."""
    counts = table_counts()
    table = Table(title="Database Status")
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right")
    for name, count in counts.items():
        table.add_row(name, str(count))
    console.print(table)


# --- Content ---


@content_app.command("add-brief")
def content_add_brief(
    name: str = typer.Option(..., help="Brief name"),
    project_type: str = typer.Option(..., help="e.g. Bathroom, Kitchen"),
    geo: str = typer.Option(..., help="e.g. DFW, Houston"),
    budget_cents: int = typer.Option(0, help="Daily budget in cents"),
):
    """Add a campaign brief."""
    brief = Brief(name=name, project_type=project_type, geo=geo, budget_cents=budget_cents)
    brief_id = add_brief(brief)
    console.print(f"[green]Brief #{brief_id} created:[/green] {name}")


@content_app.command("add")
def content_add(
    brief_id: int = typer.Option(..., help="Brief ID to attach content to"),
    headline: str = typer.Option(..., help="Ad headline"),
    primary_text: str = typer.Option(..., help="Ad primary text"),
    image_url: Optional[str] = typer.Option(None, help="Image URL or local file path"),
    cta: str = typer.Option("LEARN_MORE", help="Call-to-action type"),
    targeting: str = typer.Option("{}", help="Targeting JSON string"),
):
    """Add ad content for a brief."""
    content = Content(
        brief_id=brief_id,
        headline=headline,
        primary_text=primary_text,
        image_url=image_url,
        cta=cta,
        targeting_json=targeting,
    )
    content_id = add_content(content)
    console.print(f"[green]Content #{content_id} created[/green] for brief #{brief_id}")


@content_app.command("load")
def content_load(file: str = typer.Argument(..., help="Path to JSON file")):
    """Bulk load briefs and content from a JSON file."""
    counts = load_from_json(file)
    console.print(f"[green]Loaded {counts['briefs']} brief(s), {counts['content']} content item(s)[/green]")


@content_app.command("approve")
def content_approve(content_id: int = typer.Argument(..., help="Content ID to approve")):
    """Mark content as approved (ready for campaign creation)."""
    if approve_content(content_id):
        console.print(f"[green]Content #{content_id} approved[/green]")
    else:
        console.print(f"[red]Content #{content_id} not found[/red]")
        raise typer.Exit(1)


@content_app.command("list")
def content_list_cmd(
    brief_id: Optional[int] = typer.Option(None, help="Filter by brief ID"),
):
    """List content items."""
    briefs = list_briefs()
    if not briefs:
        console.print("[dim]No briefs yet.[/dim]")
        return

    for brief in briefs:
        if brief_id is not None and brief.id != brief_id:
            continue
        console.print(f"\n[bold]Brief #{brief.id}:[/bold] {brief.name} ({brief.project_type}, {brief.geo}) [{brief.status}]")
        items = list_content(brief.id)
        if not items:
            console.print("  [dim]No content[/dim]")
            continue
        table = Table(show_header=True)
        table.add_column("ID", style="cyan", width=4)
        table.add_column("Headline")
        table.add_column("Image", width=5)
        table.add_column("CTA", width=12)
        table.add_column("Status", width=10)
        for c in items:
            style = "green" if c.status == "approved" else "dim"
            has_img = "[green]yes[/green]" if c.image_url else "[dim]no[/dim]"
            table.add_row(str(c.id), c.headline, has_img, c.cta, f"[{style}]{c.status}[/{style}]")
        console.print(table)


# --- Campaign (placeholder — filled in Task 5) ---


@campaign_app.command("create")
def campaign_create(content_id: int = typer.Argument(..., help="Content ID to create campaign from")):
    """Create a PAUSED Meta campaign from approved content."""
    from funnel_optimizer.pipeline.campaign import create_campaign_from_content
    create_campaign_from_content(content_id, console)


@campaign_app.command("list")
def campaign_list_cmd():
    """List all campaigns."""
    from funnel_optimizer.pipeline.campaign import list_campaigns_cli
    list_campaigns_cli(console)


@campaign_app.command("activate")
def campaign_activate(campaign_id: int = typer.Argument(..., help="Campaign ID to activate")):
    """Set campaign to ACTIVE on Meta."""
    from funnel_optimizer.pipeline.campaign import activate_campaign
    activate_campaign(campaign_id, console)


@campaign_app.command("pause")
def campaign_pause(campaign_id: int = typer.Argument(..., help="Campaign ID to pause")):
    """Set campaign to PAUSED on Meta."""
    from funnel_optimizer.pipeline.campaign import pause_campaign
    pause_campaign(campaign_id, console)


# --- Leads (placeholder — filled in Task 6) ---


@leads_app.command("collect")
def leads_collect(
    campaign_id: Optional[int] = typer.Option(None, help="Specific campaign ID"),
):
    """Collect leads from Meta for active campaigns."""
    from funnel_optimizer.pipeline.leads import collect_leads
    collect_leads(campaign_id, console)


@leads_app.command("metrics")
def leads_metrics(
    campaign_id: Optional[int] = typer.Option(None, help="Specific campaign ID"),
):
    """Collect daily metrics from Meta."""
    from funnel_optimizer.pipeline.leads import collect_metrics
    collect_metrics(campaign_id, console)


# --- Status ---


@app.command("status")
def pipeline_status():
    """Full pipeline overview."""
    counts = table_counts()

    console.print("\n[bold]Pipeline Status[/bold]\n")

    table = Table(show_header=True)
    table.add_column("Table", style="cyan")
    table.add_column("Rows", justify="right")
    for name, count in counts.items():
        table.add_row(name, str(count))
    console.print(table)

    conn = get_connection()

    # Briefs by status
    rows = conn.execute("SELECT status, COUNT(*) as n FROM briefs GROUP BY status").fetchall()
    if rows:
        console.print("\n[bold]Briefs by status:[/bold]")
        for r in rows:
            console.print(f"  {r['status']}: {r['n']}")

    # Content by status
    rows = conn.execute("SELECT status, COUNT(*) as n FROM content GROUP BY status").fetchall()
    if rows:
        console.print("\n[bold]Content by status:[/bold]")
        for r in rows:
            console.print(f"  {r['status']}: {r['n']}")

    # Campaigns by status
    rows = conn.execute("SELECT status, COUNT(*) as n FROM campaigns GROUP BY status").fetchall()
    if rows:
        console.print("\n[bold]Campaigns by status:[/bold]")
        for r in rows:
            console.print(f"  {r['status']}: {r['n']}")

    # Recent leads
    row = conn.execute("SELECT COUNT(*) as n FROM leads").fetchone()
    console.print(f"\n[bold]Total leads:[/bold] {row['n']}")

    # Total spend
    row = conn.execute("SELECT COALESCE(SUM(spend_cents), 0) as total FROM campaign_metrics").fetchone()
    spend_dollars = row["total"] / 100
    console.print(f"[bold]Total spend:[/bold] ${spend_dollars:,.2f}")

    conn.close()


if __name__ == "__main__":
    app()
