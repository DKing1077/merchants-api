import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_metrics_latency_buckets_accept_json_array(monkeypatch):
    monkeypatch.setenv("METRICS_LATENCY_BUCKETS", "[0.1, 0.5, 1.0]")

    assert Settings().metrics_latency_buckets == (0.1, 0.5, 1.0)


def test_metrics_latency_buckets_accept_comma_delimited_values(monkeypatch):
    monkeypatch.setenv("METRICS_LATENCY_BUCKETS", "0.1,0.5,1.0")

    assert Settings().metrics_latency_buckets == (0.1, 0.5, 1.0)


def test_metrics_latency_buckets_reject_non_numeric_values(monkeypatch):
    monkeypatch.setenv("METRICS_LATENCY_BUCKETS", "[0.1, \"bad\", 1.0]")

    with pytest.raises(ValidationError, match="metrics_latency_buckets must be a comma-delimited string or JSON array of positive numbers"):
        Settings()


def test_metrics_latency_buckets_reject_non_increasing_values(monkeypatch):
    monkeypatch.setenv("METRICS_LATENCY_BUCKETS", "[0.5, 0.1]")

    with pytest.raises(ValidationError, match="metrics_latency_buckets must be strictly increasing"):
        Settings()
