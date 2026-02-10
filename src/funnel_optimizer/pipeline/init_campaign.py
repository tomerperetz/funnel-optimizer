"""Init campaign pipeline: parse config JSON, create DB records, generate approval report."""

import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path

from funnel_optimizer.db import get_connection
from funnel_optimizer.models import Brief, CampaignConfig, Content, Customer
from funnel_optimizer.pipeline.content import add_brief, add_content, add_customer


def dollars_to_cents(dollars: float) -> int:
    """Convert dollars to cents, rounding to nearest cent."""
    return round(dollars * 100)


def find_or_create_customer(
    config: CampaignConfig, conn: sqlite3.Connection | None = None
) -> int:
    """Find existing customer by name (case-insensitive) or create new one.

    New customers get meta_page_id='pending' — filled later by `funnel auth start`.
    """
    close = conn is None
    if conn is None:
        conn = get_connection()

    row = conn.execute(
        "SELECT id FROM customers WHERE LOWER(name) = LOWER(?)",
        (config.customer.name,),
    ).fetchone()

    if row:
        customer_id = row["id"]
    else:
        customer = Customer(
            name=config.customer.name,
            meta_page_id="pending",
        )
        customer_id = add_customer(customer, conn)

    if close:
        conn.close()
    return customer_id


def create_brief_from_config(
    customer_id: int,
    config: CampaignConfig,
    conn: sqlite3.Connection | None = None,
) -> int:
    """Create a brief from campaign config. Converts dollars to cents for DB storage."""
    brief = Brief(
        customer_id=customer_id,
        name=f"{config.service.category} — {config.geo.value}",
        project_type=config.service.category,
        geo=config.geo.value,
        budget_cents=dollars_to_cents(config.budget.daily_dollars),
        config_json=config.model_dump_json(),
    )
    return add_brief(brief, conn)


def create_content_variants(
    brief_id: int,
    config: CampaignConfig,
    conn: sqlite3.Connection | None = None,
) -> list[int]:
    """Create one Content row per value proposition. Returns list of content IDs."""
    targeting = {
        "geo_type": config.geo.type,
        "geo_value": config.geo.value,
        "location_type": config.geo.location_type,
        "age_min": config.targeting.age_min,
        "age_max": config.targeting.age_max,
    }
    if config.geo.radius_miles:
        targeting["radius_miles"] = config.geo.radius_miles
    if config.targeting.interest_keywords:
        targeting["interest_keywords"] = config.targeting.interest_keywords

    image_urls = config.creative.image_urls or []
    content_ids = []

    for i, vp in enumerate(config.creative.value_propositions):
        image_url = image_urls[i % len(image_urls)] if image_urls else None
        content = Content(
            brief_id=brief_id,
            headline=vp,
            primary_text=f"{vp} — {config.customer.name}",
            image_url=image_url,
            cta=config.creative.cta,
            targeting_json=json.dumps(targeting),
            status="draft",
        )
        content_ids.append(add_content(content, conn))

    return content_ids


def generate_campaign_plan_report(
    config: CampaignConfig,
    customer_id: int,
    brief_id: int,
    content_ids: list[int],
) -> str:
    """Generate self-contained HTML approval report. Returns file path."""
    reports_dir = Path("reports")
    reports_dir.mkdir(exist_ok=True)

    slug = config.customer.name.lower().replace(" ", "-")[:30]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    filename = f"campaign-plan-{slug}-{timestamp}.html"
    filepath = reports_dir / filename

    # Calculations
    daily = config.budget.daily_dollars
    monthly_cap = config.budget.monthly_cap_dollars or daily * 30
    target_cpl = config.budget.target_cpl_dollars or 0
    est_leads_day = math.floor(daily / target_cpl) if target_cpl > 0 else 0
    est_leads_month = math.floor(monthly_cap / target_cpl) if target_cpl > 0 else 0
    variant_count = len(config.creative.value_propositions)

    # Experiment calculations
    num_variants = config.experiment.num_variants
    min_effect = config.experiment.min_effect_pct
    # Rough sample size per variant for detecting min_effect% change (z=1.96, power=0.8)
    if target_cpl > 0 and min_effect > 0:
        p = 0.5  # conservative conversion estimate
        effect_size = min_effect / 100
        n_per_variant = math.ceil((2 * (1.96 + 0.84) ** 2 * p * (1 - p)) / (effect_size ** 2))
        total_leads_needed = n_per_variant * num_variants
        est_experiment_cost = total_leads_needed * target_cpl
        est_experiment_days = math.ceil(total_leads_needed / est_leads_day) if est_leads_day > 0 else 0
    else:
        n_per_variant = 0
        total_leads_needed = 0
        est_experiment_cost = 0
        est_experiment_days = 0

    # Warnings
    warnings = []
    if not config.creative.image_urls:
        warnings.append("No images provided — campaigns without images have significantly worse CPL")
    if daily < 20:
        warnings.append(f"${daily}/day is low — Meta needs $20+/day to exit learning phase effectively")
    if config.service.special_ad_category == "HOUSING":
        warnings.append("Housing category active — age, gender, zip, and interest targeting are restricted by Meta")

    # Variant labels
    labels = [chr(65 + i) for i in range(variant_count)]  # A, B, C, ...

    # Build HTML
    e = escape  # shorthand

    warnings_html = ""
    if warnings:
        items = "".join(f"<div class='warning-item'>{e(w)}</div>" for w in warnings)
        warnings_html = f"<div class='warnings-section'><h3>Warnings</h3>{items}</div>"

    variant_cards = ""
    image_urls = config.creative.image_urls or []
    for i, vp in enumerate(config.creative.value_propositions):
        img = image_urls[i % len(image_urls)] if image_urls else None
        img_html = f"<div class='variant-image'><img src='{e(img)}' alt='Ad image' /></div>" if img else "<div class='variant-image no-image'>No image</div>"
        variant_cards += f"""
        <div class='variant-card'>
            <div class='variant-label'>Variant {labels[i]}</div>
            {img_html}
            <div class='variant-headline'>{e(vp)}</div>
            <div class='variant-text'>{e(vp)} — {e(config.customer.name)}</div>
            <div class='variant-cta'>{e(config.creative.cta)}</div>
        </div>"""

    days_pills = "".join(
        f"<span class='day-pill'>{e(d)}</span>"
        for d in config.schedule.operating_days
    )

    questions_html = "".join(
        f"<li>{e(q)}</li>" for q in config.lead_form.questions
    )

    approve_cmds = "".join(
        f"funnel content approve {cid}\n" for cid in content_ids
    )
    create_cmds = "".join(
        f"funnel campaign create {cid}\n" for cid in content_ids
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Campaign Plan — {e(config.customer.name)}</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0f; color: #e0e0e0; padding: 32px; line-height: 1.6; }}
.container {{ max-width: 900px; margin: 0 auto; }}
h1 {{ font-size: 1.8rem; margin-bottom: 8px; color: #fff; }}
h2 {{ font-size: 1.2rem; margin: 32px 0 16px; color: #a78bfa; border-bottom: 1px solid #2a2a3a; padding-bottom: 8px; }}
h3 {{ font-size: 1rem; margin-bottom: 12px; color: #c4b5fd; }}
.subtitle {{ color: #888; margin-bottom: 24px; }}
.db-ids {{ display: inline-flex; gap: 12px; margin-bottom: 24px; }}
.db-id {{ background: #1a1a2e; border: 1px solid #2a2a3a; border-radius: 6px; padding: 4px 10px; font-size: 0.85rem; font-family: monospace; }}
.db-id span {{ color: #a78bfa; }}
.kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; margin-bottom: 24px; }}
.kpi {{ background: #1a1a2e; border: 1px solid #2a2a3a; border-radius: 8px; padding: 16px; text-align: center; }}
.kpi-value {{ font-size: 1.5rem; font-weight: 700; color: #fff; }}
.kpi-label {{ font-size: 0.75rem; color: #888; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }}
.warnings-section {{ background: #2a1a0a; border: 1px solid #5a3a0a; border-radius: 8px; padding: 16px; margin-bottom: 24px; }}
.warnings-section h3 {{ color: #f59e0b; }}
.warning-item {{ padding: 6px 0; color: #fbbf24; font-size: 0.9rem; }}
.warning-item::before {{ content: "\\26A0 "; }}
.variant-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px; margin-bottom: 24px; }}
.variant-card {{ background: #1a1a2e; border: 1px solid #2a2a3a; border-radius: 8px; padding: 16px; }}
.variant-label {{ font-size: 0.75rem; font-weight: 700; color: #a78bfa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 12px; }}
.variant-image {{ height: 120px; background: #12121f; border-radius: 6px; margin-bottom: 12px; display: flex; align-items: center; justify-content: center; overflow: hidden; }}
.variant-image img {{ max-width: 100%; max-height: 100%; object-fit: cover; }}
.variant-image.no-image {{ color: #555; font-size: 0.85rem; }}
.variant-headline {{ font-size: 1.1rem; font-weight: 600; color: #fff; margin-bottom: 6px; }}
.variant-text {{ font-size: 0.85rem; color: #aaa; margin-bottom: 8px; }}
.variant-cta {{ display: inline-block; background: #a78bfa; color: #0a0a0f; font-size: 0.75rem; font-weight: 600; padding: 4px 12px; border-radius: 4px; text-transform: uppercase; }}
.detail-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px 24px; margin-bottom: 24px; }}
.detail-item {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #1a1a2e; }}
.detail-label {{ color: #888; }}
.detail-value {{ color: #fff; font-weight: 500; }}
.day-pills {{ display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 16px; }}
.day-pill {{ background: #a78bfa33; color: #c4b5fd; border: 1px solid #a78bfa55; border-radius: 20px; padding: 4px 12px; font-size: 0.8rem; }}
.questions-list {{ list-style: decimal; padding-left: 20px; margin-bottom: 24px; }}
.questions-list li {{ padding: 4px 0; color: #ccc; }}
.approval-bar {{ background: #0f1a0f; border: 1px solid #1a3a1a; border-radius: 8px; padding: 20px; margin-top: 32px; }}
.approval-bar h3 {{ color: #4ade80; margin-bottom: 12px; }}
.cli-block {{ background: #0a0a0f; border: 1px solid #2a2a3a; border-radius: 6px; padding: 12px 16px; font-family: monospace; font-size: 0.85rem; white-space: pre; overflow-x: auto; margin: 8px 0; color: #4ade80; }}
.step-label {{ font-size: 0.85rem; color: #888; margin-top: 12px; margin-bottom: 4px; }}
.footer {{ text-align: center; margin-top: 48px; color: #555; font-size: 0.75rem; }}
</style>
</head>
<body>
<div class="container">

<h1>Campaign Plan</h1>
<p class="subtitle">{e(config.customer.name)} &mdash; {e(config.service.category.replace('_', ' '))} in {e(config.geo.value)}</p>

<div class="db-ids">
    <div class="db-id"><span>Customer</span> #{customer_id}</div>
    <div class="db-id"><span>Brief</span> #{brief_id}</div>
    <div class="db-id"><span>Content</span> #{', #'.join(str(c) for c in content_ids)}</div>
</div>

<h2>KPIs</h2>
<div class="kpi-grid">
    <div class="kpi"><div class="kpi-value">${daily:,.0f}</div><div class="kpi-label">Daily Budget</div></div>
    <div class="kpi"><div class="kpi-value">${monthly_cap:,.0f}</div><div class="kpi-label">Monthly Cap</div></div>
    <div class="kpi"><div class="kpi-value">${target_cpl:,.0f}</div><div class="kpi-label">Target CPL</div></div>
    <div class="kpi"><div class="kpi-value">{est_leads_day}</div><div class="kpi-label">Est. Leads/Day</div></div>
    <div class="kpi"><div class="kpi-value">{est_leads_month}</div><div class="kpi-label">Est. Leads/Month</div></div>
    <div class="kpi"><div class="kpi-value">{variant_count}</div><div class="kpi-label">Variants</div></div>
</div>

{warnings_html}

<h2>Creative Variants</h2>
<div class="variant-grid">
{variant_cards}
</div>

<h2>Campaign Details</h2>
<div class="detail-grid">
    <div class="detail-item"><span class="detail-label">Category</span><span class="detail-value">{e(config.service.category.replace('_', ' '))}</span></div>
    <div class="detail-item"><span class="detail-label">Area</span><span class="detail-value">{e(config.geo.value)} ({e(config.geo.type)})</span></div>
    <div class="detail-item"><span class="detail-label">Avg Ticket</span><span class="detail-value">{f'${config.service.avg_ticket_dollars:,.0f}' if config.service.avg_ticket_dollars else 'N/A'}</span></div>
    <div class="detail-item"><span class="detail-label">Bid Strategy</span><span class="detail-value">{e(config.budget.bid_strategy.replace('_', ' ').title())}</span></div>
    <div class="detail-item"><span class="detail-label">Brand Voice</span><span class="detail-value">{e(config.creative.brand_voice.title())}</span></div>
    <div class="detail-item"><span class="detail-label">Language</span><span class="detail-value">{e(config.creative.language)}</span></div>
    <div class="detail-item"><span class="detail-label">Special Category</span><span class="detail-value">{e(config.service.special_ad_category or 'None')}</span></div>
    <div class="detail-item"><span class="detail-label">Location Type</span><span class="detail-value">{e(config.geo.location_type.replace('_', ' ').title())}</span></div>
</div>

<h2>Targeting</h2>
<div class="detail-grid">
    <div class="detail-item"><span class="detail-label">Age Range</span><span class="detail-value">{config.targeting.age_min} &ndash; {config.targeting.age_max}</span></div>
    <div class="detail-item"><span class="detail-label">Location Type</span><span class="detail-value">{e(config.geo.location_type.replace('_', ' ').title())}</span></div>
    <div class="detail-item"><span class="detail-label">Interests</span><span class="detail-value">{e(config.targeting.interest_keywords or 'Broad (no keywords)')}</span></div>
</div>

<h2>Schedule</h2>
<div class="day-pills">{days_pills}</div>
<div class="detail-grid">
    <div class="detail-item"><span class="detail-label">Hours</span><span class="detail-value">{e(config.schedule.operating_hours.start)} &ndash; {e(config.schedule.operating_hours.end)}</span></div>
    <div class="detail-item"><span class="detail-label">Timezone</span><span class="detail-value">{e(config.schedule.operating_hours.timezone)}</span></div>
    <div class="detail-item"><span class="detail-label">Start Date</span><span class="detail-value">{e(config.schedule.start_date or 'Immediate')}</span></div>
    <div class="detail-item"><span class="detail-label">End Date</span><span class="detail-value">{e(config.schedule.end_date or 'Ongoing')}</span></div>
</div>

<h2>Lead Form</h2>
<ol class="questions-list">{questions_html}</ol>
{f'<p style="color:#888;font-size:0.85rem;">Thank you message: {e(config.lead_form.thank_you_message)}</p>' if config.lead_form.thank_you_message else ''}

<h2>Experiment Plan</h2>
<div class="kpi-grid">
    <div class="kpi"><div class="kpi-value">{num_variants}</div><div class="kpi-label">Variants</div></div>
    <div class="kpi"><div class="kpi-value">{total_leads_needed}</div><div class="kpi-label">Leads Needed</div></div>
    <div class="kpi"><div class="kpi-value">${est_experiment_cost:,.0f}</div><div class="kpi-label">Est. Cost</div></div>
    <div class="kpi"><div class="kpi-value">{est_experiment_days}d</div><div class="kpi-label">Est. Duration</div></div>
</div>

<div class="approval-bar">
    <h3>Next Steps</h3>
    <p class="step-label">Step 1: Review variants above, then approve each one:</p>
    <div class="cli-block">{e(approve_cmds.strip())}</div>
    <p class="step-label">Step 2: Create PAUSED campaigns on Meta:</p>
    <div class="cli-block">{e(create_cmds.strip())}</div>
    <p class="step-label">Step 3: Activate when ready (manual only):</p>
    <div class="cli-block">funnel campaign activate &lt;campaign_id&gt;</div>
</div>

<div class="footer">
    Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &bull; Funnel Optimizer
</div>

</div>
</body>
</html>"""

    filepath.write_text(html)
    return str(filepath)


@dataclass
class InitCampaignResult:
    customer_id: int
    brief_id: int
    content_ids: list[int]
    report_path: str
    config: CampaignConfig


def init_campaign(
    config_path: str, conn: sqlite3.Connection | None = None
) -> InitCampaignResult:
    """Orchestrate full init: parse config, create DB records, generate report."""
    close = conn is None
    if conn is None:
        conn = get_connection()

    # Parse and validate config
    raw = json.loads(Path(config_path).read_text())
    config = CampaignConfig.model_validate(raw)

    # Create DB records
    customer_id = find_or_create_customer(config, conn)
    brief_id = create_brief_from_config(customer_id, config, conn)
    content_ids = create_content_variants(brief_id, config, conn)

    # Generate report
    report_path = generate_campaign_plan_report(config, customer_id, brief_id, content_ids)

    if close:
        conn.close()

    return InitCampaignResult(
        customer_id=customer_id,
        brief_id=brief_id,
        content_ids=content_ids,
        report_path=report_path,
        config=config,
    )
