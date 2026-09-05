from __future__ import annotations

import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.api.routes import api_keys, ledger, payments, refunds, risk, timestamps, webhooks
from app.core.config import settings
from app.core.observability import MetricsStore, request_id_context, setup_logging
from app.db.database import engine

logger = setup_logging()

app = FastAPI(title=settings.app_name)
app.state.metrics = MetricsStore()


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started = time.perf_counter()

    route_path = request.scope.get("route").path if request.scope.get("route") else request.url.path
    route_key = f"{request.method} {route_path}"

    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        latency = time.perf_counter() - started
        app.state.metrics.observe(route_key, status_code, latency)
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": status_code,
                "latency_ms": round(latency * 1000, 2),
            },
        )
        request_id_context.reset(token)
        raise

    latency = time.perf_counter() - started
    app.state.metrics.observe(route_key, status_code, latency)
    response.headers["X-Request-ID"] = request_id

    logger.info(
        "request_complete",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": status_code,
            "latency_ms": round(latency * 1000, 2),
        },
    )

    request_id_context.reset(token)
    return response


@app.get("/")
def root():
    return {"message": "API is running"}


@app.get("/health")
def health_check():
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected", "version": settings.app_version}
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "disconnected", "version": settings.app_version},
        )


@app.get("/metrics")
def metrics():
    return PlainTextResponse(
        app.state.metrics.render(),
        media_type="text/plain; version=0.0.4",
    )


for router, prefix, tags in [
    (payments.router, "/v1/payment_intents", ["payment_intents"]),
    (refunds.router, "/v1/refunds", ["refunds"]),
    (webhooks.router, "/v1/webhooks", ["webhooks"]),
    (ledger.router, "/v1", ["ledger"]),
    (risk.router, "/v1", ["risk"]),
    (timestamps.router, "/v1/timestamps", ["timestamps"]),
]:
    app.include_router(router, prefix=prefix, tags=tags)

app.include_router(api_keys.router)