# Data Directory

CRM exports from GoHighLevel (GHL). Files are gitignored — never commit raw data.

## Contacts (`contacts_jan_2026.csv`)

~7K rows. One row per unique person (deduplicated by phone/email).

| Column | Type | Description |
|--------|------|-------------|
| Contact Id | string | GHL unique ID (links to Opportunities) |
| First Name | string | May be empty |
| Last Name | string | May be empty |
| Phone | string | Numeric 11-digit (e.g., `13463208495`), not +1 format |
| Email | string | May be empty |
| Business Name | string | Rarely populated |
| Created | datetime | ISO 8601 with timezone offset |
| Last Activity | string | Human-readable date |
| Tags | string | Comma-separated tags (e.g., "sfa media") |

## Opportunities (`Opportunities (1).csv`)

~7.5K rows. One row per lead event. A contact can have multiple opportunities (different sources, job types, or duplicates).

**Migration batch:** 6,366 rows bulk-imported on Oct 22, 2025 (15:56–16:28 UTC). Only 1,186 rows are post-migration operational data. Always filter with `Created on >= 2025-10-23` for operational analysis.

| Column | Type | Description |
|--------|------|-------------|
| Opportunity Name | string | Often empty or same as contact name |
| Contact Name | string | Full name |
| phone | string | Numeric 11-digit (e.g., `13463208495`). Area code at [1:4]. |
| email | string | May be empty |
| pipeline | string | GHL pipeline name (e.g., "Leads Pipeline") |
| stage | string | Current pipeline stage (key for funnel analysis) |
| Lead Value | number | Monetary value (often 0) |
| source | string | Lead source / provider name |
| assigned | string | Call center agent name |
| Created on | datetime | ISO 8601 UTC |
| Updated on | datetime | ISO 8601 UTC |
| lost reason ID | string | GHL ID for why lead was lost |
| lost reason name | string | Human-readable lost reason |
| Followers | string | GHL followers |
| Notes | string | Free text notes |
| tags | string | Comma-separated tags |
| Engagement Score | number | GHL engagement metric |
| status | string | open / won / lost / abandoned |
| Lead Type | string | e.g., "Inbound Call", "Outreach" |
| Project Type | string | e.g., "Bathroom", "Kitchen" |
| Project Details | string | Free text description of project |
| Follow Up Date | datetime | Scheduled follow-up |
| Airtable ID | string | External reference |
| Test | string | Test flag |
| Tracker Resource ID | string | Internal tracking |
| Opportunity ID | string | GHL unique ID |
| Contact ID | string | Links to Contacts table |
| Pipeline Stage ID | string | GHL stage ID |
| Pipeline ID | string | GHL pipeline ID |
| Days Since Last Stage Change Date | string | Relative time label |
| Days Since Last Status Change Date | string | Relative time label |
| Days Since Last Updated | string | Relative time label |

## Key Relationships

- **Contact ID** links Opportunities to Contacts (many-to-one)
- One contact can have multiple opportunities from different sources or for different project types
- Duplicate opportunities can exist (same contact, similar data — system or setup errors)

## Key Fields for Analysis

- **Funnel stages:** `stage` column — traces lead through pipeline
- **Conversion outcome:** `status` column — won = booked meeting, lost/abandoned = dropped
- **Segmentation:** `source`, `Lead Type`, `Project Type`, `tags`
- **Time analysis:** `Created on`, `Updated on`, `Follow Up Date`
- **Agent performance:** `assigned`
- **Drop-off reasons:** `lost reason name`

## Loading Pattern

```python
import pandas as pd

contacts = pd.read_csv("data/contacts_jan_2026.csv")
opportunities = pd.read_csv("data/Opportunities (1).csv")

# REQUIRED: fix trailing spaces in column names
opportunities.columns = opportunities.columns.str.strip()

# REQUIRED: parse dates with utc=True (mixed timezone offsets cause errors otherwise)
opportunities["Created on"] = pd.to_datetime(opportunities["Created on"], utc=True)
opportunities["Updated on"] = pd.to_datetime(opportunities["Updated on"], utc=True)
contacts["Created"] = pd.to_datetime(contacts["Created"], utc=True)

# Filter to post-migration operational data
post = opportunities[opportunities["Created on"] >= pd.Timestamp("2025-10-23", tz="UTC")]

# Join on Contact ID
merged = opportunities.merge(contacts, left_on="Contact ID", right_on="Contact Id", how="left", suffixes=("_opp", "_contact"))
```

## Deducible Fields

These fields can be inferred from existing data but are NOT structured CRM columns:

| Field | Source | Method | Coverage | Reliability |
|-------|--------|--------|----------|-------------|
| State | phone | Area code [1:4] → US state lookup | 97% | Medium — phone portability |
| Metro | phone | Area code → DFW/SA/Houston/Austin | 97% | Medium — same caveat |
| Project Type (gap-fill) | Project Details | Keyword matching on free text | +11% over structured | Medium — first-match, misses multi-project |

## Data Quality Notes

- **Lead Value:** All zeros — skip
- **Engagement Score:** All zeros — skip
- **Airtable ID / Test:** 100% null — skip
- **Email:** High null rate. Check coverage when analyzing — email presence is a strong signal worth investigating.
- **Lead Type:** High null rate — check coverage before relying on it
- **Project Type:** Partially filled — consider deducing from Project Details to improve coverage
- **Assigned agent:** Mostly null — check before attempting agent performance analysis
- **Lost reason:** Well documented post-migration, mostly missing in migration batch

## Generated Data Files

- `features.csv` — Engineered feature matrix (all opps) with area_code, state, has_email, etc.
- `model_results.json` — RF and GB model AUC scores and feature importances
- `profiles.json` — Converter profiles per project type (source lifts, email stats, etc.)
