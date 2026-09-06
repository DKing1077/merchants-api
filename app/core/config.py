from __future__ import annotations

import json
from pathlib import Path

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_SQLITE_DATABASE_PATH = Path(__file__).resolve().parents[2] / "merchants.db"


class Settings(BaseSettings):
    app_name: str = "Merchants API"
    app_version: str = "1.0.0"
    database_url: str = f"sqlite:///{_DEFAULT_SQLITE_DATABASE_PATH}"
    high_value_payment_threshold: int = 100_000
    merchant_velocity_window_seconds: int = 60
    merchant_velocity_limit: int = 10
    metrics_latency_buckets: tuple[float, ...] = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("metrics_latency_buckets", mode="before")
    @classmethod
    def parse_metrics_latency_buckets(cls, value):
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value.startswith("["):
                return tuple(float(bucket) for bucket in json.loads(stripped_value))
            return tuple(float(bucket.strip()) for bucket in value.split(",") if bucket.strip())
        return value


settings = Settings()
