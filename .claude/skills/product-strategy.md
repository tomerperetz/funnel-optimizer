---
name: product-strategy
description: Business model, unit economics, success metrics, and product vision for Funnel Optimizer
---

# Product Strategy

## Vision

**Replace the campaign manager** — Automate the entire Meta Ads lifecycle (creative → campaign → leads) so call centers can scale without hiring more people.

**Improve lead quality through iteration** — Use meeting outcomes as feedback to optimize campaigns, not just lead volume.

## Business Model

### Stakeholders

| Role | Who | Cares About |
|------|-----|-------------|
| Tenant | Call center operator | ROI on platform, operational efficiency |
| Customer | End business (plumber, reno contractor) | Meetings booked, cost per meeting |
| Lead | Homeowner | Getting their project done |
| Platform | Us (Funnel Optimizer) | MRR, customer success |

### Unit Economics

```
Ad Spend → Leads → Meetings → Sales → Revenue

Example (home renovation):
- $1,000 ad spend
- 25 leads @ $40 CPL
- 5 meetings @ 20% lead-to-meeting
- 2 sales @ 40% meeting-to-sale
- $10,000 revenue @ $5,000 avg ticket

ROAS = $10,000 / $1,000 = 10x
```

**Break-even calculation:**
```
Required ROAS = 1 / gross_margin

If gross margin is 30%:
Required ROAS = 1 / 0.30 = 3.3x

If CPL = $40 and avg ticket = $5,000:
Break-even = need 1 sale per $1,650 ad spend
           = need 41 leads per sale
           = lead-to-sale rate of 2.4%
```

### Pricing Vectors (Future)

| Model | Description | Pros | Cons |
|-------|-------------|------|------|
| Per-meeting | Charge per meeting booked | Aligned with customer value | Requires meeting tracking |
| % of ad spend | 10-20% of managed spend | Predictable, scales with usage | Misaligned (we want to spend more) |
| Per-lead | Charge per qualified lead | Simple to track | Volume vs quality tension |
| SaaS subscription | Monthly fee per customer | Predictable MRR | Less aligned with value |

## Current Phase: Single Tenant, Prove Unit Economics

### What We're Proving
1. Can we create campaigns that generate leads? ✅ (Phase 1 done)
2. Can we collect leads reliably? ✅ (Phase 1 done)
3. Do leads convert to meetings at acceptable rate? (Testing now)
4. Can meeting feedback improve campaign performance? (Phase 2)
5. Can this run without human intervention? (Phase 3)

### Success Criteria for Phase 2
- [ ] At least 100 leads collected across campaigns
- [ ] Meeting outcomes tracked for >80% of leads
- [ ] Demonstrable improvement in lead quality over time
- [ ] Operator can manage 5+ customers without scaling headcount

## Scaling Strategy

### Phase 2: Depth (Better Feedback Loop)
- Track meeting outcomes (booked, showed, sold, lost reason)
- Feed outcomes back to campaign optimization
- AI content generation based on winning patterns
- Auto-pause underperforming campaigns

### Phase 3: Width (More Customers)
- Self-serve customer onboarding
- Customer-level dashboards
- Multi-customer budget management
- Automated page creation

### Phase 4: Multi-Tenant (More Call Centers)
- Call center self-signup
- Tenant isolation
- White-label option
- Usage-based billing

## Key Product Decisions

### Already Made
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Database as integration layer | Yes | Enables agent orchestration later |
| Campaigns start PAUSED | Yes | Safety for human and agent control |
| One page per customer | Yes | Client branding, isolation |
| Money in cents | Yes | Avoid floating point errors |

### Pending Decisions
| Decision | Options | Impact |
|----------|---------|--------|
| Where do hyperparameters live? | Brief / Customer / Config table | Flexibility vs complexity |
| Manual vs auto meeting tracking? | CRM sync / Manual entry / Webhook | Data quality vs effort |
| How to handle lost reasons? | Structured categories / Free text | Analysis quality vs UX |
| AI content: when to enable? | After N successful campaigns / Always with approval | Quality vs speed |

## Competitive Landscape

### What Exists Today

| Solution | What It Does | Gap |
|----------|--------------|-----|
| Meta Ads Manager | Manual campaign creation | No automation, requires expertise |
| AdEspresso / Revealbot | Campaign automation | No lead quality feedback, no meeting tracking |
| GoHighLevel | CRM + basic ads | Ads are afterthought, not core |
| LeadsBridge | Lead sync | Just data movement, no optimization |
| Human agency | Full service | Expensive, doesn't scale |

### Our Differentiation
1. **Feedback loop** — Meeting outcomes inform campaigns (others stop at leads)
2. **Vertical focus** — Built for service businesses with appointments
3. **Agent-ready architecture** — Designed for AI autonomy from day one
4. **Multi-customer native** — One platform, many client businesses

## Metrics Dashboard (Target State)

### Call Center View
- Total ad spend (all customers)
- Total leads generated
- Total meetings booked
- Overall CPL and CPM (cost per meeting)
- ROAS by customer

### Customer View
- Campaign status and spend
- Leads this period
- Meetings booked
- Conversion funnel visualization
- Top performing ads

### Agent View (Phase 3)
- Campaigns within guardrails vs flagged
- Automated actions taken
- Escalations to human
- Learning metrics (improvement over time)
