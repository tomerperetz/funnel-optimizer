---
name: report-generator
description: Use when generating pipeline performance reports — produces self-contained HTML from pipeline DB data
---

# Report Generator

You generate pipeline performance reports from the Funnel Optimizer SQLite database.

## Data Source

```python
import sqlite3
conn = sqlite3.connect("data/pipeline.db")
conn.row_factory = sqlite3.Row
```

Or use: `from funnel_optimizer.db import get_connection`

## Key Queries

```sql
-- Campaign overview
SELECT c.id, c.status, c.meta_campaign_id, co.headline, b.name, b.project_type, b.geo
FROM campaigns c
JOIN content co ON c.content_id = co.id
JOIN briefs b ON co.brief_id = b.id;

-- Daily metrics
SELECT cm.*, c.meta_campaign_id
FROM campaign_metrics cm
JOIN campaigns c ON cm.campaign_id = c.id
ORDER BY cm.date;

-- Leads per campaign
SELECT c.id, COUNT(l.id) as lead_count
FROM campaigns c LEFT JOIN leads l ON c.id = l.campaign_id
GROUP BY c.id;

-- Cost per lead by campaign
SELECT campaign_id, SUM(spend_cents) as total_spend, SUM(leads_count) as total_leads,
       CASE WHEN SUM(leads_count) > 0 THEN SUM(spend_cents) / SUM(leads_count) ELSE 0 END as cpl_cents
FROM campaign_metrics GROUP BY campaign_id;
```

## Report Structure

1. **Header** — Title, date range, generation timestamp
2. **KPI Grid** — Total spend, total leads, avg CPL, active campaigns
3. **Campaign Table** — Status, spend, leads, CPL per campaign
4. **Trend Charts** — Daily spend, daily leads, CPL over time
5. **Geo/Project Breakdown** — Performance by brief dimensions

## Chart Embedding

```python
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import base64
from io import BytesIO

def fig_to_b64(fig):
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    b64 = base64.b64encode(buf.read()).decode()
    plt.close(fig)
    return f'<img src="data:image/png;base64,{b64}" style="max-width:100%;">'
```

## Output

- Write to `reports/` directory
- Self-contained HTML — no external dependencies
- Use inline CSS
- Run with `.venv/bin/python3`
