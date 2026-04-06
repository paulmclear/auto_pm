"""
Application settings
====================
Single source of truth for all configuration.  Values are read from
environment variables (and ``.env`` via pydantic-settings) at first access.

Usage::

    from project_manager_agent.core.config import settings

    settings.chaser_frequency_days   # agent behaviour thresholds
    settings.openai_api_key          # secrets
    settings.reference_date          # simulated date (str in .env → date here)
"""

import datetime as dt

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # -- Secrets / API keys --------------------------------------------------
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""
    groq_api_key: str = ""
    pushover_user: str = ""
    pushover_token: str = ""
    sendgrid_api_key: str = ""
    serper_api_key: str = ""
    from_email: str = ""
    to_email: str = ""

    # -- LangSmith -----------------------------------------------------------
    langsmith_tracing: bool = True
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_api_key: str = ""
    langsmith_project: str = "project-manager"

    # -- LLM -----------------------------------------------------------------
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.0

    # -- Agent ----------------------------------------------------------------
    agent_sender_email: str = "agent@project-manager.local"
    reports_dir: str = "data/reports"

    # -- Agent behaviour thresholds ------------------------------------------
    chaser_frequency_days: int = 2
    advance_warning_days: int = 2
    escalation_threshold_days: int = 3
    re_escalation_gap_days: int = 3

    # -- Database -------------------------------------------------------------
    database_uri: str

    # -- Simulated date ------------------------------------------------------
    reference_date: dt.date = dt.date.today()

    @field_validator("reference_date", mode="before")
    @classmethod
    def _parse_reference_date(cls, v):
        if isinstance(v, str):
            return dt.date.fromisoformat(v)
        return v


settings = Settings()

# Convenience aliases — keeps existing import sites working with minimal churn.
CHASER_FREQUENCY_DAYS: int = settings.chaser_frequency_days
ADVANCE_WARNING_DAYS: int = settings.advance_warning_days
ESCALATION_THRESHOLD_DAYS: int = settings.escalation_threshold_days
RE_ESCALATION_GAP_DAYS: int = settings.re_escalation_gap_days
