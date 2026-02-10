# Funnel Optimizer

Campaign pipeline SaaS for lead generation call centers. Works across service verticals (home renovation, HVAC, roofing, plumbing, etc.). Automates Meta Ads campaign creation, lead collection, and performance tracking — with AI agent-managed optimization on the roadmap.

## What It Does

```
Brief → Ad Content → Meta Campaign → Lead Collection → Performance Tracking
                          ↓                 ↓                    ↓
                    (always PAUSED     (idempotent          (daily metrics
                     until approved)    dedup by ID)         with upsert)
```

Call center operators define what to advertise (brief) for each end-client business (customer), write ad copy (content), and the system handles Meta campaign creation, lead ingestion, and metric tracking. Every step requires explicit approval before progressing — campaigns are created PAUSED and must be explicitly activated.

## Product Vision

**Phase 1 (current):** Manual content pipeline with CLI. Single call center, local deployment.

**Phase 2:** Web dashboard (FastAPI) for operators managing multiple customers. Serverless deployment (Fly.io/Railway + managed Postgres). AI content suggestions. GHL CRM sync. Real-time lead webhooks.

**Phase 3:** AI agent-managed campaigns within guardrails. Agents operate autonomously within budget caps, geo/brand rules, and CPL thresholds. Escalate outside bounds. Humans set rules and review dashboards.

**Growth:** Self-serve SaaS. Call centers sign up, connect Meta accounts, onboard customers. Multi-tenant isolation. White-label potential.

## Quick Start

```bash
# Setup
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# Configure Meta API credentials
cp .env.example .env
# Edit .env with your Meta API credentials

# Initialize
funnel db init

# Create a campaign
funnel content add-brief --name "DFW Bathroom" --project-type Bathroom --geo DFW --budget-cents 5000
funnel content add --brief-id 1 --headline "Transform Your Bathroom" --primary-text "Get a free quote"
funnel content approve 1
funnel campaign create 1        # Creates PAUSED on Meta
funnel campaign activate 1      # Go live

# Collect results
funnel leads collect
funnel leads metrics
funnel status
```

## CLI Reference

| Command | Description |
|---------|-------------|
| `funnel db init` | Create database tables |
| `funnel db status` | Show row counts per table |
| `funnel content add-brief` | Add a campaign brief |
| `funnel content add` | Add ad content for a brief |
| `funnel content load <file>` | Bulk load briefs + content from JSON |
| `funnel content approve <id>` | Mark content as approved |
| `funnel content list` | List all briefs and content |
| `funnel campaign create <id>` | Create PAUSED Meta campaign from approved content |
| `funnel campaign list` | List all campaigns |
| `funnel campaign activate <id>` | Activate campaign on Meta |
| `funnel campaign pause <id>` | Pause campaign on Meta |
| `funnel leads collect` | Collect leads from Meta (idempotent) |
| `funnel leads metrics` | Collect daily campaign metrics |
| `funnel status` | Full pipeline overview |

## Architecture

- **Database-driven pipeline** — SQLite is the integration layer. Each pipeline block reads/writes DB independently. No block-to-block coupling.
- **Thin API clients** — `clients/` handles HTTP concerns only. Business logic lives in `pipeline/`.
- **Idempotent operations** — Lead collection deduplicates by Meta lead ID. Metrics upsert by (campaign_id, date).
- **Safety by default** — Campaigns always created PAUSED. Explicit activation required.
- **Agent-ready** — DB state is the contract between humans and future AI agents. Errors stored for agent learning. All financial data in cents.

## Project Structure

```
src/funnel_optimizer/
├── config.py              # Settings from .env (FO_ prefix)
├── db.py                  # SQLite schema + connection
├── models.py              # Pydantic data models
├── cli.py                 # Typer CLI
├── clients/
│   └── meta_ads.py        # Meta Marketing API wrapper
└── pipeline/
    ├── content.py         # Brief + content CRUD
    ├── campaign.py        # Meta campaign lifecycle
    └── leads.py           # Lead + metrics collection
```

## Configuration

Copy `.env.example` to `.env` and fill in your Meta API credentials:

| Variable | Description |
|----------|-------------|
| `FO_META_APP_ID` | Meta Developer app ID |
| `FO_META_APP_SECRET` | Meta Developer app secret |
| `FO_META_AD_ACCOUNT_ID` | Ad account ID (`act_` prefix) |
| `FO_PRIVACY_POLICY_URL` | Required for lead gen forms |
| `FO_DB_PATH` | Database path (default: `data/pipeline.db`) |

## Development

```bash
pip install -e ".[dev]"
pytest                    # Run tests (16 tests, all with mocked Meta API)
```

## License

Proprietary. All rights reserved.
