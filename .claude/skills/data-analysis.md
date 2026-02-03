---
name: data-analysis
description: Use when working with Funnel Optimizer CRM data — provides schema knowledge, loading patterns, key field definitions, and analysis conventions for GoHighLevel exports
---

# Data Analysis — Shared Knowledge

## Data Location

All data lives in `data/` (gitignored). See `data/CLAUDE.md` for full schema.

## Quick Reference

| Table | File | Rows | Key |
|-------|------|------|-----|
| Contacts | `data/contacts_jan_2026.csv` | ~7K | Contact Id |
| Opportunities | `data/Opportunities (1).csv` | ~10.7K | Opportunity ID |

**Join key:** `Contact ID` in Opportunities → `Contact Id` in Contacts (many-to-one).

## Loading Pattern

```python
import pandas as pd

contacts = pd.read_csv("data/contacts_jan_2026.csv")
opps = pd.read_csv("data/Opportunities (1).csv")
opps["Created on"] = pd.to_datetime(opps["Created on"])
opps["Updated on"] = pd.to_datetime(opps["Updated on"])
```

## Key Fields

- **status:** open / won / lost / abandoned. `won` = booked meeting (the conversion target).
- **stage:** GHL pipeline stage. Defines funnel position.
- **source:** Lead provider or channel. Key for ad optimization.
- **Lead Type:** Inbound Call, Outreach, etc.
- **Project Type:** Bathroom, Kitchen, etc. The renovation service.
- **lost reason name:** Why a lead dropped off. Critical for bottleneck analysis.
- **assigned:** Call center agent. For agent performance analysis.
- **Engagement Score:** GHL metric, often 0. Use cautiously.

## GHL-Specific Notes

- Pipeline stages are ordered within a pipeline but the CSV doesn't encode order — infer from data or ask.
- "Days Since" columns contain relative labels ("Today", "3 Days"), not numbers. Parse or ignore.
- Duplicate opportunities can exist for the same contact. Always check `Contact ID` cardinality.

## Code Conventions

- Keep code simple and readable (code-simplifier)
- Prefer pandas vectorized operations over loops
- Use seaborn for statistical plots, matplotlib for custom charts
- Always label axes and add titles to plots
