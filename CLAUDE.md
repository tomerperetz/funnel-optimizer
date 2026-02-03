# Funnel Optimizer

## Project Purpose

AI-powered optimization for a home renovation call center in the US. Lead providers send homeowner leads, the call center contacts them via GoHighLevel (GHL) CRM, and the goal is to book renovation meetings.

## Business Context

- **Industry:** Home renovation (bathrooms, kitchens, etc.)
- **Flow:** Lead providers → Call center → Pipeline stages → Book meeting
- **CRM:** GoHighLevel (GHL)
- **Key metrics:** Lead quality, stage conversion rates, meeting booking rate

## Stakeholders

- **Data scientist** (you) — builds analysis and models
- **Call center managers** — consume operational insights
- **Ads manager** — consumes lead profiling for targeting/creative

## Tech Stack

- Python, Jupyter notebooks for exploration
- pandas, scikit-learn, matplotlib/seaborn for analysis
- LLMs embedded in analysis pipelines
- Code-simplifier convention: all code must be clean, simple, readable

## Project Structure

- `data/` — Raw CRM exports (gitignored). See `data/CLAUDE.md` for schema.
- `notebooks/` — Exploration and analysis. See `notebooks/CLAUDE.md` for conventions.
- `src/funnel_optimizer/` — Reusable code promoted from notebooks.
- `docs/plans/` — Design documents and plans.
- `.claude/agents/` — Specialist agents (data-analyst, funnel-profiler, customer-profiler, data-scientist, project-manager).
- `.claude/commands/` — Slash commands for common workflows.
- `.claude/skills/` — Shared knowledge for agents.

## Workflow

1. Explore in notebooks first
2. Promote to `src/` only when proven useful
3. All code follows code-simplifier principles: simple, readable, no over-engineering

## Data Overview

Two GHL exports linked by Contact ID:
- **Contacts** (~7K rows) — Unique people, deduplicated by phone/email
- **Opportunities** (~10.7K rows) — Lead events per contact (one-to-many)

See `data/CLAUDE.md` for full schema and field definitions.
