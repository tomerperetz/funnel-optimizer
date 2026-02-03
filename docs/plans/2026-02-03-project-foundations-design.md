# Funnel Optimizer — Project Foundations Design

## Project Purpose

AI-powered optimization platform for a home renovation call center in the US. Lead providers send homeowner leads, the call center contacts them through a GoHighLevel (GHL) CRM pipeline, and the goal is to book meetings with sales reps.

**Primary objectives:**
- Profile top-of-funnel leads to improve ad targeting and creative
- Analyze funnel conversion to find drop-off points and bottlenecks
- Compare converting leads (meeting stage) vs. overall population
- Use ML to extract actionable insights for ads and operations

**Stakeholders:**
- Data scientist (builder) — works directly in the repo
- Call center managers — consume operational insights
- Ads manager — consumes lead profiling and targeting insights

## Data

Two CRM exports from GoHighLevel, stored in `data/` (gitignored):

- `contacts_jan_2026.csv` (~7K rows) — Unique people. Deduplicated by phone/email.
- `Opportunities (1).csv` (~10.7K rows) — Lead events. One contact can have multiple opportunities (different sources, job types, or duplicates).

Linked by `Contact ID`.

## Tech Stack

- Python, Jupyter notebooks for exploration
- `src/funnel_optimizer/` for proven reusable code (promoted from notebooks)
- Claude Code as dev assistant + LLMs embedded in analysis pipelines
- All code must be clean, simple, and easy to read (code-simplifier convention)

## Directory Structure

```
funnel-optimizer/
├── CLAUDE.md
├── README.md
├── .gitignore
├── .python-version
├── pyproject.toml
│
├── data/
│   ├── CLAUDE.md              # Data dictionary, GHL schema
│   ├── contacts_jan_2026.csv
│   └── Opportunities (1).csv
│
├── notebooks/
│   └── CLAUDE.md              # Notebook conventions
│
├── src/
│   └── funnel_optimizer/
│       └── __init__.py
│
├── docs/
│   └── plans/
│
└── .claude/
    ├── settings.json
    ├── commands/
    │   ├── plan.md            # /plan — PM orchestrates a goal
    │   ├── explore-data.md    # /explore-data — open-ended exploration
    │   ├── funnel.md          # /funnel — funnel profiling
    │   ├── profile-customers.md # /profile-customers — converter profiling
    │   ├── ask.md             # /ask — quick data question
    │   └── model.md           # /model — ML analysis
    ├── agents/
    │   ├── project-manager.md
    │   ├── data-analyst.md
    │   ├── funnel-profiler.md
    │   ├── customer-profiler.md
    │   └── data-scientist.md
    └── skills/
        └── data-analysis.md
```

## Agents

### project-manager.md
Orchestrator. Takes high-level goals, breaks them into tasks, dispatches to specialist agents, tracks progress, synthesizes outputs into coherent reports. Knows each agent's strengths.

### data-analyst.md
Loads CSVs, answers ad-hoc questions, explores distributions, cross-tabs, filters. Knows GHL schema and Contacts/Opportunities relationship.

### funnel-profiler.md
Maps pipeline stage conversions, calculates stage-by-stage drop-off rates, segments by source/lead type/project type/time. Produces funnel charts, waterfalls, conversion heatmaps.

### customer-profiler.md
Compares meeting-stage leads vs. overall population. Profiles by source, project type, engagement score, time patterns. Outputs comparison visualizations and statistical summary.

### data-scientist.md
ML expert. Classification (who converts?), feature importance, clustering for segmentation, anomaly detection. Interprets model outputs into actionable business recommendations.

## Slash Commands

| Command | Agent | Purpose |
|---------|-------|---------|
| `/plan` | project-manager | Orchestrate a high-level goal |
| `/explore-data` | data-analyst | Open-ended data exploration |
| `/funnel` | funnel-profiler | Funnel analysis and visualization |
| `/profile-customers` | customer-profiler | Converter vs. population profiling |
| `/ask` | data-analyst | Quick question about the data |
| `/model` | data-scientist | ML-based analysis |

## Skills

### data-analysis.md
Shared knowledge layer for all agents:
- Data file locations and loading patterns
- GHL schema definitions for both tables
- How Contacts and Opportunities relate (Contact ID, one-to-many)
- Key field meanings (pipeline stages, status, lost reasons, engagement score)
- Preferred visualization libraries and style
- Code-simplifier convention: all code must be clean, simple, readable

## Conventions

- Explore in notebooks first, promote to `src/` only when proven useful
- All code follows code-simplifier principles: simple, readable, no over-engineering
- Data files never committed to git
- CLAUDE.md files scoped per directory for contextual AI assistance
