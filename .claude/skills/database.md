---
name: database
description: Full DDL, connection patterns, CRUD templates, money/timestamp conventions for pipeline DB
---

# Database Skill

## Connection

```python
from funnel_optimizer.db import get_connection, init_db, table_counts

conn = get_connection()          # row_factory=Row, FK on
init_db()                        # CREATE IF NOT EXISTS all tables
counts = table_counts()          # {"customers": 0, "briefs": 0, ...}
```

## Schema (SQLite at data/pipeline.db)

### customers
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | AUTOINCREMENT |
| name | TEXT NOT NULL | Client business name |
| meta_page_id | TEXT NOT NULL | Facebook Page ID for this client |
| meta_page_name | TEXT | Facebook Page name (optional) |
| status | TEXT | active / inactive |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### briefs
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | AUTOINCREMENT |
| customer_id | INTEGER FK NOT NULL | → customers(id) |
| name | TEXT NOT NULL | Brief name |
| project_type | TEXT NOT NULL | Bathroom, Kitchen, etc. |
| geo | TEXT NOT NULL | DFW, Houston, etc. |
| budget_cents | INTEGER | Daily budget in cents |
| status | TEXT | draft / active / paused / archived |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP |

### content
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | AUTOINCREMENT |
| brief_id | INTEGER FK | → briefs(id) |
| headline | TEXT NOT NULL | Ad headline |
| primary_text | TEXT NOT NULL | Ad body text |
| image_url | TEXT | Image URL or local path for ad creative |
| cta | TEXT | LEARN_MORE, SIGN_UP, etc. |
| targeting_json | TEXT | JSON targeting spec |
| status | TEXT | draft / approved / rejected |
| created_at, updated_at | TIMESTAMP | |

### campaigns
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | AUTOINCREMENT |
| content_id | INTEGER FK | → content(id) |
| meta_campaign_id | TEXT | Meta campaign ID |
| meta_adset_id | TEXT | Meta ad set ID |
| meta_ad_id | TEXT | Meta ad ID |
| meta_form_id | TEXT | Meta lead form ID |
| status | TEXT | pending / paused / active / error / archived |
| error_message | TEXT | Error details if failed |
| created_at, updated_at | TIMESTAMP | |

### leads
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | AUTOINCREMENT |
| campaign_id | INTEGER FK | → campaigns(id) |
| meta_lead_id | TEXT UNIQUE | Idempotent via INSERT OR IGNORE |
| full_name | TEXT | |
| email | TEXT | |
| phone | TEXT | |
| form_data_json | TEXT | Raw form fields as JSON |
| created_at | TIMESTAMP | |

### campaign_metrics
| Column | Type | Notes |
|--------|------|-------|
| id | INTEGER PK | AUTOINCREMENT |
| campaign_id | INTEGER FK | → campaigns(id) |
| date | TEXT NOT NULL | YYYY-MM-DD |
| impressions, clicks | INTEGER | |
| spend_cents | INTEGER | Money in cents |
| leads_count | INTEGER | |
| cpl_cents | INTEGER | Cost per lead in cents |
| created_at, updated_at | TIMESTAMP | |
| UNIQUE(campaign_id, date) | | Upsert key |

## Entity Relationships

```
customers (1) ──< briefs (1) ──< content (1) ──< campaigns (1) ──< leads
                                                    │
                                                    └──< campaign_metrics
```

- Each **customer** (client) has many **briefs**
- Each **brief** has many **content** items
- Each **content** becomes one **campaign**
- Each **campaign** collects many **leads** and **metrics**

## Multi-Customer Design

- **Customer isolation:** All data traces back to a customer via the FK chain
- **Page per customer:** Each customer has their own Facebook Page (`meta_page_id`)
- **Campaigns use customer's page:** Lead forms and ads are created on the customer's page, not a global one

## Conventions

- **Money:** Always cents. Display as `${cents / 100:,.2f}`
- **Timestamps:** Let SQLite set via DEFAULT CURRENT_TIMESTAMP. Set `updated_at = CURRENT_TIMESTAMP` on updates.
- **Idempotent writes:** Leads use INSERT OR IGNORE. Metrics use ON CONFLICT DO UPDATE.
- **Foreign keys:** Enabled via `PRAGMA foreign_keys = ON` in get_connection().
