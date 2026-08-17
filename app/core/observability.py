from __future__ import annotations
import contextvars
import logging
from collections import defaultdict

from app.core.config import settings

request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id",
    default="-",
)


class RequestIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_context.get()
        return True


class MetricsStore:
    def __init__(self) -> None:
        self.requests = defaultdict(int)
        self.errors = defaultdict(int)
        self.latency_count = defaultdict(int)
        self.latency_sum = defaultdict(float)
        self.latency_buckets = defaultdict(lambda: defaultdict(int))

    def observe(self, route_key: str, status_code: int, latency_seconds: float) -> None:
        self.requests[route_key] += 1
        self.latency_count[route_key] += 1
        self.latency_sum[route_key] += latency_seconds
        if status_code >= 400:
            self.errors[route_key] += 1
        for bucket in settings.metrics_latency_buckets:
            if latency_seconds <= bucket:
                self.latency_buckets[route_key][bucket] += 1

    def render(self) -> str:
        lines = [
            "# HELP merchants_api_requests_total Total requests by route",
            "# TYPE merchants_api_requests_total counter",
        ]
        for route_key, value in sorted(self.requests.items()):
            method, path = route_key.split(" ", 1)
            lines.append(
                f'merchants_api_requests_total{{method="{method}",path="{path}"}} {value}'
            )

        lines.extend(
            [
                "# HELP merchants_api_errors_total Total error responses by route",
                "# TYPE merchants_api_errors_total counter",
            ]
        )
        for route_key, value in sorted(self.errors.items()):
            method, path = route_key.split(" ", 1)
            lines.append(
                f'merchants_api_errors_total{{method="{method}",path="{path}"}} {value}'
            )

        lines.extend(
            [
                "# HELP merchants_api_request_latency_seconds_sum Request latency sum by route",
                "# TYPE merchants_api_request_latency_seconds_sum counter",
            ]
        )
        for route_key, value in sorted(self.latency_sum.items()):
            method, path = route_key.split(" ", 1)
            lines.append(
                f'merchants_api_request_latency_seconds_sum{{method="{method}",path="{path}"}} {value}'
            )

        lines.extend(
            [
                "# HELP merchants_api_request_latency_seconds_count Request latency count by route",
                "# TYPE merchants_api_request_latency_seconds_count counter",
            ]
        )
        for route_key, value in sorted(self.latency_count.items()):
            method, path = route_key.split(" ", 1)
            lines.append(
                f'merchants_api_request_latency_seconds_count{{method="{method}",path="{path}"}} {value}'
            )

        lines.extend(
            [
                "# HELP merchants_api_request_latency_seconds_bucket Request latency buckets by route",
                "# TYPE merchants_api_request_latency_seconds_bucket histogram",
            ]
        )
        for route_key, buckets in sorted(self.latency_buckets.items()):
            method, path = route_key.split(" ", 1)
            running_total = 0
            for bucket in settings.metrics_latency_buckets:
                running_total += buckets.get(bucket, 0)
                lines.append(
                    "merchants_api_request_latency_seconds_bucket"
                    f'{{method="{method}",path="{path}",le="{bucket}"}} {running_total}'
                )
            lines.append(
                "merchants_api_request_latency_seconds_bucket"
                f'{{method="{method}",path="{path}",le="+Inf"}} {self.latency_count[route_key]}'
            )
        return "\n".join(lines) + "\n"


def setup_logging() -> logging.Logger:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s request_id=%(request_id)s %(message)s",
        )
    request_filter = RequestIdFilter()
    for handler in root.handlers:
        handler.addFilter(request_filter)
    root.setLevel(logging.INFO)
    return logging.getLogger("merchants_api")
