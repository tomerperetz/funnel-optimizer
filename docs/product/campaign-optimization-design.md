# Campaign Optimization Design

> Last updated: 2026-02-05

## Executive Summary

This document defines the experimental framework for autonomous campaign optimization in Funnel Optimizer. It covers:
1. Campaign hyperparameters that can be tuned
2. Success metrics and measurement methodology
3. Agent architecture for autonomous optimization
4. Learning loop design
5. Implementation roadmap

## 1. Hyperparameters Inventory

### 1.1 Budget Parameters

| Parameter | Current Location | Default | Range | Optimization Goal |
|-----------|-----------------|---------|-------|-------------------|
| `daily_budget_cents` | brief.budget_cents | 100 ($1) | 100-100000 | Maximize leads within budget |
| Bid strategy | meta_ads.py L110 | LOWEST_COST_WITHOUT_CAP | See 1.1.1 | Minimize CPL |
| Billing event | meta_ads.py L108 | IMPRESSIONS | IMPRESSIONS, LINK_CLICKS | Maximize efficiency |

#### 1.1.1 Bid Strategy Options
- `LOWEST_COST_WITHOUT_CAP` - Let Meta optimize for lowest cost (current default)
- `LOWEST_COST_WITH_BID_CAP` - Set maximum bid per impression/click
- `COST_CAP` - Target specific cost per result (CPL)
- `MINIMUM_ROAS` - Target return on ad spend (not applicable for lead gen)

### 1.2 Targeting Parameters

| Parameter | Current Location | Default | Options | Impact |
|-----------|-----------------|---------|---------|--------|
| Geo (countries) | meta_ads.py L101 | IL (hardcoded) | Any country codes | Audience size, CPL |
| Geo (regions) | content.targeting_json | None | State/metro/city | Local relevance |
| Age min | meta_ads.py L103 | 18 | 18-65 | Audience quality |
| Age max | meta_ads.py L104 | 65 | age_min-65+ | Audience size |
| Interests | content.targeting_json | None | Meta interest IDs | Intent signal |
| Behaviors | content.targeting_json | None | Meta behavior IDs | Intent signal |
| Custom audiences | Not implemented | None | Lookalike, retargeting | Higher intent |

### 1.3 Creative Parameters

| Parameter | Current Location | Default | Notes |
|-----------|-----------------|---------|-------|
| Headline | content.headline | User input | Max 40 chars recommended |
| Primary text | content.primary_text | User input | Max 125 chars recommended |
| CTA button | content.cta | LEARN_MORE | See 1.3.1 |
| Image | content.image_url | None | 1200x628 recommended |
| Image hash | Derived | Computed | From upload |

#### 1.3.1 CTA Options
- `LEARN_MORE` (current default)
- `SIGN_UP`
- `GET_QUOTE`
- `CONTACT_US`
- `APPLY_NOW`
- `BOOK_NOW`
- `DOWNLOAD`

### 1.4 Lead Form Parameters

| Parameter | Current Location | Default | Options |
|-----------|-----------------|---------|---------|
| Form questions | meta_ads.py L132-136 | Name, Email, Phone | Configurable |
| Privacy policy URL | settings.privacy_policy_url | Required | Per customer |
| Form type | Not implemented | More volume | More volume vs Higher intent |
| Custom questions | Not implemented | None | Project type, timeline, budget |

### 1.5 Optimization Parameters

| Parameter | Current Location | Default | Options |
|-----------|-----------------|---------|---------|
| Optimization goal | meta_ads.py L109 | LEAD_GENERATION | See 1.5.1 |
| Attribution window | Not implemented | 7-day click | 1/7/28 day click/view |
| Placement | Not implemented | Automatic | Feed, Stories, Reels, etc. |

#### 1.5.1 Optimization Goal Options
- `LEAD_GENERATION` (current) - Optimize for form submissions
- `LINK_CLICKS` - Optimize for clicks (use with landing page)
- `LANDING_PAGE_VIEWS` - Optimize for page loads
- `CONVERSATIONS` - Optimize for Messenger/WhatsApp

## 2. Success Metrics Framework

### 2.1 Primary Metrics (North Stars)

| Metric | Formula | Target | Measurement Latency |
|--------|---------|--------|---------------------|
| **CPL (Cost Per Lead)** | spend_cents / leads_count | < $40 | Real-time |
| **Meeting Rate** | meetings_booked / leads | > 20% | 7-14 days |
| **ROAS** | revenue / spend | > 3x | 30-60 days |

### 2.2 Secondary Metrics (Leading Indicators)

| Metric | Formula | Target | Use |
|--------|---------|--------|-----|
| CTR | clicks / impressions | > 1% | Creative quality |
| CVR | leads / clicks | > 10% | Form optimization |
| CPC | spend / clicks | < $4 | Audience quality |
| Frequency | impressions / reach | < 3 | Fatigue detection |
| Lead quality score | Model prediction | > 0.6 | Lead prioritization |

### 2.3 Guardrail Metrics (Safety Rails)

| Metric | Threshold | Action |
|--------|-----------|--------|
| Daily spend | > budget_cents | PAUSE campaign |
| CPL | > 2x target | PAUSE + alert |
| CTR | < 0.3% | Alert (creative issue) |
| Frequency | > 5 | Alert (audience fatigue) |

### 2.4 Statistical Requirements

For experiment validity:
- **Minimum sample size:** 100 leads per variant
- **Confidence level:** 95% (p < 0.05)
- **Minimum detectable effect:** 20% relative improvement
- **Experiment duration:** Minimum 7 days (full weekly cycle)

## 3. Experiment Design

### 3.1 Experiment Types

#### Type A: A/B Split Test
Compare two variants with controlled traffic split.

```
Campaign Budget: $50/day
├── Variant A (50%): Headline A, Image A
└── Variant B (50%): Headline B, Image B

Measurement: CPL, CTR, CVR per variant
Winner: Statistically significant lower CPL
```

#### Type B: Sequential Test
Run one variant, then another, compare.

```
Week 1: Variant A ($50/day)
Week 2: Variant B ($50/day)

Control for: Day-of-week, seasonality
Limitation: External factors may differ
```

#### Type C: Multi-Armed Bandit
Dynamically allocate budget to better performers.

```
Initial: 33% each to A, B, C
Day 3: A performing best → 50% A, 25% B, 25% C
Day 7: A confirmed winner → 70% A, 15% B, 15% C

Advantage: Faster convergence, less waste
Limitation: Harder to achieve statistical significance
```

### 3.2 What to Test (Priority Order)

| Priority | Hyperparameter | Expected Impact | Test Complexity |
|----------|---------------|-----------------|-----------------|
| 1 | Creative (headline + image) | High | Simple A/B |
| 2 | Targeting (geo precision) | High | A/B split |
| 3 | CTA button | Medium | Simple A/B |
| 4 | Bid strategy | Medium | Sequential |
| 5 | Age range | Medium | A/B split |
| 6 | Form questions | Medium | A/B split |
| 7 | Placements | Low | A/B split |

### 3.3 Experiment Lifecycle

```
1. HYPOTHESIS
   "Changing CTA from LEARN_MORE to GET_QUOTE will increase CVR by 15%"

2. DESIGN
   - Variant A: Current (LEARN_MORE)
   - Variant B: Test (GET_QUOTE)
   - Budget: $25/day each
   - Duration: 7 days
   - Success criteria: CVR improvement > 15% with p < 0.05

3. EXECUTE
   - Create campaigns with identical settings except CTA
   - Activate both simultaneously
   - Collect daily metrics

4. ANALYZE
   - Day 3: Interim check (no action unless guardrail breach)
   - Day 7: Statistical analysis
   - Calculate: effect size, confidence interval, p-value

5. DECIDE
   - If significant improvement: Roll out winner
   - If no difference: Keep current (simpler)
   - If inconclusive: Extend or redesign

6. LEARN
   - Document result in experiment log
   - Update hyperparameter recommendations
   - Feed into next experiment design
```

## 4. Agent Architecture

### 4.1 Agent Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     LEARNING COORDINATOR                         │
│  (Orchestrates experiments, tracks learnings, updates models)    │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│   CONTENT    │ │  EXPERIMENT  │ │ HYPERPARAMETER│ │   RESULTS    │
│   CREATOR    │ │   DESIGNER   │ │    TUNER     │ │   ANALYST    │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
      │                │                │                │
      └────────────────┴────────────────┴────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  PIPELINE (DB)   │
                    │  campaigns       │
                    │  experiments     │
                    │  metrics         │
                    │  learnings       │
                    └──────────────────┘
```

### 4.2 Agent Responsibilities

#### 4.2.1 Content Creator Agent
**Purpose:** Generate and optimize ad creative (headline, text, image)

**Inputs:**
- Brief (project type, geo, customer)
- Historical performance data (what worked before)
- Brand guidelines

**Outputs:**
- Content variants with rationale
- A/B test suggestions

**Autonomy Level:**
- Phase 2: Suggest content, human approves
- Phase 3: Auto-generate within guidelines, human reviews periodically

**Key Decisions:**
- What messaging resonates with this audience?
- Which images drive engagement?
- How to avoid creative fatigue?

#### 4.2.2 Experiment Designer Agent
**Purpose:** Design statistically valid experiments

**Inputs:**
- Optimization goals (reduce CPL, increase meeting rate)
- Available hyperparameters to test
- Historical experiment results
- Budget constraints

**Outputs:**
- Experiment specification (variants, budget, duration, success criteria)
- Risk assessment

**Autonomy Level:**
- Phase 2: Propose experiments, human approves
- Phase 3: Auto-run low-risk experiments, escalate novel ones

**Key Decisions:**
- What should we test next? (prioritization)
- How much budget to allocate?
- When is there enough data to conclude?

#### 4.2.3 Hyperparameter Tuner Agent
**Purpose:** Optimize campaign configuration based on learnings

**Inputs:**
- Experiment results
- Performance trends
- Constraints (budget, targeting rules)

**Outputs:**
- Recommended hyperparameter changes
- Expected impact estimates

**Autonomy Level:**
- Phase 2: Recommend changes, human implements
- Phase 3: Auto-adjust within guardrails

**Key Decisions:**
- Should we increase/decrease budget?
- Should we narrow/broaden targeting?
- Which bid strategy for this situation?

#### 4.2.4 Results Analyst Agent
**Purpose:** Measure experiment outcomes and detect patterns

**Inputs:**
- Campaign metrics (impressions, clicks, leads, spend)
- Lead outcomes (meeting rate, sale rate)
- External signals (seasonality, competition)

**Outputs:**
- Experiment verdict (winner, loser, inconclusive)
- Pattern insights (e.g., "DFW converts 40% better")
- Anomaly alerts

**Autonomy Level:**
- Phase 2: Report results, human interprets
- Phase 3: Auto-generate insights, trigger actions

**Key Decisions:**
- Is this result statistically significant?
- What explains this performance change?
- Should we pause this underperformer?

#### 4.2.5 Learning Coordinator Agent
**Purpose:** Orchestrate the optimization loop and maintain institutional knowledge

**Inputs:**
- All other agents' outputs
- Business rules and constraints
- Human feedback and overrides

**Outputs:**
- Next experiment to run
- Updated hyperparameter defaults
- Performance reports

**Autonomy Level:**
- Phase 2: Coordinate, human decides
- Phase 3: Fully autonomous within guardrails

**Key Decisions:**
- What's the optimization priority?
- When to explore vs exploit?
- When to escalate to human?

### 4.3 Agent Interfaces

#### Database Tables (New)

```sql
-- Experiment definitions
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

-- Experiment variants (campaigns in the experiment)
CREATE TABLE experiment_variants (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    campaign_id INTEGER REFERENCES campaigns(id),
    variant_name TEXT,  -- 'control', 'variant_a', 'variant_b'
    traffic_allocation REAL DEFAULT 0.5,  -- percentage
    hyperparameters_json TEXT  -- what's different in this variant
);

-- Experiment results
CREATE TABLE experiment_results (
    id INTEGER PRIMARY KEY,
    experiment_id INTEGER REFERENCES experiments(id),
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    winner_variant_id INTEGER REFERENCES experiment_variants(id),
    effect_size REAL,  -- percentage improvement
    confidence_level REAL,  -- 0-1
    p_value REAL,
    recommendation TEXT,
    analysis_json TEXT  -- detailed breakdown
);

-- Learnings (institutional knowledge)
CREATE TABLE learnings (
    id INTEGER PRIMARY KEY,
    source_experiment_id INTEGER REFERENCES experiments(id),
    category TEXT,  -- 'creative' | 'targeting' | 'bidding' | 'timing'
    finding TEXT,  -- "GET_QUOTE CTA increases CVR by 18%"
    confidence TEXT,  -- 'high' | 'medium' | 'low'
    applicable_to TEXT,  -- 'all' | 'home_renovation' | 'DFW'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### Agent Communication Protocol

```python
# Each agent exposes these methods:

class BaseAgent:
    def analyze(self, context: dict) -> dict:
        """Analyze current state, return insights."""
        pass

    def recommend(self, context: dict) -> list[Recommendation]:
        """Propose actions based on analysis."""
        pass

    def execute(self, action: Action) -> Result:
        """Execute an approved action."""
        pass

    def learn(self, outcome: Outcome) -> None:
        """Update internal state based on outcome."""
        pass
```

## 5. Learning Loop Design

### 5.1 Loop Overview

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│    ┌────────┐    ┌────────┐    ┌────────┐    ┌────────┐   │
│    │ CREATE │───▶│  RUN   │───▶│MEASURE │───▶│ LEARN  │   │
│    └────────┘    └────────┘    └────────┘    └────────┘   │
│         ▲                                         │        │
│         │                                         │        │
│         └─────────────────────────────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 Loop Cadence

| Activity | Frequency | Trigger |
|----------|-----------|---------|
| Metrics collection | Hourly | Scheduled |
| Performance review | Daily | Scheduled (9 AM) |
| Experiment analysis | When sample size met | Automatic |
| Learning extraction | Post-experiment | Automatic |
| Strategy update | Weekly | Scheduled (Monday) |

### 5.3 Decision Rules

#### Auto-Pause Rules (No Human Needed)
```python
if campaign.cpl_cents > brief.max_cpl_cents * 2:
    pause_campaign(campaign.id)
    alert("CPL exceeded 2x threshold")

if campaign.daily_spend_cents > brief.budget_cents * 1.2:
    pause_campaign(campaign.id)
    alert("Daily budget exceeded")
```

#### Auto-Adjust Rules (Phase 3)
```python
if experiment.winner and experiment.confidence > 0.95:
    apply_winning_variant_to_all_campaigns()

if campaign.frequency > 4 and campaign.ctr_trend == "declining":
    trigger_creative_refresh()
```

#### Escalation Rules
```python
if campaign.cpl_cents > brief.max_cpl_cents * 1.5:
    alert_human("CPL elevated, review recommended")

if no_leads_24h and campaign.status == "active":
    alert_human("No leads in 24h, investigate")
```

### 5.4 Knowledge Accumulation

The system builds knowledge at three levels:

1. **Campaign Level:** This specific campaign's learnings
   - Best performing creative
   - Optimal time of day
   - Audience fatigue signals

2. **Customer Level:** Patterns for this customer
   - What project types work best
   - Geographic performance differences
   - Seasonal patterns

3. **Platform Level:** Universal learnings
   - Industry benchmarks
   - Meta platform changes
   - Cross-customer patterns

## 6. Implementation Roadmap

### Phase 2A: Foundation (2 weeks)
- [ ] Create experiments, experiment_variants, experiment_results, learnings tables
- [ ] Implement basic A/B test creation (two campaigns with split budget)
- [ ] Build experiment status tracking
- [ ] Add statistical significance calculator

### Phase 2B: Measurement (2 weeks)
- [ ] Extend metrics collection for experiment attribution
- [ ] Implement winner detection algorithm
- [ ] Build experiment dashboard (list, status, results)
- [ ] Add learning extraction and storage

### Phase 2C: Agent Scaffolding (2 weeks)
- [ ] Create base agent class with analyze/recommend/execute/learn
- [ ] Implement Results Analyst agent (first, simplest)
- [ ] Implement Experiment Designer agent
- [ ] Build agent orchestration in Learning Coordinator

### Phase 3A: Autonomy (4 weeks)
- [ ] Implement guardrail system (hard limits)
- [ ] Add auto-pause rules
- [ ] Implement Hyperparameter Tuner agent
- [ ] Add Content Creator agent (AI-generated variants)

### Phase 3B: Full Loop (4 weeks)
- [ ] Connect all agents in autonomous loop
- [ ] Implement bandit-style budget allocation
- [ ] Add creative fatigue detection and refresh
- [ ] Build escalation and human override system

## 7. Success Criteria

### Phase 2 Exit Criteria
- [ ] 3+ experiments completed with statistical conclusions
- [ ] Experiment dashboard showing active and completed tests
- [ ] Learnings table with 5+ documented findings
- [ ] Auto-pause working for budget/CPL guardrails

### Phase 3 Exit Criteria
- [ ] Agents running autonomously for 30+ days
- [ ] 20%+ improvement in average CPL vs Phase 2 baseline
- [ ] <5% false positive rate on auto-pause decisions
- [ ] Human intervention rate <1x per week per customer

## Appendix A: Meta API Reference

### Bid Strategy Details

| Strategy | Best For | Risk Level |
|----------|----------|------------|
| LOWEST_COST_WITHOUT_CAP | Starting out, learning | Low |
| LOWEST_COST_WITH_BID_CAP | Cost control | Medium |
| COST_CAP | Predictable CPL | Medium |

### Targeting Structure
```json
{
  "geo_locations": {
    "countries": ["US"],
    "regions": [{"key": "4081"}],  // Texas
    "cities": [{"key": "2420605", "radius": 25}]  // Dallas
  },
  "age_min": 25,
  "age_max": 55,
  "interests": [{"id": "6003139266461"}],  // Home improvement
  "behaviors": [{"id": "6002714895372"}]   // Homeowners
}
```

## Appendix B: Statistical Methods

### Sample Size Calculator
```python
def required_sample_size(
    baseline_rate: float,  # e.g., 0.10 for 10% CVR
    minimum_effect: float,  # e.g., 0.20 for 20% relative improvement
    alpha: float = 0.05,    # Type I error rate
    power: float = 0.80     # 1 - Type II error rate
) -> int:
    from scipy import stats
    import numpy as np

    p1 = baseline_rate
    p2 = baseline_rate * (1 + minimum_effect)

    effect_size = 2 * np.arcsin(np.sqrt(p1)) - 2 * np.arcsin(np.sqrt(p2))

    z_alpha = stats.norm.ppf(1 - alpha / 2)
    z_power = stats.norm.ppf(power)

    n = ((z_alpha + z_power) / effect_size) ** 2
    return int(np.ceil(n))
```

### P-Value Calculation
```python
def calculate_significance(
    control_leads: int,
    control_spend: int,
    variant_leads: int,
    variant_spend: int
) -> dict:
    from scipy import stats

    control_cpl = control_spend / control_leads if control_leads else float('inf')
    variant_cpl = variant_spend / variant_leads if variant_leads else float('inf')

    # Chi-square test for lead counts
    observed = [[control_leads, variant_leads]]
    expected_total = control_leads + variant_leads
    expected = [[expected_total / 2, expected_total / 2]]

    chi2, p_value = stats.chisquare(observed[0], expected[0])

    effect_size = (control_cpl - variant_cpl) / control_cpl if control_cpl else 0

    return {
        "control_cpl": control_cpl,
        "variant_cpl": variant_cpl,
        "effect_size": effect_size,
        "p_value": p_value,
        "significant": p_value < 0.05
    }
```
