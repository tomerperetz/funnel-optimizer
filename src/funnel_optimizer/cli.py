"""CLI for the funnel optimizer pipeline."""

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from funnel_optimizer.config import get_settings
from funnel_optimizer.db import init_db, table_counts, get_connection
from funnel_optimizer.models import Brief, Content, Customer
from funnel_optimizer.pipeline.content import (
    add_brief,
    add_content,
    add_customer,
    approve_content,
    get_customer,
    list_briefs,
    list_content,
    list_customers,
    load_from_json,
)

app = typer.Typer(help="Funnel Optimizer — campaign pipeline CLI")
db_app = typer.Typer(help="Database management")
auth_app = typer.Typer(help="Meta authentication")
customer_app = typer.Typer(help="Customer management")
content_app = typer.Typer(help="Brief and content management")
campaign_app = typer.Typer(help="Meta campaign management")
leads_app = typer.Typer(help="Lead collection")

app.add_typer(db_app, name="db")
app.add_typer(auth_app, name="auth")
app.add_typer(customer_app, name="customer")
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
def db_check_meta(
    customer_id: Optional[int] = typer.Option(None, help="Customer ID to use for token (default: first with token)"),
):
    """Verify Meta API credentials using a customer's page token."""
    from funnel_optimizer.clients.meta_ads import MetaAdsClient
    try:
        settings = get_settings()
        customers = list_customers()
        if not customers:
            console.print("[red]No customers yet. Run: funnel auth start[/red]")
            raise typer.Exit(1)

        if customer_id is not None:
            customer = get_customer(customer_id)
            if not customer:
                console.print(f"[red]Customer #{customer_id} not found[/red]")
                raise typer.Exit(1)
        else:
            customer = next((c for c in customers if c.meta_page_access_token), None)

        if not customer or not customer.meta_page_access_token:
            console.print("[red]No customer with a page token found. Run: funnel auth start[/red]")
            raise typer.Exit(1)

        console.print(f"Using token from customer: {customer.name} (#{customer.id})")
        client = MetaAdsClient(settings, access_token=customer.meta_page_access_token)
        info = client.check_connection()
        console.print("[green]Meta API connection OK[/green]")
        for key, val in info.items():
            console.print(f"  {key}: {val}")
    except typer.Exit:
        raise
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


# --- Auth ---


@auth_app.command("start")
def auth_start(
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open browser automatically"),
    redirect_uri: Optional[str] = typer.Option(None, "--redirect-uri", help="Custom redirect URI (e.g., ngrok URL)"),
):
    """Start OAuth flow to get long-lived page tokens and link to customers."""
    from funnel_optimizer.auth import run_oauth_flow, set_redirect_uri, REDIRECT_PORT
    from funnel_optimizer.pipeline.content import (
        add_customer,
        get_customer_by_page_id,
        list_customers,
        update_customer_token,
    )

    try:
        settings = get_settings()
        if not settings.meta_app_id:
            console.print("[red]FO_META_APP_ID not set. Add it to your .env file.[/red]")
            raise typer.Exit(1)
        if not settings.meta_app_secret:
            console.print("[red]FO_META_APP_SECRET not set. Add it to your .env file.[/red]")
            raise typer.Exit(1)

        # Set custom redirect URI if provided (for ngrok)
        if redirect_uri:
            set_redirect_uri(redirect_uri)
            console.print(f"[cyan]Using custom redirect URI: {redirect_uri}[/cyan]")
            console.print(f"[yellow]Make sure ngrok is forwarding to localhost:{REDIRECT_PORT}[/yellow]\n")

        console.print("[bold]Starting Meta OAuth flow...[/bold]")
        console.print("You'll be asked to log in and grant access to your Pages.\n")

        user_token, pages = run_oauth_flow(open_browser=not no_browser)

        if not pages:
            console.print("[yellow]No pages found. Make sure you have admin access to at least one Page.[/yellow]")
            raise typer.Exit(1)

        # Show available pages
        console.print(f"\n[bold]Found {len(pages)} Page(s):[/bold]\n")
        table = Table()
        table.add_column("#", style="cyan", width=3)
        table.add_column("Page Name")
        table.add_column("Page ID")
        table.add_column("Linked Customer")

        for i, page in enumerate(pages, 1):
            existing = get_customer_by_page_id(page.id)
            linked = f"[green]{existing.name}[/green]" if existing else "[dim]—[/dim]"
            table.add_row(str(i), page.name, page.id, linked)
        console.print(table)

        # Process each page
        console.print("\n[bold]Link pages to customers:[/bold]")
        console.print("[dim]Enter page numbers to link (comma-separated), or 'all', or 'skip'[/dim]")

        selection = typer.prompt("Pages to link", default="all")

        if selection.lower() == "skip":
            console.print("[yellow]Skipped. No tokens saved.[/yellow]")
            return

        if selection.lower() == "all":
            indices = list(range(len(pages)))
        else:
            try:
                indices = [int(x.strip()) - 1 for x in selection.split(",")]
            except ValueError:
                console.print("[red]Invalid selection[/red]")
                raise typer.Exit(1)

        # Link selected pages
        for idx in indices:
            if idx < 0 or idx >= len(pages):
                console.print(f"[yellow]Skipping invalid index {idx + 1}[/yellow]")
                continue

            page = pages[idx]
            existing = get_customer_by_page_id(page.id)

            if existing:
                # Update existing customer's token
                update_customer_token(existing.id, page.access_token)
                console.print(f"[green]✓[/green] Updated token for customer: {existing.name}")
            else:
                # Create new customer
                console.print(f"\n[bold]New page: {page.name}[/bold]")
                customer_name = typer.prompt("  Customer name", default=page.name)

                customer = Customer(
                    name=customer_name,
                    meta_page_id=page.id,
                    meta_page_name=page.name,
                    meta_page_access_token=page.access_token,
                )
                customer_id = add_customer(customer)
                console.print(f"[green]✓[/green] Created customer #{customer_id}: {customer_name}")

        console.print("\n[green]Done![/green] Page tokens saved to customer records.")
        console.print("[dim]Page tokens don't expire as long as you maintain admin access.[/dim]")
        console.print("\nRun [cyan]funnel customer list[/cyan] to see customers.")

    except Exception as e:
        console.print(f"[red]Auth failed: {e}[/red]")
        raise typer.Exit(1)


@auth_app.command("status")
def auth_status():
    """Show token status for all customers."""
    from funnel_optimizer.auth import debug_token
    from funnel_optimizer.pipeline.content import list_customers
    from datetime import datetime

    customers = list_customers()

    if not customers:
        console.print("[yellow]No customers yet. Run: funnel auth start[/yellow]")
        return

    console.print("\n[bold]Customer Token Status[/bold]\n")

    table = Table()
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Customer")
    table.add_column("Page")
    table.add_column("Token")
    table.add_column("Status")

    for c in customers:
        if not c.meta_page_access_token:
            table.add_row(
                str(c.id),
                c.name,
                c.meta_page_id,
                "[dim]—[/dim]",
                "[red]No token[/red]",
            )
            continue

        try:
            info = debug_token(c.meta_page_access_token)
            is_valid = info.get("is_valid", False)
            expires_at = info.get("expires_at", 0)

            if not is_valid:
                status = "[red]Invalid[/red]"
            elif expires_at == 0:
                status = "[green]Never expires[/green]"
            else:
                expiry = datetime.fromtimestamp(expires_at)
                days = (expiry - datetime.now()).days
                if days < 7:
                    status = f"[red]Expires in {days}d[/red]"
                else:
                    status = f"[yellow]Expires in {days}d[/yellow]"

            table.add_row(
                str(c.id),
                c.name,
                c.meta_page_id,
                f"{c.meta_page_access_token[:12]}...",
                status,
            )
        except Exception as e:
            table.add_row(
                str(c.id),
                c.name,
                c.meta_page_id,
                f"{c.meta_page_access_token[:12]}...",
                f"[red]Error: {e}[/red]",
            )

    console.print(table)


# --- Customers ---


@customer_app.command("add")
def customer_add(
    name: str = typer.Option(..., help="Customer/client name"),
    page_id: str = typer.Option(..., help="Facebook Page ID"),
    page_name: Optional[str] = typer.Option(None, help="Facebook Page name (optional)"),
):
    """Add a new customer (client whose ads you manage)."""
    customer = Customer(name=name, meta_page_id=page_id, meta_page_name=page_name)
    customer_id = add_customer(customer)
    console.print(f"[green]Customer #{customer_id} created:[/green] {name}")


@customer_app.command("list")
def customer_list_cmd():
    """List all customers."""
    customers = list_customers()
    if not customers:
        console.print("[dim]No customers yet.[/dim]")
        return
    table = Table(title="Customers")
    table.add_column("ID", style="cyan", width=4)
    table.add_column("Name")
    table.add_column("Page ID")
    table.add_column("Page Name")
    table.add_column("Token", width=8)
    table.add_column("Status")
    for c in customers:
        status_style = "green" if c.status == "active" else "dim"
        token_status = "[green]✓[/green]" if c.meta_page_access_token else "[red]✗[/red]"
        table.add_row(
            str(c.id),
            c.name,
            c.meta_page_id,
            c.meta_page_name or "-",
            token_status,
            f"[{status_style}]{c.status}[/{status_style}]",
        )
    console.print(table)


# --- Content ---


@content_app.command("add-brief")
def content_add_brief(
    customer_id: int = typer.Option(..., help="Customer ID this brief belongs to"),
    name: str = typer.Option(..., help="Brief name"),
    project_type: str = typer.Option(..., help="e.g. Bathroom, Kitchen"),
    geo: str = typer.Option(..., help="e.g. DFW, Houston"),
    budget_cents: int = typer.Option(0, help="Daily budget in cents"),
):
    """Add a campaign brief for a customer."""
    customer = get_customer(customer_id)
    if not customer:
        console.print(f"[red]Customer #{customer_id} not found[/red]")
        raise typer.Exit(1)
    brief = Brief(customer_id=customer_id, name=name, project_type=project_type, geo=geo, budget_cents=budget_cents)
    brief_id = add_brief(brief)
    console.print(f"[green]Brief #{brief_id} created:[/green] {name} (for {customer.name})")


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
    customer_id: Optional[int] = typer.Option(None, help="Filter by customer ID"),
):
    """List content items."""
    briefs = list_briefs()
    if not briefs:
        console.print("[dim]No briefs yet.[/dim]")
        return

    for brief in briefs:
        if brief_id is not None and brief.id != brief_id:
            continue
        if customer_id is not None and brief.customer_id != customer_id:
            continue
        customer = get_customer(brief.customer_id)
        customer_name = customer.name if customer else "Unknown"
        console.print(f"\n[bold]Brief #{brief.id}:[/bold] {brief.name} ({brief.project_type}, {brief.geo}) [{brief.status}] — Customer: {customer_name}")
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


@campaign_app.command("init")
def campaign_init(
    config_file: str = typer.Argument(..., help="Path to campaign config JSON file"),
    customer_id: Optional[int] = typer.Option(None, "--customer-id", help="Use existing customer ID instead of auto-matching"),
):
    """Initialize a campaign from config JSON: parse, create DB records, generate approval report."""
    from pathlib import Path
    from funnel_optimizer.pipeline.init_campaign import init_campaign

    path = Path(config_file)
    if not path.exists():
        console.print(f"[red]File not found: {config_file}[/red]")
        raise typer.Exit(1)

    try:
        result = init_campaign(config_file)
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Init failed: {e}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[green bold]Campaign initialized![/green bold]\n")
    console.print(f"  Customer:  #{result.customer_id} ({result.config.customer.name})")
    console.print(f"  Brief:     #{result.brief_id}")
    console.print(f"  Variants:  {', '.join(f'#{c}' for c in result.content_ids)}")
    console.print(f"  Report:    {result.report_path}")
    console.print()
    console.print("[bold]Next steps:[/bold]")
    console.print(f"  1. Review report:  [cyan]open {result.report_path}[/cyan]")
    for cid in result.content_ids:
        console.print(f"  2. Approve content: [cyan]funnel content approve {cid}[/cyan]")
    console.print(f"  3. Create campaign: [cyan]funnel campaign create <content_id>[/cyan]")


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
