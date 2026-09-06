from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_SQLITE_DATABASE_PATH = Path(__file__).resolve().parents[2] / "merchants.db"


def _normalize_metrics_latency_buckets(value) -> tuple[float, ...]:
    try:
        buckets = tuple(float(bucket) for bucket in value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            "metrics_latency_buckets must be a comma-delimited string or JSON array of positive numbers"
        ) from exc
    if not buckets or any(bucket <= 0 for bucket in buckets):
        raise ValueError("metrics_latency_buckets must contain positive values")
    if any(current >= following for current, following in zip(buckets, buckets[1:])):
        raise ValueError("metrics_latency_buckets must be strictly increasing")
    return buckets


class Settings(BaseSettings):
    app_name: str = "Merchants API"
    app_version: str = "1.0.0"
    database_url: str = f"sqlite:///{_DEFAULT_SQLITE_DATABASE_PATH}"
    high_value_payment_threshold: int = 100_000
    merchant_velocity_window_seconds: int = 60
    merchant_velocity_limit: int = 10
    metrics_latency_buckets: Annotated[tuple[float, ...], NoDecode] = (
        0.01,
        0.05,
        0.1,
        0.25,
        0.5,
        1.0,
        2.5,
        5.0,
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", validate_default=True)

    @field_validator("metrics_latency_buckets", mode="before")
    @classmethod
    def parse_metrics_latency_buckets(cls, value):
        if isinstance(value, str):
            stripped_value = value.strip()
            if stripped_value.startswith("["):
                return _normalize_metrics_latency_buckets(json.loads(stripped_value))
            return _normalize_metrics_latency_buckets(
                bucket.strip() for bucket in value.split(",") if bucket.strip()
            )
        return _normalize_metrics_latency_buckets(value)


settings = Settings()
