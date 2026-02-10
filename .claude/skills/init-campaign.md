---
name: init-campaign
description: Campaign initialization pipeline — parse form JSON, create DB records, generate approval report
---

# Init Campaign Skill

## Overview

The init-campaign pipeline takes a JSON config (exported from `reports/campaign-init-form.html`) and:
1. Validates it against the `CampaignConfig` Pydantic model
2. Finds or creates a customer in the DB
3. Creates a brief with full config stored as `config_json`
4. Creates content variants (one per value proposition)
5. Generates an HTML approval report

## Config JSON Shape

```json
{
  "customer": { "name": "str", "website_url": "str|null", "business_description": "str|null" },
  "service": { "category": "str", "avg_ticket_dollars": "float|null", "special_ad_category": "str|null" },
  "geo": { "type": "city|zip|radius", "value": "str", "radius_miles": "int|null", "location_type": "str" },
  "budget": { "daily_dollars": "float", "monthly_cap_dollars": "float|null", "target_cpl_dollars": "float|null", "max_cpl_dollars": "float|null", "bid_strategy": "str" },
  "schedule": { "start_date": "str|null", "end_date": "str|null", "operating_hours": {...}, "operating_days": ["Mon","Tue",...] },
  "creative": { "value_propositions": ["str", "str", ...], "cta": "str", "image_urls": ["str"]|null, "brand_voice": "str", "language": "str", "prohibited_words": ["str"]|null },
  "lead_form": { "questions": ["str"], "thank_you_message": "str|null", "privacy_policy_url": "str|null" },
  "targeting": { "age_min": "int", "age_max": "int", "interest_keywords": "str|null" },
  "experiment": { "num_variants": "int", "primary_metric": "str", "min_effect_pct": "int" },
  "context": { "competitive_density": "str|null", "competitors": "str|null", ... },
  "_meta": { "form_version": "str", "generated_at": "str", "generated_by": "str" }
}
```

## Key Design Decisions

- **Money in dollars in config, cents in DB.** The form works in dollars. `dollars_to_cents()` converts at the pipeline boundary.
- **Customer matching is case-insensitive by name.** New customers get `meta_page_id="pending"` — requires `funnel auth start` before campaigns can be created on Meta.
- **One Content row per value proposition.** Each VP becomes a variant. Images cycle through `image_urls` if multiple provided.
- **All content created as `status="draft"`.** Requires explicit `funnel content approve <id>` before campaign creation.
- **Full config stored in `briefs.config_json`.** Queryable fields (`project_type`, `geo`, `budget_cents`) stay as first-class columns. The JSON blob holds everything else.

## CLI Usage

```bash
funnel campaign init <config.json>          # Parse → DB records → report
funnel campaign init config.json --customer-id 3  # Use existing customer
```

## Post-Init Workflow

```bash
funnel content approve <id>    # For each variant
funnel campaign create <id>    # Creates PAUSED Meta campaign
funnel campaign activate <id>  # Go live (manual only)
```

## Code Location

- Model: `src/funnel_optimizer/models.py` — `CampaignConfig` and sub-models
- Pipeline: `src/funnel_optimizer/pipeline/init_campaign.py`
- CLI: `src/funnel_optimizer/cli.py` — `campaign_init` command
- Tests: `tests/test_init_campaign.py`
