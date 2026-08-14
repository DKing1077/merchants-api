from __future__ import annotations

import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

import app.db.models.models
from app.api.routes import api_keys, ledger, payments, refunds, risk, timestamps, webhooks
from app.core.config import settings
from app.core.observability import MetricsStore, request_id_context, setup_logging
from app.db.database import Base, create_database_if_missing, engine

create_database_if_missing()
logger = setup_logging()
app = FastAPI(title=settings.app_name)
app.state.metrics = MetricsStore()


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())
    token = request_id_context.set(request_id)
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        latency = time.perf_counter() - started
        route_path = request.scope.get("route").path if request.scope.get("route") else request.url.path
        route_key = f"{request.method} {route_path}"
        app.state.metrics.observe(route_key, 500, latency)
        logger.exception(
            "request_failed",
            extra={
                "method": request.method,
                "path": request.url.path,
                "latency_ms": round(latency * 1000, 2),
                "status_code": 500,
            },
        )
        request_id_context.reset(token)
        raise
    latency = time.perf_counter() - started
    route_path = request.scope.get("route").path if request.scope.get("route") else request.url.path
    route_key = f"{request.method} {route_path}"
    app.state.metrics.observe(route_key, response.status_code, latency)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_complete",
        extra={
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
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
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "db": "disconnected", "version": settings.app_version},
        )
    return {"status": "ok", "db": "connected", "version": settings.app_version}


@app.get("/metrics")
def metrics():
    return PlainTextResponse(app.state.metrics.render(), media_type="text/plain; version=0.0.4")


app.include_router(payments.router, prefix="/v1/payment_intents", tags=["payment_intents"])
app.include_router(refunds.router, prefix="/v1/refunds", tags=["refunds"])
app.include_router(webhooks.router, prefix="/v1/webhooks", tags=["webhooks"])
app.include_router(ledger.router, prefix="/v1", tags=["ledger"])
app.include_router(risk.router, prefix="/v1", tags=["risk"])
app.include_router(timestamps.router, prefix="/v1/timestamps", tags=["timestamps"])
app.include_router(api_keys.router)

Base.metadata.create_all(bind=engine)
