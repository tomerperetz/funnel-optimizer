# Funnel Optimizer - Task List

> Last updated: 2026-02-04

## Current Phase

**Phase 1 Complete** — End-to-end pipeline working with real Meta API integration.

**Phase 2 In Progress** — Learning loop design, hyperparameters, production readiness.

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Pipeline code | Complete | 18 tests passing |
| Multi-customer | Complete | customers table with meta_page_id |
| Meta API integration | Complete | Campaign, AdSet, Ad, Lead Form, Insights |
| Demo campaign | Created | TestApp2 page |
| Token | Expired | Needs regeneration before API calls |
| Lead collection | Untested | 0 leads in DB |
| Metrics collection | Untested | 0 metrics in DB |

## Task List

### Tier 1: Unblock Real Campaigns

These have no dependencies and can be done immediately.

| ID | Task | Status | Description |
|----|------|--------|-------------|
| #21 | Fix default targeting geo | Pending | Change hardcoded Israel → US in meta_ads.py |
| #22 | Token management | Pending | Strategy for long-lived tokens, expiry checking |
| #23 | Customer onboarding checklist | Pending | Document what info to collect from business clients |

### Tier 2: Learning Loop Foundation

Task #24 is foundational — it unblocks the others.

| ID | Task | Status | Blocked By |
|----|------|--------|------------|
| #24 | Define learning loop architecture | Pending | — |
| #25 | Campaign hyperparameters config | Pending | #24 |
| #26 | Budget guardrails system | Pending | #24 |
| #27 | Performance thresholds | Pending | #24 |

## Task Details

### #21: Fix default targeting geo (Israel → US)

**Problem:** `meta_ads.py` has hardcoded `geo_locations: {"countries": ["IL"]}` as fallback.

**Solution:**
- Default to US
- Pull geo from brief.geo field
- Map geo strings (e.g., "DFW") to Meta targeting format

**Acceptance criteria:**
- [ ] Default geo is US, not Israel
- [ ] Geo pulled from brief when available
- [ ] Tests verify geo handling

---

### #22: Implement long-lived token management

**Problem:** Meta access tokens expire (current one expired 2026-02-04).

**Options:**
1. System User tokens (60-day, refreshable via API)
2. Long-lived Page tokens (never expire for owned pages)
3. Manual refresh with clear instructions

**Acceptance criteria:**
- [ ] Token strategy documented in docs/meta-setup.md
- [ ] Token expiry check in `funnel db check-meta`
- [ ] Consider auto-refresh or CLI refresh command

---

### #23: Create customer onboarding checklist

**Purpose:** Document what info to collect before running campaigns for a business.

**Required info:**
- Business name
- Facebook Page ID (or create new page)
- Target geography (cities, metros, states)
- Project types they handle
- Budget limits (daily/monthly)
- Brand guidelines / prohibited words
- Privacy policy URL

**Acceptance criteria:**
- [ ] Checklist in docs/customer-onboarding.md
- [ ] Required vs optional fields identified
- [ ] Maps to database schema

---

### #24: Define learning loop architecture

**Purpose:** Design the feedback loop connecting campaign performance to future decisions.

**Key questions:**
1. What metrics drive decisions? (CPL, CTR, conversion rate, lead quality)
2. What decisions can be made? (pause/activate, adjust budget, change targeting)
3. Who makes decisions? (Phase 2: human, Phase 3: agent within guardrails)
4. How is learning stored? (campaign_metrics? new table?)

**Deliverables:**
- [ ] Architecture diagram (data flow)
- [ ] Decision matrix (metric thresholds → actions)
- [ ] Schema design for storing learnings
- [ ] Phase 2 vs Phase 3 separation
- [ ] Write to docs/learning-loop-design.md

---

### #25: Create campaign hyperparameters configuration

**Problem:** Values hardcoded in meta_ads.py:
- `bid_strategy: "LOWEST_COST_WITHOUT_CAP"`
- `optimization_goal: "LEAD_GENERATION"`
- `billing_event: "IMPRESSIONS"`
- `targeting: age_min=18, age_max=65`

**Design decision:** Where do hyperparameters live?
- Option A: Brief-level (each campaign inherits)
- Option B: Separate `campaign_config` table
- Option C: Customer-level defaults + brief-level overrides

**Acceptance criteria:**
- [ ] Hyperparameters extracted to config
- [ ] Defaults documented
- [ ] Can override per-brief or per-customer
- [ ] Tests pass

---

### #26: Design budget guardrails system

**Purpose:** Safety limits before agent autonomy (Phase 3).

**Guardrail types:**
1. Per-campaign daily budget cap (exists: brief.budget_cents)
2. Per-customer monthly budget cap (new)
3. Per-customer concurrent campaign limit (new)
4. Auto-pause if CPL exceeds threshold (new)

**Enforcement timing:**
- At campaign creation (reject if over)
- At metrics collection (auto-pause if exceeded)
- At activation (check before enabling)

**Acceptance criteria:**
- [ ] Schema updates for budget limits
- [ ] Enforcement at key checkpoints
- [ ] Clear error messages
- [ ] Tests for guardrails

---

### #27: Add performance thresholds to campaign model

**Purpose:** Store thresholds that trigger actions.

**Threshold types:**
- `max_cpl_cents`: Auto-pause if CPL exceeds
- `min_ctr`: Alert if CTR drops below
- `min_daily_leads`: Alert if volume drops
- `max_daily_spend_cents`: Hard cap

**Acceptance criteria:**
- [ ] Schema updated with threshold columns
- [ ] Models updated
- [ ] Threshold checking in collect_metrics
- [ ] Tests for threshold triggering

---

## Completed Tasks

_None yet in Phase 2_

## Notes

- **Demo run:** TestApp2 page was used for testing. Next step is real business page.
- **Learning loop priority:** User wants to define the feedback mechanism before scaling.
- **Token expiry:** Must regenerate before any live API testing.
