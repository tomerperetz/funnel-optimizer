# Funnel Optimizer - Task List

> Last updated: 2026-02-06

## Current Goal

**Phase 2: Experiment-Driven Optimization** -- Build the learning loop that connects campaign performance to future decisions.

## Phase Summary

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | End-to-end pipeline with real Meta API | Complete |
| Phase 2A | Experiment foundation (schema, A/B tests) | In Progress |
| Phase 2B | Measurement and analysis | Pending |
| Phase 2C | Agent scaffolding | Pending |
| Phase 3 | Autonomous optimization | Future |

## Project Status

| Component | Status | Notes |
|-----------|--------|-------|
| Pipeline code | Complete | 18 tests passing |
| Multi-customer | Complete | customers table with meta_page_id |
| Meta API integration | Complete | Campaign, AdSet, Ad, Lead Form, Insights |
| OAuth flow | Complete | Per-customer page tokens |
| Campaign #2 (Wa2ig) | Created | PAUSED, $1/day budget |
| Lead collection | Untested | 0 leads in DB |
| Metrics collection | Untested | 0 metrics in DB |
| Experiment framework | Not started | Design complete |

---

## Tier 0: Unblock First Campaign

These tasks must complete before we can run experiments.

| ID | Task | Status | Owner | Notes |
|----|------|--------|-------|-------|
| #1 | Regenerate Meta access token | Pending | Human | Token expired 2026-02-04 |
| #2 | Fix default geo (IL -> US) | Pending | pipeline-dev | Hardcoded in meta_ads.py L101 |
| #3 | Activate Campaign #2 | Blocked | Human | Needs #1 |
| #4 | Collect first leads | Blocked | Human | Needs #3 + wait |
| #5 | Collect first metrics | Blocked | Human | Needs #3 + wait |

---

## Tier 1: Experiment Foundation (Phase 2A)

Database and basic experiment support.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #10 | Create experiment tables (experiments, variants, results, learnings) | Pending | - | pipeline-dev |
| #11 | Add hyperparameters model | Pending | - | pipeline-dev |
| #12 | Implement A/B test creation (split budget campaigns) | Pending | #10 | pipeline-dev |
| #13 | Add experiment CLI commands | Pending | #12 | pipeline-dev |
| #14 | Write experiment table tests | Pending | #10 | pipeline-dev |

### Task Details

#### #10: Create experiment tables

**Schema:**
```sql
CREATE TABLE experiments (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    hypothesis TEXT,
    status TEXT DEFAULT 'draft',  -- draft | running | completed | cancelled
    experiment_type TEXT,  -- a_b | sequential | bandit
    start_date TEXT,
    end_date TEXT,
    success_metric TEXT,  -- cpl | ctr | cvr | meeting_rate
    min_sample_size INTEGER DEFAULT 100,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE experiment_variants (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    campaign_id INTEGER REFERENCES campaigns(id),
    variant_name TEXT,
    traffic_allocation REAL DEFAULT 0.5,
    hyperparameters_json TEXT
);

CREATE TABLE experiment_results (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    winner_variant_id INTEGER REFERENCES experiment_variants(id),
    effect_size REAL,
    confidence_level REAL,
    p_value REAL,
    recommendation TEXT,
    analysis_json TEXT
);

CREATE TABLE learnings (
    id INTEGER PRIMARY KEY,
    source_experiment_id INTEGER REFERENCES experiments(id),
    category TEXT,  -- creative | targeting | bidding | timing
    finding TEXT,
    confidence TEXT,  -- high | medium | low
    applicable_to TEXT,  -- all | specific customer/project type
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### #11: Add hyperparameters model

Extract hardcoded values from `meta_ads.py` into a `HyperParameters` model:
- bid_strategy (default: LOWEST_COST_WITHOUT_CAP)
- optimization_goal (default: LEAD_GENERATION)
- billing_event (default: IMPRESSIONS)
- age_min (default: 18)
- age_max (default: 65)
- default_geo (default: US)

Store as JSON in content or separate table.

---

## Tier 2: Measurement (Phase 2B)

Statistical analysis and result tracking.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #20 | Implement statistical significance calculator | Pending | #14 | data-scientist |
| #21 | Add experiment metrics aggregation | Pending | #10 | pipeline-dev |
| #22 | Implement winner detection algorithm | Pending | #20, #21 | data-scientist |
| #23 | Build experiment analysis function | Pending | #22 | data-scientist |
| #24 | Add learning extraction and storage | Pending | #23 | data-scientist |

### Task Details

#### #20: Statistical significance calculator

Implement in `src/funnel_optimizer/analytics/`:
```python
def calculate_significance(
    control_leads: int,
    control_spend: int,
    variant_leads: int,
    variant_spend: int
) -> dict:
    """Return effect_size, p_value, significant bool"""
```

#### #22: Winner detection algorithm

Rules:
1. Minimum 100 leads per variant
2. p-value < 0.05
3. Effect size > 10% (avoid declaring winner for trivial differences)
4. Both variants ran for same duration

---

## Tier 3: Agent Scaffolding (Phase 2C)

Build the agent framework.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #30 | Create base agent class (analyze, recommend, execute, learn) | Pending | - | pipeline-dev |
| #31 | Wire campaign-orchestrator to DB and CLI | Pending | #30 | pipeline-dev |
| #32 | Wire budget-controller to briefs.budget_cents | Pending | #30 | pipeline-dev |
| #33 | Add experiment management commands | Pending | #12 | pipeline-dev |
| #34 | Add agent definitions to .claude/agents/ | **Complete** | - | project-manager |

### Task Details

#### #30: Base agent class

```python
class BaseAgent:
    def analyze(self, context: dict) -> dict:
        """Analyze current state, return insights."""

    def recommend(self, context: dict) -> list[Recommendation]:
        """Propose actions based on analysis."""

    def execute(self, action: Action) -> Result:
        """Execute an approved action."""

    def learn(self, outcome: Outcome) -> None:
        """Update internal state based on outcome."""
```

#### #34: Agent definitions (Complete)

All 13 agents defined in `.claude/agents/`:
- Product: product-manager, project-manager
- Data: data-scientist, data-analyst, experiment-designer
- Campaign: campaign-orchestrator, content-creator, targeting-optimizer, budget-controller
- Software: pipeline-dev, meta-integration, feature-manager, report-generator

---

## Tier 4: Guardrails (Phase 2D)

Safety rails before autonomy.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #40 | Add max_cpl_cents to briefs table | Pending | - | pipeline-dev |
| #41 | Add monthly_budget_cents to customers table | Pending | - | pipeline-dev |
| #42 | Implement auto-pause on CPL threshold | Pending | #40 | pipeline-dev |
| #43 | Implement daily spend guardrail | Pending | #5 | pipeline-dev |
| #44 | Add alerting system (console + future webhook) | Pending | #42, #43 | pipeline-dev |

---

## Tier 5: Autonomy (Phase 3)

Full autonomous optimization -- future work.

| ID | Task | Status | Blocked By | Agent |
|----|------|--------|------------|-------|
| #50 | Add hyperparameter tuning to budget-controller | Future | Tier 3, 4 | data-scientist |
| #51 | Wire content-creator to generate ad variations | Future | Tier 3 | content-creator |
| #52 | Add bandit-style budget allocation | Future | #50 | budget-controller |
| #53 | Implement creative fatigue detection | Future | Tier 2 | data-analyst |
| #54 | Build escalation and override system | Future | Tier 4 | campaign-orchestrator |

---

## Hyperparameters Inventory

Extracted from codebase -- these are the levers we can tune.

### Budget Parameters
| Parameter | Location | Default | Range |
|-----------|----------|---------|-------|
| daily_budget_cents | brief.budget_cents | 100 | 100-100000 |
| bid_strategy | meta_ads.py L110 | LOWEST_COST_WITHOUT_CAP | See options |
| billing_event | meta_ads.py L108 | IMPRESSIONS | IMPRESSIONS, LINK_CLICKS |

### Targeting Parameters
| Parameter | Location | Default | Notes |
|-----------|----------|---------|-------|
| geo_countries | meta_ads.py L101 | IL (bug!) | Should be US |
| age_min | meta_ads.py L103 | 18 | 18-65 |
| age_max | meta_ads.py L104 | 65 | age_min-65+ |
| interests | content.targeting_json | None | Meta interest IDs |

### Creative Parameters
| Parameter | Location | Default | Notes |
|-----------|----------|---------|-------|
| headline | content.headline | Required | Max 40 chars |
| primary_text | content.primary_text | Required | Max 125 chars |
| cta | content.cta | LEARN_MORE | See CTA options |
| image_url | content.image_url | None | 1200x628 recommended |

### CTA Options
LEARN_MORE, SIGN_UP, GET_QUOTE, CONTACT_US, APPLY_NOW, BOOK_NOW, DOWNLOAD

### Bid Strategy Options
- LOWEST_COST_WITHOUT_CAP (default, safest)
- LOWEST_COST_WITH_BID_CAP (set max bid)
- COST_CAP (target specific CPL)

---

## Success Metrics

### Phase 2 Exit Criteria
- [ ] 3+ experiments completed with statistical conclusions
- [ ] Experiment dashboard showing active and completed tests
- [ ] Learnings table with 5+ documented findings
- [ ] Auto-pause working for budget/CPL guardrails
- [ ] At least one agent running (Results Analyst)

### Phase 3 Exit Criteria (Future)
- [ ] Agents running autonomously for 30+ days
- [ ] 20%+ improvement in average CPL vs Phase 2 baseline
- [ ] <5% false positive rate on auto-pause decisions
- [ ] Human intervention rate <1x per week per customer

---

## Agent Architecture

Agents are organized into four teams. See CLAUDE.md for full documentation.

### Product Team (Strategy)
| Agent | Purpose | Color |
|-------|---------|-------|
| product-manager | Goals, CPL targets, guardrails, what to test | Purple |
| project-manager | Coordination, priorities, tracking | Purple |

### Data Team (Analysis)
Serves both Software and Campaign teams.

| Agent | Purpose | Color |
|-------|---------|-------|
| data-scientist | Experiment design, models, methodology | Orange |
| data-analyst | Measurement, reporting, insights | Red |
| experiment-designer | Statistical test design, sample sizes | Blue |

### Campaign Team (Execution)
| Agent | Purpose | Color |
|-------|---------|-------|
| campaign-orchestrator | Coordinates optimization loop, executes decisions | Cyan |
| content-creator | Generates ad creative variations | Yellow |
| targeting-optimizer | Optimizes audience targeting | Orange |
| budget-controller | Manages spend allocation and bids | Green |

### Software Team (Development)
| Agent | Purpose | Color |
|-------|---------|-------|
| pipeline-dev | Pipeline code, DB schema, business logic | Green |
| meta-integration | Meta Ads API integration | Cyan |
| feature-manager | Git workflow, feature implementation | Yellow |
| report-generator | Performance reports from DB | Magenta |

### Agent Flow
```
product-manager → sets strategy, targets, guardrails
       ↓
data-scientist/experiment-designer → designs experiments
       ↓
campaign team → executes campaigns
       ↓
data-analyst → measures results, reports back
       ↓
product-manager → reviews, adjusts strategy
```

---

## Quick Reference

### Test Command
```bash
.venv/bin/python3 -m pytest tests/ --tb=short
```

### Status Commands
```bash
.venv/bin/python3 -m funnel_optimizer.cli db status
.venv/bin/python3 -m funnel_optimizer.cli status
```

### Create Campaign Flow
```bash
funnel customer add --name "..." --page-id "..."
funnel content add-brief --customer-id X --name "..." --project-type "..." --geo "DFW" --budget-cents 5000
funnel content add --brief-id X --headline "..." --primary-text "..."
funnel content approve X
funnel campaign create X
funnel campaign activate X
```

---

## Design Documents

- `/docs/product/campaign-optimization-design.md` -- Full experiment framework design
- `/.claude/skills/database.md` -- Database schema reference
- `/CLAUDE.md` -- Project overview and architecture
