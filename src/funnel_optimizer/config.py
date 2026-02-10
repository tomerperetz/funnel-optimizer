"""Configuration via environment variables (FO_ prefix)."""

from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"env_prefix": "FO_"}

    # Meta Ads API
    meta_app_id: str = ""
    meta_app_secret: str = ""
    meta_ad_account_id: str = ""  # act_XXXXXXXXX
    meta_api_version: str = "v21.0"

    # Lead form
    privacy_policy_url: str = ""

    # Database
    db_path: str = "data/pipeline.db"

    def db_abs_path(self) -> Path:
        """Return absolute path to the database file."""
        p = Path(self.db_path)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[2] / p
        return p


def get_settings() -> Settings:
    """Load settings from .env and environment."""
    return Settings(_env_file=".env", _env_file_encoding="utf-8")
