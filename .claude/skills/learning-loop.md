---
name: learning-loop
description: Framework for the feedback loop that connects campaign outcomes to optimization decisions
---

# Learning Loop Framework

## Core Concept

The learning loop closes the gap between **spending money** and **knowing if it worked**.

```
TODAY:    Spend → Leads → ??? → Maybe good?
GOAL:     Spend → Leads → Meetings → Sales → Learn → Spend Better
```

## The Loop

```
┌────────────────────────────────────────────────────────────────┐
│                                                                │
│    CAMPAIGN                 OUTCOME                            │
│    ┌──────┐                 ┌──────┐                          │
│    │Target│──▶ Leads ──▶ Calls ──▶│Result│                    │
│    │Budget│                       │      │                    │
│    │Creative                      │Meeting│                   │
│    └──────┘                       │Sale   │                   │
│        ▲                          │Lost   │                   │
│        │                          └───┬───┘                   │
│        │                              │                       │
│        │    ┌─────────────────────────┘                       │
│        │    │                                                 │
│        │    ▼                                                 │
│        │  LEARNING                                            │
│        │  ┌──────────────────┐                               │
│        │  │ What worked?     │                               │
│        │  │ What didn't?     │                               │
│        │  │ Why?             │                               │
│        │  └────────┬─────────┘                               │
│        │           │                                          │
│        │           ▼                                          │
│        │  DECISION                                            │
│        │  ┌──────────────────┐                               │
│        └──│ Adjust targeting │                               │
│           │ Change budget    │                               │
│           │ New creative     │                               │
│           │ Pause campaign   │                               │
│           └──────────────────┘                               │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Input Signals

| Signal | Source | Delay | Granularity |
|--------|--------|-------|-------------|
| Impressions | Meta API | Minutes | Campaign/Ad |
| Clicks | Meta API | Minutes | Campaign/Ad |
| Spend | Meta API | Minutes | Campaign |
| Leads | Meta API | Minutes | Campaign |
| Lead details | Lead form | Immediate | Lead |
| Call outcome | CRM | Hours-Days | Lead |
| Meeting status | CRM | Days | Lead |
| Sale status | CRM | Weeks | Lead |
| Lost reason | CRM | Days | Lead |

### Derived Metrics

```python
# Efficiency metrics
cpl = spend / leads
cpm = spend / impressions * 1000
ctr = clicks / impressions
cvr = leads / clicks

# Quality metrics
contact_rate = contacted / leads
meeting_rate = meetings / leads
sale_rate = sales / leads

# Financial metrics
revenue = sales * avg_ticket
roas = revenue / spend
cac = spend / sales
ltv_cac_ratio = ltv / cac
```

### Output Decisions

| Decision | Input Signals | Threshold | Action |
|----------|--------------|-----------|--------|
| Pause poor performer | CPL, 7-day trend | CPL > 2x target | Set PAUSED |
| Scale winner | ROAS, volume | ROAS > 3x, leads > 50 | +20% budget |
| Refresh creative | CTR, frequency | CTR ↓ 30%, freq > 3 | New creative |
| Expand audience | Saturation | Reach > 80% of audience | Broaden targeting |
| Alert operator | Anomaly score | Score > threshold | Send notification |

## Learning Levels

### Level 1: Rules (Phase 2)
Simple if-then rules based on thresholds.

```python
if campaign.cpl > campaign.max_cpl:
    pause_campaign(campaign)
    alert_operator("CPL exceeded threshold")
```

**Pros:** Transparent, predictable, easy to debug
**Cons:** Doesn't adapt, misses patterns

### Level 2: Scoring Models (Phase 2-3)
ML models that score leads/campaigns.

```python
lead.quality_score = model.predict(lead.features)
if lead.quality_score > 0.7:
    prioritize_for_callback(lead)
```

**Pros:** Captures complex patterns, improves over time
**Cons:** Requires training data, less transparent

### Level 3: Optimization (Phase 3+)
Automated optimization within guardrails.

```python
# Agent proposes action
action = agent.recommend(campaign_state)

# Guardrails check
if within_budget(action) and within_rules(action):
    execute(action)
else:
    escalate_to_human(action)
```

**Pros:** Continuous improvement, scales without humans
**Cons:** Complex, needs robust guardrails

## Schema Design

### Core Tables (Exist)
- `campaigns` — Campaign config and Meta IDs
- `leads` — Individual leads with form data
- `campaign_metrics` — Daily aggregates (spend, impressions, etc.)

### New Tables (Learning Loop)

```sql
-- Lead outcomes (from CRM sync)
CREATE TABLE lead_outcomes (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    contacted_at TIMESTAMP,
    contact_result TEXT,  -- answered, voicemail, no_answer, wrong_number
    meeting_scheduled_at TIMESTAMP,
    meeting_status TEXT,  -- scheduled, completed, no_show, cancelled
    sale_status TEXT,     -- won, lost, pending
    lost_reason TEXT,     -- price, timing, competitor, not_qualified, other
    revenue_cents INTEGER,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Lead quality predictions
CREATE TABLE lead_scores (
    id INTEGER PRIMARY KEY,
    lead_id INTEGER REFERENCES leads(id),
    model_version TEXT,
    quality_score REAL,  -- 0.0 to 1.0
    meeting_probability REAL,
    sale_probability REAL,
    score_factors JSON,  -- Feature contributions
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Campaign performance predictions
CREATE TABLE campaign_predictions (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    model_version TEXT,
    predicted_cpl_cents INTEGER,
    predicted_meeting_rate REAL,
    confidence_interval JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Decision log (audit trail)
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    campaign_id INTEGER REFERENCES campaigns(id),
    decision_type TEXT,  -- pause, scale, alert, creative_refresh
    trigger_reason TEXT,
    trigger_data JSON,
    action_taken TEXT,
    actor TEXT,  -- human, agent, rule
    outcome TEXT,  -- pending, success, failed, rolled_back
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Implementation Phases

### Phase 2A: Manual Learning
1. Add `lead_outcomes` table
2. Build CRM sync to import outcomes
3. Dashboard showing lead → meeting → sale funnel
4. Manual analysis of what works

**Exit criteria:** Can see meeting rate by campaign

### Phase 2B: Lead Scoring
1. Collect 500+ leads with outcomes
2. Train lead quality model
3. Score new leads in real-time
4. Operator uses scores to prioritize calls

**Exit criteria:** Model AUC > 0.65

### Phase 2C: Automated Rules
1. Define threshold rules (CPL cap, etc.)
2. Implement rule engine
3. Rules suggest actions, human approves
4. Log all decisions

**Exit criteria:** Rules catch 80% of bad campaigns before human would

### Phase 3: Agent Autonomy
1. Agent executes low-risk decisions automatically
2. Human approval for high-risk decisions
3. Continuous model retraining
4. Self-improving targeting

**Exit criteria:** Agent manages campaigns with better ROAS than manual

## Key Metrics to Track

### Funnel Health
| Metric | Formula | Target | Alert |
|--------|---------|--------|-------|
| CPL | spend/leads | < $50 | > $75 |
| Contact rate | contacted/leads | > 70% | < 50% |
| Meeting rate | meetings/contacted | > 25% | < 15% |
| Show rate | showed/scheduled | > 80% | < 60% |
| Close rate | sales/meetings | > 30% | < 20% |

### Model Performance
| Metric | Formula | Target |
|--------|---------|--------|
| Lead score AUC | ROC area | > 0.70 |
| Score calibration | Brier score | < 0.2 |
| Decision accuracy | correct/total | > 80% |

### Loop Velocity
| Metric | Description | Target |
|--------|-------------|--------|
| Outcome delay | Time from lead to outcome | < 7 days avg |
| Decision latency | Time from signal to action | < 1 hour (auto) |
| Learning cycle | Time to retrain models | Weekly |

## Attribution Logic

### Simple Attribution (Phase 2)
- Last-touch: Credit to campaign that generated lead
- Works for single-campaign customers

### Multi-touch (Phase 3+)
- Customer may see multiple campaigns before converting
- Need to distribute credit across touchpoints
- Requires cross-campaign tracking

For Phase 2, use simple last-touch attribution.
