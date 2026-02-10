"""Pydantic models for pipeline entities."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


# --- Campaign Config (form JSON) ---


class ConfigCustomer(BaseModel):
    name: str
    website_url: str | None = None
    business_description: str | None = None


class ConfigService(BaseModel):
    category: str
    avg_ticket_dollars: float | None = None
    special_ad_category: str | None = None  # HOUSING, CREDIT, EMPLOYMENT, or None


class ConfigGeo(BaseModel):
    type: str = "city"  # city | zip | radius
    value: str
    radius_miles: int | None = None
    location_type: str = "living_in"  # living_in | recently_in


class ConfigBudget(BaseModel):
    daily_dollars: float
    monthly_cap_dollars: float | None = None
    target_cpl_dollars: float | None = None
    max_cpl_dollars: float | None = None
    bid_strategy: str = "lowest_cost"  # lowest_cost | cost_cap | bid_cap


class ConfigOperatingHours(BaseModel):
    start: str = "08:00"
    end: str = "20:00"
    timezone: str = "America/Chicago"


class ConfigSchedule(BaseModel):
    start_date: str | None = None
    end_date: str | None = None
    operating_hours: ConfigOperatingHours = ConfigOperatingHours()
    operating_days: list[str] = ["Mon", "Tue", "Wed", "Thu", "Fri"]


class ConfigCreative(BaseModel):
    value_propositions: list[str]
    cta: str = "GET_QUOTE"
    image_urls: list[str] | None = None
    brand_voice: str = "professional"
    language: str = "en"
    prohibited_words: list[str] | None = None

    @field_validator("value_propositions")
    @classmethod
    def min_two_vps(cls, v: list[str]) -> list[str]:
        if len(v) < 2:
            raise ValueError("At least 2 value propositions required for A/B testing")
        return v


class ConfigLeadForm(BaseModel):
    questions: list[str] = ["full_name", "phone_number", "email"]
    thank_you_message: str | None = None
    privacy_policy_url: str | None = None


class ConfigTargeting(BaseModel):
    age_min: int = 25
    age_max: int = 65
    interest_keywords: str | None = None


class ConfigExperiment(BaseModel):
    num_variants: int = 3
    primary_metric: str = "cpl"
    min_effect_pct: int = 25


class ConfigContext(BaseModel):
    competitive_density: str | None = None  # low | medium | high
    competitors: str | None = None
    season: str | None = None  # peak | shoulder | off
    historical_cpl_dollars: float | None = None
    historical_conversion_rate: float | None = None
    max_leads_per_day: int | None = None


class ConfigMeta(BaseModel):
    form_version: str = "1.0"
    generated_at: str | None = None
    generated_by: str = "campaign-init-form"


class CampaignConfig(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    customer: ConfigCustomer
    service: ConfigService
    geo: ConfigGeo
    budget: ConfigBudget
    schedule: ConfigSchedule = ConfigSchedule()
    creative: ConfigCreative
    lead_form: ConfigLeadForm = ConfigLeadForm()
    targeting: ConfigTargeting = ConfigTargeting()
    experiment: ConfigExperiment = ConfigExperiment()
    context: ConfigContext = ConfigContext()
    meta: ConfigMeta = Field(default_factory=ConfigMeta, alias="_meta")


# --- Pipeline entities ---


class Customer(BaseModel):
    id: int | None = None
    name: str
    meta_page_id: str
    meta_page_name: str | None = None
    meta_page_access_token: str | None = None  # Long-lived page token (never expires)
    status: str = "active"  # active | inactive
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Brief(BaseModel):
    id: int | None = None
    customer_id: int
    name: str
    project_type: str
    geo: str
    budget_cents: int
    config_json: str | None = None
    status: str = "draft"  # draft | active | paused | archived
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Content(BaseModel):
    id: int | None = None
    brief_id: int
    headline: str
    primary_text: str
    image_url: str | None = None
    cta: str = "LEARN_MORE"
    targeting_json: str = "{}"
    status: str = "draft"  # draft | approved | rejected
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Campaign(BaseModel):
    id: int | None = None
    content_id: int
    meta_campaign_id: str | None = None
    meta_adset_id: str | None = None
    meta_ad_id: str | None = None
    meta_form_id: str | None = None
    status: str = "pending"  # pending | paused | active | error | archived
    error_message: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Lead(BaseModel):
    id: int | None = None
    campaign_id: int
    meta_lead_id: str
    full_name: str | None = None
    email: str | None = None
    phone: str | None = None
    form_data_json: str = "{}"
    created_at: datetime | None = None


class CampaignMetric(BaseModel):
    id: int | None = None
    campaign_id: int
    date: str  # YYYY-MM-DD
    impressions: int = 0
    clicks: int = 0
    spend_cents: int = 0
    leads_count: int = 0
    cpl_cents: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None
