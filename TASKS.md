# Funnel Optimizer — Productization Plan

> Last updated: 2026-02-07

## Current Goal

**Ship a usable product for one call center.** Prove the full loop works with real leads, then make it accessible via web dashboard. Scale infrastructure only when there's a second client.

## Guiding Principles

1. **Finish before expanding.** Phase 1 isn't truly done — zero real leads collected, token expired.
2. **One user before many.** Build for the one call center operator first. API key auth, not JWT. SQLite, not PostgreSQL.
3. **Data before experiments.** Need real leads flowing before A/B tests mean anything.
4. **Dashboard before agents.** An operator who can see data beats an agent framework with no data.
5. **Migrate when it hurts.** PostgreSQL, multi-tenant auth, and billing are "second client" problems.

## Software Design Status

Current codebase audit (2026-02-07). Items are prioritized by when they block progress.

### What's Solid
- **DB as integration layer** — pipeline blocks share DB only, never call each other
- **Idempotent collection** — leads (`INSERT OR IGNORE`), metrics (`ON CONFLICT DO UPDATE`)
- **Money in cents** — no floating point for financial data
- **Pydantic validation** — type-safe models for all entities and config
- **FK enforcement** — `PRAGMA foreign_keys = ON`, full chain from customer → leads
- **Per-customer tokens** — each customer has own Meta page token, proper isolation

### What's Missing (by phase)

| Gap | Severity | When to Fix | Notes |
|-----|----------|-------------|-------|
| **No logging config** — loggers exist but no handlers/formatters | Critical | Phase 2A | Impossible to debug production issues |
| **No retry logic** — any network hiccup fails the operation | Critical | Phase 2A | Add `tenacity` with exponential backoff for Meta API |
| **Campaign creation not idempotent** — re-run creates duplicate on Meta | Critical | Phase 1.5 | Check for existing campaign before Meta API call |
| **No config validation on startup** — missing env vars error late | Critical | Phase 2A | Validate all required vars at app start |
| **No DB indexes** beyond PKs | Important | Phase 2A | Add indexes on all FK columns + status + date |
| **No state machine validation** — invalid status transitions allowed | Important | Phase 2A | `approved→draft` shouldn't be possible |
| **No audit trail** — who approved what, when | Important | Phase 2B | Add `pipeline_events` table |
| **No error categorization** — can't distinguish transient vs permanent | Important | Phase 2A | Custom exception hierarchy |
| **~40% test coverage** — error paths and edge cases under-tested | Important | Phase 2A | Target 80% before deploy |
| **No input sanitization** — XSS risk in web UI | Important | Phase 2B | Escape all user input in templates |
| **No data retention policy** — metrics grow indefinitely | Nice-to-have | Phase 2D | Archive metrics older than 90 days |
| **No correlation IDs** — can't trace request through pipeline | Nice-to-have | Phase 3 | Agents need this for debugging |

### Data Flow

```
                    ┌──────────────┐
                    │  Config JSON │ (from init form)
                    └──────┬───────┘
                           ▼
┌──────────┐    ┌──────────────────┐    ┌─────────┐    ┌──────────┐
│ Customer │◄───│ init_campaign()  │───►│  Brief  │───►│ Content  │
│  (find/  │    │ dollars→cents    │    │ +config │    │ (1 per   │
│  create) │    │ validate config  │    │  _json  │    │  VP,     │
└──────────┘    └──────────────────┘    └─────────┘    │  draft)  │
                                                        └────┬─────┘
                                                             │ approve
                                                             ▼
                           ┌─────────────────────────────────────────┐
                           │         create_campaign()               │
                           │  Meta API: Campaign → Form → AdSet →   │
                           │           Creative → Ad (all PAUSED)    │
                           └────────────────┬────────────────────────┘
                                            │ activate (manual)
                                            ▼
                    ┌───────────────────────────────────────┐
                    │          LIVE ON META                  │
                    │                                       │
                    │  collect_leads()    collect_metrics()  │
                    │  (idempotent)       (upsert by date)  │
                    └───────┬───────────────────┬───────────┘
                            ▼                   ▼
                      ┌──────────┐      ┌──────────────┐
                      │  Leads   │      │   Metrics    │
                      │ (dedup   │      │ (daily agg,  │
                      │  by ID)  │      │  CPL calc)   │
                      └──────────┘      └──────────────┘
```

### Table Usage Patterns

| Table | Write Pattern | Read Pattern | Growth Rate | Indexes Needed |
|-------|--------------|-------------|-------------|----------------|
| customers | Rare (onboarding) | Frequent (every API call for token) | ~10s | PK only (fine) |
| briefs | Rare (campaign init) | Moderate (dashboard, lists) | ~10s | `customer_id` |
| content | Rare (campaign init) | Moderate (approval workflow) | ~50s | `brief_id`, `status` |
| campaigns | Rare (creation) | Frequent (status checks, dashboards) | ~50s | `content_id`, `status` |
| leads | High (collection runs) | High (inbox, reports, export) | **~1000s/month** | `campaign_id`, `created_at` |
| campaign_metrics | Moderate (daily upsert) | High (charts, CPL calc) | ~30/campaign/month | `(campaign_id, date)` already unique |

**Key insight:** `leads` is the only table that grows fast. Everything else stays small. Retention policy needed for leads after CRM sync (Phase 2D).

### Storage Strategy

| Phase | DB | Why | Migration Trigger |
|-------|-----|-----|-------------------|
| Phase 1-2A | SQLite (volume mount) | Simple, zero ops, fast for single tenant | — |
| Phase 2B+ | SQLite still | Dashboard queries are simple, single-server | Concurrent write contention |
| Phase 4 | PostgreSQL (managed) | Multi-tenant needs connection pooling, RLS | Second client signs up |

SQLite handles the expected load fine: <100 campaigns, <10k leads/month, single server. The `conn` parameter pattern makes migration mechanical when needed.

## Phase Summary

| Phase | Focus | Status | Exit Criteria |
|-------|-------|--------|---------------|
| Phase 1 | End-to-end pipeline with real Meta API | Code complete, unverified | Real leads and metrics in DB |
| Phase 1.5 | Prove it works end-to-end | **Current** | Campaign live, leads collected, metrics recorded |
| Phase 2A | Deploy + Minimal API | Pending | Backend running on server, API accessible |
| Phase 2B | Operator Dashboard | Pending | Operator manages campaigns via web UI |
| Phase 2C | Experiment Framework | Pending | 3+ experiments completed with statistical conclusions |
| Phase 2D | AI Content + Automation | Pending | AI-generated variants, scheduled data collection |
| Phase 3 | Agent Autonomy | Future | Agents optimizing within guardrails for 30+ days |
| Phase 4 | Multi-tenant SaaS | Future | Second call center onboarded, tenant isolation working |

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Pipeline code | Complete | 27 tests passing |
| Multi-customer | Complete | Per-customer page tokens via OAuth |
| Meta API integration | Complete | Campaign, AdSet, Ad, Lead Form, Insights |
| Campaign init flow | Complete | Form JSON → DB records → approval report |
| Campaign #2 (Wa2ig) | Created | PAUSED on Meta, never activated |
| Lead collection | Code done, untested | 0 leads in DB |
| Metrics collection | Code done, untested | 0 metrics in DB |
| Web API | Not started | — |
| Dashboard | Not started | — |
| Experiment framework | Design complete | See `/docs/product/campaign-optimization-design.md` |

---

## Phase 1.5: Prove It Works

**Goal:** A real campaign generating real leads with real metrics in the DB.

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| #1 | Refresh Meta access token | Pending | Human | Token expired 2026-02-04. Run `funnel auth start` |
| #2 | Fix default geo (IL → US) | Pending | pipeline-dev | Hardcoded in meta_ads.py L101 |
| #3 | Commit uncommitted work | Pending | Human | 15+ modified files on main — risk of lost work |
| #4 | Activate Campaign #2 | Blocked (#1) | Human | `funnel campaign activate 2` |
| #5 | Collect first real leads | Blocked (#4) | Human | `funnel leads collect` — wait for campaign to generate leads |
| #6 | Collect first real metrics | Blocked (#4) | Human | `funnel leads metrics` |
| #7 | Create campaign via init flow | Blocked (#1) | Human | Use form → export JSON → `funnel campaign init` → approve → create |
| #8 | Make campaign creation idempotent | Pending | — | pipeline-dev | Check for existing campaign before Meta API call |
| #9 | Add status transition validation | Pending | — | pipeline-dev | Prevent invalid transitions (e.g., error→active) |

**Exit:** `funnel status` shows active campaign, leads > 0, metrics > 0.

---

## Phase 2A: Deploy + Minimal API

**Goal:** Backend running on a server so the operator doesn't need CLI access to your laptop.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #10 | FastAPI app with core endpoints | Pending | Phase 1.5 | pipeline-dev |
| #11 | API key auth (single key, no user tables) | Pending | #10 | pipeline-dev |
| #12 | Dockerfile + fly.io/Railway deploy | Pending | #10 | pipeline-dev |
| #13 | Scheduled lead + metrics collection (cron) | Pending | #12 | pipeline-dev |
| #14 | Health endpoint (DB + Meta API check) | Pending | #10 | pipeline-dev |
| #15 | Structured logging (JSON, correlation IDs, log levels) | Pending | — | pipeline-dev |
| #16 | DB indexes on FK columns + status + date | Pending | — | pipeline-dev |
| #17 | Retry logic for Meta API calls (tenacity, backoff) | Pending | — | pipeline-dev |
| #18 | Config validation on startup (fail fast on missing vars) | Pending | — | pipeline-dev |
| #19 | Error categorization (custom exceptions, transient vs permanent) | Pending | — | pipeline-dev |

### API Endpoints (Minimal Set)

```
GET    /health
GET    /api/v1/status                   — Pipeline overview
GET    /api/v1/customers                — List customers
GET    /api/v1/campaigns                — List campaigns with status + metrics
GET    /api/v1/leads                    — List leads (filterable by campaign, date)
GET    /api/v1/metrics                  — Campaign metrics
POST   /api/v1/campaigns/init           — Upload config JSON, create DB records
POST   /api/v1/content/:id/approve      — Approve content variant
POST   /api/v1/campaigns/create         — Create PAUSED Meta campaign
POST   /api/v1/campaigns/:id/activate   — Go live
POST   /api/v1/campaigns/:id/pause      — Pause
```

**Key decisions:**
- SQLite is fine for single-tenant, single-server deployment
- API key auth (header: `X-API-Key`) — one key in env vars, no user tables yet
- Deploy with SQLite volume mount — migrate to PostgreSQL only when needed

**Exit:** API accessible at a public URL, lead/metrics collection running on schedule.

---

## Phase 2B: Operator Dashboard

**Goal:** Call center operator manages campaigns and sees leads via web browser.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #20 | Dashboard home — status, active campaigns, today's leads, spend | Pending | #10 | pipeline-dev |
| #21 | Campaign list view — status, spend, leads, CPL, activate/pause | Pending | #10 | pipeline-dev |
| #22 | Lead inbox — new leads with contact info, filterable | Pending | #10 | pipeline-dev |
| #23 | Metrics charts — spend, leads, CPL over time | Pending | #10 | pipeline-dev |
| #24 | Campaign init wizard — web version of the init form | Pending | #10 | pipeline-dev |
| #25 | Web OAuth flow — "Connect Facebook" button | Pending | #10 | meta-integration |
| #26 | Audit trail — `pipeline_events` table (who did what when) | Pending | #10 | pipeline-dev |
| #27 | Input sanitization for web UI (XSS prevention) | Pending | #20 | pipeline-dev |
| #28 | Meta ↔ DB reconciliation (sync campaign status from Meta) | Pending | #13 | pipeline-dev |

**Tech decision needed:** HTMX+Jinja2 (faster to ship for solo dev) vs React (better long-term if hiring frontend). Recommend HTMX for now.

**Exit:** Operator can view campaigns, see leads, and create new campaigns from browser.

---

## Phase 2C: Experiment Framework

**Goal:** Run A/B tests on campaign variants and determine winners with statistical rigor.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #30 | Create experiment tables (experiments, variants, results, learnings) | Pending | Phase 1.5 | pipeline-dev |
| #31 | Add hyperparameters model (extract hardcoded values from meta_ads.py) | Pending | — | pipeline-dev |
| #32 | Implement A/B test creation (split budget across variants) | Pending | #30 | pipeline-dev |
| #33 | Statistical significance calculator | Pending | #30 | data-scientist |
| #34 | Winner detection algorithm (min sample, p-value, effect size) | Pending | #33 | data-scientist |
| #35 | Learning extraction and storage | Pending | #34 | data-scientist |
| #36 | Experiment CLI commands (create, status, results) | Pending | #32 | pipeline-dev |
| #37 | Experiment view in dashboard | Pending | #20, #34 | pipeline-dev |

**Design reference:** `/docs/product/campaign-optimization-design.md` — full experiment types, statistical methods, agent architecture.

**Exit:** 3+ experiments completed with statistical conclusions. Learnings table with 5+ documented findings.

---

## Phase 2D: AI Content + Automation

**Goal:** Reduce manual work. AI writes ad copy, system collects data automatically.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #40 | AI content generation (Claude API → headline/text variants) | Pending | Phase 2C | content-creator |
| #41 | Guardrails — max CPL auto-pause, daily spend limits | Pending | Phase 2C | pipeline-dev |
| #42 | Real-time lead webhooks (Meta → instant notification) | Pending | #12 | meta-integration |
| #43 | Performance-based alerts (CPL spike, no leads 24h, budget exhausted) | Pending | #13 | pipeline-dev |

**Exit:** AI-generated content variants (with human approval gate). Auto-pause on CPL threshold. Scheduled data collection running.

---

## Phase 3: Agent Autonomy (Future)

**Goal:** Agents optimize campaigns within guardrails. Humans set rules and review dashboards.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #50 | Rule engine — budget caps, CPL thresholds, content approval, geo/brand rules | Future | Phase 2D | pipeline-dev |
| #51 | Campaign orchestrator agent — monitor, adjust, experiment, learn | Future | #50 | campaign-orchestrator |
| #52 | Budget controller — auto-adjust spend based on CPL performance | Future | #50 | budget-controller |
| #53 | Content creator agent — auto-generate and test creative variations | Future | #50 | content-creator |
| #54 | Bandit-style budget allocation (shift spend to winners dynamically) | Future | #51 | data-scientist |
| #55 | Creative fatigue detection and auto-refresh | Future | #51 | data-analyst |

**Exit:** Agents running autonomously for 30+ days. 20%+ CPL improvement vs baseline. Human intervention < 1x/week/customer.

---

## Phase 4: Multi-Tenant SaaS (Future)

**Goal:** Second call center can sign up and use the product independently.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #60 | PostgreSQL migration (SQLite → managed Postgres) | Future | Phase 3 | pipeline-dev |
| #61 | Tenant + user tables, JWT auth, RBAC | Future | #60 | pipeline-dev |
| #62 | Tenant isolation (row-level scoping on all queries) | Future | #61 | pipeline-dev |
| #63 | Self-serve onboarding flow | Future | #62 | pipeline-dev |
| #64 | Stripe billing integration | Future | #63 | pipeline-dev |
| #65 | Audit logging (who did what when) | Future | #61 | pipeline-dev |

**Trigger:** Only start this phase when there is a second paying client or public launch date.

**Exit:** Second call center onboarded, operating independently with full tenant isolation.

---

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Duplicate campaign creation (not idempotent) | **Critical** | Task #8 — check for existing campaign before Meta API call |
| Meta API token expiry at scale | High | Token health monitoring, auto-refresh, alerts |
| No retry logic — transient failures crash pipeline | High | Task #17 — tenacity with exponential backoff |
| Invalid state transitions corrupt pipeline | High | Task #9 — validate transitions before status updates |
| No logging — can't debug production issues | High | Task #15 — structured logging before deploy |
| Uncommitted code on main | Medium | Commit immediately (Task #3) |
| Single developer bottleneck | Medium | Prioritize ruthlessly, ship MVP of each phase |
| No DB indexes — slow queries as data grows | Medium | Task #16 — add before deploy |
| Meta ↔ DB status drift | Medium | Task #28 — reconciliation job |
| Agent makes bad campaign decisions | High | Human-in-the-loop first, tighten guardrails gradually |
| SQLite → PostgreSQL migration | Low | Code already uses `conn` params, customer_id isolation |

---

## Design Documents

- `/docs/product/campaign-optimization-design.md` — Experiment framework, agent architecture, learning loop, statistical methods
- `/docs/plans/2026-02-03-project-foundations-design.md` — Original project foundations
- `/.claude/skills/database.md` — Database schema reference
- `/.claude/skills/init-campaign.md` — Campaign init pipeline reference
- `/CLAUDE.md` — Project overview, architecture, conventions
