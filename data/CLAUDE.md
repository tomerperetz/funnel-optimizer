# Data Directory

CRM exports from GoHighLevel (GHL). Files are gitignored — never commit raw data.

## Contacts (`contacts_jan_2026.csv`)

~7K rows. One row per unique person (deduplicated by phone/email).

| Column | Type | Description |
|--------|------|-------------|
| Contact Id | string | GHL unique ID (links to Opportunities) |
| First Name | string | May be empty |
| Last Name | string | May be empty |
| Phone | string | Format: +1XXXXXXXXXX |
| Email | string | May be empty |
| Business Name | string | Rarely populated |
| Created | datetime | ISO 8601 with timezone offset |
| Last Activity | string | Human-readable date |
| Tags | string | Comma-separated tags (e.g., "sfa media") |

## Opportunities (`Opportunities (1).csv`)

~10.7K rows. One row per lead event. A contact can have multiple opportunities (different sources, job types, or duplicates).

| Column | Type | Description |
|--------|------|-------------|
| Opportunity Name | string | Often empty or same as contact name |
| Contact Name | string | Full name |
| phone | string | Format: +1XXXXXXXXXX |
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

# Join on Contact ID
merged = opportunities.merge(contacts, left_on="Contact ID", right_on="Contact Id", how="left", suffixes=("_opp", "_contact"))
```
