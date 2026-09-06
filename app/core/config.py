from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Merchants API"
    app_version: str = "1.0.0"
    database_url: str = "sqlite:///./merchants.db"
    high_value_payment_threshold: int = 100_000
    merchant_velocity_window_seconds: int = 60
    merchant_velocity_limit: int = 10
    metrics_latency_buckets: tuple[float, ...] = (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("metrics_latency_buckets", mode="before")
    @classmethod
    def parse_metrics_latency_buckets(cls, value):
        if isinstance(value, str):
            return tuple(float(bucket.strip()) for bucket in value.split(",") if bucket.strip())
        return value


settings = Settings()
