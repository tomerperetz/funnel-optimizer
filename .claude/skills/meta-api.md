---
name: meta-api
description: Meta Marketing API setup, campaign flow, lead forms, targeting, insights, error codes
---

# Meta API Skill

## SDK Initialization

```python
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount

FacebookAdsApi.init(app_id, app_secret, access_token, api_version="v21.0")
account = AdAccount("act_XXXXXXXXX")
```

## Campaign Creation Flow

1. `account.create_campaign(name, objective="OUTCOME_LEADS", status="PAUSED")`
2. `LeadgenForm(parent_id=page_id).api_create(name, questions, privacy_policy)`
3. `account.create_ad_set(campaign_id, daily_budget, targeting, optimization="LEAD_GENERATION")`
4. `account.create_ad_creative(object_story_spec with lead_gen_form_id)`
5. `account.create_ad(adset_id, creative, status="PAUSED")`

## Lead Form Questions

```python
questions = [
    {"type": "FULL_NAME"},
    {"type": "EMAIL"},
    {"type": "PHONE"},
    # Custom: {"type": "CUSTOM", "key": "project_type", "label": "What type of project?"}
]
```

## Targeting Template

```json
{
    "geo_locations": {
        "cities": [{"key": "2420379", "name": "Dallas-Fort Worth", "region": "Texas"}]
    },
    "age_min": 25,
    "age_max": 65,
    "publisher_platforms": ["facebook", "instagram"],
    "facebook_positions": ["feed", "instant_article"],
    "instagram_positions": ["stream"]
}
```

## Insights Retrieval

```python
campaign.get_insights(
    fields=["date_start", "impressions", "clicks", "spend", "actions"],
    params={"date_preset": "last_7d", "time_increment": 1}
)
```

Lead count from actions: `action_type == "lead"`

## Common Error Codes

| Code | Meaning | Fix |
|------|---------|-----|
| #100 | Invalid parameter | Check field names/types |
| #200 | Permission error | Check token permissions |
| #2635 | Reach too low | Expand targeting |
| #1487930 | Account not found | Check act_ prefix |
| #17 | Rate limited | Wait/retry (SDK auto-retries) |

## Environment Variables

All prefixed with `FO_`:
- `FO_META_APP_ID`, `FO_META_APP_SECRET`
- `FO_META_AD_ACCOUNT_ID` (act_ prefix)
- `FO_META_API_VERSION` (default v21.0), `FO_PRIVACY_POLICY_URL`

Access tokens are per-customer page tokens stored in the `customers` DB table (never expire).
