"""Application configuration, loaded from environment variables.

Never hard-code secrets. All sensitive values come from the environment
(see .env.example at the repo root).
"""
from __future__ import annotations

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    app_name: str = "ULPF - Universal Log Pre-processing Framework"
    environment: str = Field(default="development")
    debug: bool = Field(default=True)
    api_prefix: str = "/api"

    # --- Database ---
    # SQLite default keeps the prototype runnable with zero infrastructure.
    # docker-compose overrides this with a PostgreSQL URL.
    database_url: str = Field(default="sqlite:///./ulpf.db")

    # --- Auth / security ---
    secret_key: str = Field(default="dev-only-insecure-change-me")
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 12

    # --- CORS ---
    cors_origins: List[str] = Field(default=["http://localhost:5173", "http://localhost:3000"])

    # --- Privacy / PII ---
    # HMAC key for deterministic pseudonymization. MUST be overridden in production.
    pii_hmac_key: str = Field(default="dev-only-pii-key-change-me")
    pii_default_mode: str = Field(default="DETERMINISTIC_HASH")  # OFF | MASK | DETERMINISTIC_HASH

    # --- Security shield ---
    # quarantine lines whose only findings are SUSPICIOUS injection indicators
    # (WEAPONIZED_LOG is always quarantined regardless of this flag)
    shield_quarantine_suspicious: bool = Field(default=True)

    # --- Ingestion limits ---
    max_upload_bytes: int = 50 * 1024 * 1024  # 50 MB
    allowed_upload_extensions: List[str] = Field(
        default=[".log", ".txt", ".json", ".jsonl", ".ndjson", ".csv", ".syslog"]
    )

    # --- Bootstrap admin (first run only) ---
    first_admin_email: str = Field(default="admin@ulpf.io")
    first_admin_password: str = Field(default="ChangeMe!123")

    # --- Local AI ---
    ai_provider: str = Field(default="local_template")  # local_template | disabled | ollama
    ollama_base_url: str = Field(default="http://localhost:11434")
    ollama_model: str = Field(default="llama3.2")
    ai_max_context_chars: int = Field(default=6000)
    ai_max_raw_input_chars: int = Field(default=16000)
    ai_ollama_timeout_seconds: int = Field(default=20)

    @field_validator("cors_origins", "allowed_upload_extensions", mode="before")
    @classmethod
    def _split_csv(cls, v):
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
