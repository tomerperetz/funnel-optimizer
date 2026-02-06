"""Pydantic models for pipeline entities."""

from datetime import datetime

from pydantic import BaseModel


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
