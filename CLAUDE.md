# Funnel Optimizer

## Workflow Rules

- **Plan before execute.** For any task involving code changes, present a numbered plan with specific files and changes. Wait for explicit approval before writing code. If I say "just do it" or provide complete code, skip the plan and execute directly.
- **Feature branches always.** Never commit directly to main. Create a feature branch, implement, PR, merge.
- **Execute explicit instructions literally.** When I provide code, file contents, or specific instructions to create something, do it exactly as given. Don't explore the codebase or "understand context" first unless asked.
- **Verify after deploy.** After merging or deploying, check that the deployed version matches what was merged and test the specific feature changed. Don't close the task until verified.
- **Meta API: read docs first.** Before writing Meta Ads API integration code, read the relevant API docs and list all constraints, required fields, and common errors. Propose an implementation that handles them upfront — don't discover constraints one at a time through serial failures.
- **Max 2 fix attempts.** On any failure, present a root cause hypothesis before attempting a fix. After 2 failed fix iterations, check in with me before continuing.

## Product

Standalone SaaS product for lead generation call centers (any service vertical — home renovation, HVAC, roofing, etc.). Automates Meta Ads campaign lifecycle: brief → ad content → campaign creation → lead collection → performance tracking.

Currently serving one call center with multiple end-client businesses. Architected for multi-tenant growth.

**End state:** AI agents manage the entire campaign process within guardrails (budget caps, content approval, geo/brand rules, CPL thresholds). Agents operate autonomously within rules, escalate outside them. Humans set rules and review dashboards.

## Business Model

- **Tenant** = call center (manages the platform)
- **Customer** = end-client business (plumber, reno contractor, etc.) that the call center runs campaigns for. Each customer has their own Facebook Page (created/managed by the call center) and campaign briefs.
- **Operator** = call center employee using the dashboard
- **Ad platform** = Meta only for now. Code shouldn't fight adding Google Ads later, but no abstraction layer needed yet.
- **Page ownership:** Call center creates and owns Facebook Pages for each client. Ads show "by [Client Name]" branding. Single ad account (call center's) pays for all ads.

## Deployment

- **Target:** Serverless (Fly.io / Railway + managed Postgres like Neon/Supabase)
- **Interface:** Web dashboard (not CLI). CLI is a dev/ops tool only.
- **Phase 2 UI:** Operator dashboard controlling multiple customers
- **Phase 3+ UI:** Self-serve SaaS — call centers sign up, connect Meta accounts, onboard customers

## Architecture

```
[Customers] → [Briefs] → [Content] → [Meta Campaign] → [Lead Collection] → [Leads]
                                            ↓                   ↓
                                      [Campaigns]          [Metrics]
```

Each customer has their own Facebook Page. Campaigns are created on the customer's page, so ads display the client's branding.

**Core principle:** Database is the integration layer. Pipeline blocks read/write DB, never call each other. This makes blocks independently orchestrable — by humans today, by AI agents tomorrow.

**Growth considerations:**
- DB will migrate from SQLite to PostgreSQL for production
- All pipeline functions accept `conn` parameter — ready for connection pooling
- Customer isolation via `customer_id` on briefs (other tables inherit through FK chain)
- Approval workflows will move from CLI to web API endpoints

## Tech Stack

- Python 3.13+ (venv at `.venv/`, use `.venv/bin/python3` to run)
- SQLite at `data/pipeline.db` (PostgreSQL in production)
- Meta Marketing API via `facebook-business` SDK
- Pydantic for models, pydantic-settings for config
- Typer + Rich for CLI (dev/ops tool)
- FastAPI for web API (Phase 2)
- pytest for testing

## Project Structure

```
src/funnel_optimizer/
├── config.py              # pydantic-settings, FO_ prefix, loads .env
├── db.py                  # SQLite DDL, init_db(), get_connection()
├── models.py              # Customer, Brief, Content, Campaign, Lead, CampaignMetric
├── clients/
│   └── meta_ads.py        # MetaAdsClient — thin Meta API wrapper
├── pipeline/
│   ├── content.py         # CRUD for customers, briefs, content
│   ├── campaign.py        # Content → Meta campaign (always PAUSED)
│   └── leads.py           # Lead + metrics collection (idempotent)
└── cli.py                 # Typer CLI (dev/ops tool)
```

## CLI Reference (Dev/Ops Tool)

```bash
funnel db init                       # Create tables
funnel db status                     # Row counts
funnel db check-meta                 # Verify Meta API credentials
funnel customer add ...              # Add a customer (client)
funnel customer list                 # List customers
funnel content add-brief ...         # Add brief for a customer
funnel content add ...               # Add content for brief
funnel content load <file.json>      # Bulk load from JSON
funnel content approve <id>          # Mark content ready
funnel content list                  # List briefs and content
funnel campaign create <content_id>  # Create PAUSED Meta campaign
funnel campaign list                 # List campaigns
funnel campaign activate <id>        # Activate on Meta
funnel campaign pause <id>           # Pause on Meta
funnel leads collect                 # Collect leads from Meta
funnel leads metrics                 # Collect daily metrics
funnel status                        # Full pipeline overview
```

## Database

6 tables: `customers`, `briefs`, `content`, `campaigns`, `leads`, `campaign_metrics`. See `.claude/skills/database.md` for full schema.

**Entity relationships:**
```
customers (1) ──< briefs (1) ──< content (1) ──< campaigns (1) ──< leads
                                                    └──< campaign_metrics
```

**Conventions:**
- Money in cents (budget_cents, spend_cents, cpl_cents)
- Timestamps via SQLite CURRENT_TIMESTAMP
- Leads idempotent via `INSERT OR IGNORE` on `meta_lead_id`
- Metrics upsert via `ON CONFLICT(campaign_id, date) DO UPDATE`
- Foreign keys enforced (`PRAGMA foreign_keys = ON`)

## Config

Environment variables with `FO_` prefix, loaded from `.env`. See `.env.example`.

## Key Design Decisions

1. **DB as integration layer** — blocks are independent, agents can orchestrate via DB state
2. **Campaigns always PAUSED** — explicit activation required (safety for human and agent control)
3. **Idempotent collection** — safe to run lead/metric collection repeatedly
4. **Money in cents** — no floating point for financial data
5. **Errors in DB** — campaign errors stored in `error_message` column for agent learning
6. **Thin API clients** — `clients/` has HTTP concerns only; `pipeline/` has business logic
7. **All functions accept optional `conn`** — ready for connection pooling and testing
8. **Approval gates at every phase transition** — content must be approved before campaign creation, campaigns must be explicitly activated
9. **Vertical-agnostic** — no hardcoded project types, geos, or industry-specific logic. Call centers configure these per customer.

## Agent Organization

Agents are organized into three teams with clear responsibilities:

### Product Team (Strategy)
Sets goals, defines what to optimize for, establishes guardrails.

| Agent | Role |
|-------|------|
| `product-manager` | Goals, CPL targets, guardrails, what to test |
| `project-manager` | Coordination, priorities, tracking |

### Data Team (Analysis)
Designs experiments, measures results, provides insights. Serves both Software and Campaign teams.

| Agent | Role |
|-------|------|
| `data-scientist` | Experiment design, models, methodology |
| `data-analyst` | Measurement, reporting, insights |
| `experiment-designer` | Statistical test design, sample sizes |

### Campaign Team (Execution)
Executes campaigns and optimizations within product-defined guardrails.

| Agent | Role |
|-------|------|
| `campaign-orchestrator` | Coordinates optimization loop, executes decisions |
| `content-creator` | Generates ad creative variations |
| `targeting-optimizer` | Optimizes audience targeting |
| `budget-controller` | Manages spend allocation and bids |

### Software Team (Development)
Builds and maintains the product codebase.

| Agent | Role |
|-------|------|
| `pipeline-dev` | Pipeline code, DB schema, business logic |
| `meta-integration` | Meta Ads API integration |
| `feature-manager` | Git workflow, feature implementation |
| `report-generator` | Performance reports from DB |

### Agent Flow
```
product-manager → sets strategy, targets, guardrails
       ↓
data-scientist → designs experiments to meet goals
       ↓
campaign team → executes campaigns
       ↓
data-analyst → measures results, reports back
       ↓
(loop continues)
```

## Agent Guardrails

Agents operate autonomously within a rule engine:
- **Budget caps** — per-campaign and per-customer daily/monthly limits
- **Content approval** — new ad copy/targeting requires human sign-off
- **Geo/brand rules** — allowed geographies, brand guidelines, prohibited words
- **Performance thresholds** — min/max CPL, minimum conversion rate before auto-pause
- Agents act freely within rules. Escalate to human when outside bounds.

## Development

```bash
.venv/bin/pip install -e ".[dev]"    # Install with dev deps
.venv/bin/pytest                      # Run tests
.venv/bin/python3 -m funnel_optimizer.cli db init  # Init DB
```

## Phase 1 Philosophy: "Touch the Wall"

Phase 1 goal is to **prove the full loop works end-to-end with real integrations**. Every component starts simple — the point is to connect the pipeline from brief to collected lead with real Meta API calls, not to build polished components. Once the full loop runs, we iterate by replacing simple components with smarter versions (AI content, auto-targeting, etc.).

**What "done" looks like for Phase 1:**
1. Customer created with their Facebook Page ID
2. Brief created for customer
3. Content written (manually) and approved
4. Real Meta campaign created (PAUSED) on customer's page via API
5. Campaign activated, real ad runs with client branding
6. Real leads collected from Meta into DB
7. Real daily metrics collected into DB
8. `funnel status` shows the full picture

**Then iterate:** swap content creation for AI-generated. Swap static targeting for data-driven. Add GHL sync. Each swap is independent because blocks only share DB.

## Roadmap

- **Phase 1 (current):** End-to-end pipeline with real Meta integration. CLI-driven. Single tenant. SQLite. Prove every block works with real API calls.
- **Phase 2:** Web dashboard (FastAPI). Operator controls multiple customers. Serverless deployment + managed Postgres. AI content generation. GHL CRM sync. Real-time lead webhooks.
- **Phase 3:** Agent-managed campaigns within guardrails. Rule engine for budget/content/geo/CPL constraints. Agents optimize autonomously, escalate outside bounds.
- **Growth:** Self-serve SaaS. Call centers sign up and onboard. Multi-tenant isolation. White-label potential.

## Historical Reference

- `data/CLAUDE.md` — CRM schema reference (useful for lead field mapping)
- `data/*.csv` — Original CRM exports from first call center
- `notebooks/` — Analysis notebooks from Phase 0
- `reports/` — Generated reports
