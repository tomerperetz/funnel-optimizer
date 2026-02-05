"""Thin wrapper around the Meta (Facebook) Marketing API."""

import logging
import os
import tempfile
import urllib.request

from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adset import AdSet
from facebook_business.adobjects.campaign import Campaign
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adimage import AdImage
from facebook_business.adobjects.leadgenform import LeadgenForm
from facebook_business.api import FacebookAdsApi

from funnel_optimizer.config import Settings

logger = logging.getLogger(__name__)


class MetaAdsClient:
    """Meta Marketing API operations. Thin HTTP layer — no business logic."""

    def __init__(self, settings: Settings):
        self.settings = settings
        FacebookAdsApi.init(
            app_id=settings.meta_app_id,
            app_secret=settings.meta_app_secret,
            access_token=settings.meta_access_token,
            api_version=settings.meta_api_version,
        )
        self.account = AdAccount(settings.meta_ad_account_id)

    # --- Connectivity check ---

    def check_connection(self) -> dict:
        """Verify credentials by reading ad account info. Returns account name + id."""
        fields = ["name", "account_id", "account_status", "currency", "timezone_name"]
        info = self.account.api_get(fields=fields)
        return {f: info.get(f) for f in fields}

    # --- Image upload ---

    def upload_image(self, image_path: str) -> str:
        """Upload an image file to the ad account. Returns image_hash."""
        img = AdImage(parent_id=self.settings.meta_ad_account_id)
        img[AdImage.Field.filename] = image_path
        img.remote_create()
        image_hash = img[AdImage.Field.hash]
        logger.info("Uploaded image %s -> hash %s", image_path, image_hash)
        return image_hash

    def upload_image_from_url(self, url: str) -> str:
        """Download an image from URL and upload to Meta. Returns image_hash."""
        suffix = os.path.splitext(url.split("?")[0])[-1] or ".jpg"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            urllib.request.urlretrieve(url, tmp.name)
            image_hash = self.upload_image(tmp.name)
        os.unlink(tmp.name)
        return image_hash

    # --- Campaign ---

    def create_campaign(self, name: str, objective: str = "OUTCOME_LEADS") -> dict:
        """Create a campaign in PAUSED status with ad set level budgets. Returns dict with id."""
        params = {
            "name": name,
            "objective": objective,
            "status": "PAUSED",
            "special_ad_categories": [],
            "is_using_l3_scheduling": False,
            "smart_promotion_type": "GUIDED_CREATION",
        }
        result = self.account.create_campaign(params=params)
        logger.info("Created campaign %s", result["id"])
        return {"id": result["id"]}

    # --- Ad Set ---

    def create_adset(
        self,
        campaign_id: str,
        name: str,
        daily_budget_cents: int,
        targeting: dict,
        page_id: str | None = None,
    ) -> dict:
        """Create an ad set. Returns dict with id."""
        # Ensure targeting has at least geo_locations (required by Meta)
        if not targeting or not targeting.get("geo_locations"):
            targeting = {
                "geo_locations": {"countries": ["IL"]},  # Default to Israel for testing
                "age_min": 18,
                "age_max": 65,
            }
        params = {
            "campaign_id": campaign_id,
            "name": name,
            "billing_event": "IMPRESSIONS",
            "optimization_goal": "LEAD_GENERATION",
            "bid_strategy": "LOWEST_COST_WITHOUT_CAP",
            "daily_budget": daily_budget_cents,
            "targeting": targeting,
            "status": "PAUSED",
            "promoted_object": {"page_id": page_id or self.settings.meta_page_id},
            "destination_type": "ON_AD",
        }
        result = self.account.create_ad_set(params=params)
        logger.info("Created adset %s", result["id"])
        return {"id": result["id"]}

    # --- Lead Form ---

    def create_lead_form(
        self,
        name: str,
        questions: list[dict] | None = None,
        privacy_policy_url: str | None = None,
        page_id: str | None = None,
    ) -> dict:
        """Create a lead gen form on the page. Returns dict with id."""
        if questions is None:
            questions = [
                {"type": "FULL_NAME"},
                {"type": "EMAIL"},
                {"type": "PHONE"},
            ]
        params = {
            "name": name,
            "questions": questions,
            "privacy_policy": {
                "url": privacy_policy_url or self.settings.privacy_policy_url,
            },
            "follow_up_action_url": privacy_policy_url or self.settings.privacy_policy_url,
        }
        pid = page_id or self.settings.meta_page_id
        from facebook_business.adobjects.page import Page
        page = Page(pid)
        result = page.create_lead_gen_form(params=params)
        logger.info("Created lead form %s", result["id"])
        return {"id": result["id"]}

    # --- Creative + Ad ---

    def create_creative(
        self,
        name: str,
        page_id: str | None = None,
        headline: str = "",
        primary_text: str = "",
        cta: str = "LEARN_MORE",
        form_id: str = "",
        image_hash: str = "",
        link: str = "",
    ) -> dict:
        """Create an ad creative for lead gen. Returns dict with id."""
        pid = page_id or self.settings.meta_page_id
        # Lead gen ads require an external link (not facebook.com)
        external_link = link or self.settings.privacy_policy_url
        link_data = {
            "message": primary_text,
            "name": headline,
            "call_to_action": {
                "type": cta,
                "value": {"lead_gen_form_id": form_id} if form_id else {"link": external_link},
            },
            "link": external_link,
        }
        if image_hash:
            link_data["image_hash"] = image_hash
        params = {
            "name": name,
            "object_story_spec": {
                "page_id": pid,
                "link_data": link_data,
            },
        }
        result = self.account.create_ad_creative(params=params)
        logger.info("Created creative %s", result["id"])
        return {"id": result["id"]}

    def create_ad(self, adset_id: str, creative_id: str, name: str) -> dict:
        """Create an ad in PAUSED status. Returns dict with id."""
        params = {
            "adset_id": adset_id,
            "creative": {"creative_id": creative_id},
            "name": name,
            "status": "PAUSED",
        }
        result = self.account.create_ad(params=params)
        logger.info("Created ad %s", result["id"])
        return {"id": result["id"]}

    # --- Status Management ---

    def update_campaign_status(self, campaign_id: str, status: str) -> None:
        """Update campaign status (ACTIVE or PAUSED)."""
        campaign = Campaign(campaign_id)
        campaign.api_update(params={"status": status})
        logger.info("Campaign %s set to %s", campaign_id, status)

    def update_adset_status(self, adset_id: str, status: str) -> None:
        """Update ad set status."""
        adset = AdSet(adset_id)
        adset.api_update(params={"status": status})
        logger.info("Adset %s set to %s", adset_id, status)

    # --- Leads ---

    def get_leads(self, form_id: str, limit: int = 500) -> list[dict]:
        """Fetch leads from a lead gen form. Returns list of lead dicts."""
        form = LeadgenForm(form_id)
        leads = form.get_leads(fields=["id", "created_time", "field_data"])
        results = []
        for lead in leads:
            field_data = {f["name"]: f["values"][0] for f in lead.get("field_data", [])}
            results.append({
                "id": lead["id"],
                "created_time": lead.get("created_time"),
                "full_name": field_data.get("full_name", ""),
                "email": field_data.get("email", ""),
                "phone": field_data.get("phone_number", ""),
                "form_data": field_data,
            })
        return results

    # --- Insights ---

    def get_campaign_insights(self, campaign_id: str, date_preset: str = "last_7d") -> list[dict]:
        """Fetch daily insights for a campaign. Returns list of daily metric dicts."""
        campaign = Campaign(campaign_id)
        params = {
            "date_preset": date_preset,
            "time_increment": 1,
        }
        fields = ["date_start", "impressions", "clicks", "spend", "actions"]
        insights = campaign.get_insights(fields=fields, params=params)
        results = []
        for row in insights:
            leads_count = 0
            for action in row.get("actions", []):
                if action["action_type"] == "lead":
                    leads_count = int(action["value"])
                    break
            spend_cents = int(float(row.get("spend", "0")) * 100)
            results.append({
                "date": row["date_start"],
                "impressions": int(row.get("impressions", 0)),
                "clicks": int(row.get("clicks", 0)),
                "spend_cents": spend_cents,
                "leads_count": leads_count,
                "cpl_cents": spend_cents // leads_count if leads_count > 0 else 0,
            })
        return results
