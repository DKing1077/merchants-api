# Merchants API

A production-style REST API built with **FastAPI** and **PostgreSQL** that models a payments processing platform — covering payment intents, refunds, double-entry ledger accounting, risk scoring, webhook delivery, and API key authentication.

This project is primarily a learning exercise designed to put real backend engineering and API design concepts into practice in one cohesive codebase.

---

## Table of Contents

- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Running Tests](#running-tests)
- [API Overview](#api-overview)
- [Backend Engineering Concepts Covered](#backend-engineering-concepts-covered)
  - [API Design](#api-design)
  - [Authentication & Authorization](#authentication--authorization)
  - [Database & ORM](#database--orm)
  - [Business Logic Patterns](#business-logic-patterns)
  - [Event-Driven Architecture](#event-driven-architecture)
  - [Observability](#observability)
  - [Testing](#testing)
  - [Containerization](#containerization)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | [FastAPI](https://fastapi.tiangolo.com/) |
| Database | PostgreSQL 16 (SQLite in tests) |
| ORM & Migrations | SQLAlchemy + Alembic |
| HTTP Client | httpx |
| Validation | Pydantic v2 |
| Linting / Formatting | Ruff + Black + pre-commit |
| Containerization | Docker + Docker Compose |
| Testing | pytest + pytest-cov |

---

## Project Structure

```
app/
├── main.py              # App entry point — middleware, routers, health/metrics routes
├── api/routes/          # One file per resource group (payments, refunds, webhooks, ledger, …)
├── services/            # Business logic layer, called by routes
├── db/
│   ├── database.py      # Engine, session factory, base class
│   └── models/          # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response models
├── auth/
│   └── dependencies.py  # API key auth — FastAPI dependency injection
└── core/
    ├── config.py        # Pydantic settings (env-var driven)
    ├── exceptions.py    # Custom exception classes
    └── observability.py # Structured logging + in-memory metrics store

alembic/                 # Database migrations
tests/                   # pytest test suite
docker-compose.yaml
Dockerfile
```

---

## Getting Started

### With Docker (recommended)

```bash
docker compose up --build
```

This starts a Postgres 16 container, runs `alembic upgrade head` to apply migrations, then starts the API on `http://localhost:8000`.

### Locally (no Docker)

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Set environment variables (copy and edit as needed)
export DATABASE_URL="******localhost:5432/merchants"

# Apply migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
# or
./dev.sh
```

Interactive docs are available at `http://localhost:8000/docs`.

---

## Running Tests

Tests use an **in-memory SQLite database** — no Postgres required.

```bash
PYTHONPATH=. pytest app/tests -q

# With coverage
make test-cov
```

---

## API Overview

All routes are prefixed with `/v1`. Most require an `Authorization` header containing a valid API key.

| Resource | Key Endpoints |
|---|---|
| **Payment Intents** | `POST /v1/payment_intents`, confirm → capture → cancel lifecycle |
| **Refunds** | `POST /v1/refunds/payment_intents/{id}/refunds`, confirm / decline / cancel |
| **Webhooks** | CRUD on `/v1/webhooks/endpoints`, delivery history, manual dispatch trigger |
| **Ledger** | `POST /v1/ledger/accounts`, double-entry entries, balance sheet |
| **Risk** | `GET /v1/admin/risk/summary` — admin-only aggregate risk view |
| **API Keys** | `POST /v1/api_keys` — create a new API key (raw key returned once) |
| **Timestamps** | `GET /v1/timestamps/payment_intents/{id}/created_at` and `updated_at` |

Base utility routes:

| Route | Purpose |
|---|---|
| `GET /` | Liveness check |
| `GET /health` | DB connectivity + version |
| `GET /metrics` | Prometheus-style text metrics |

---

## Backend Engineering Concepts Covered

### API Design

- **RESTful resource modeling** — resources are nouns (`/payment_intents`, `/refunds`), actions use HTTP verbs or verb-suffixed sub-routes (`/confirm`, `/capture`, `/cancel`).
- **Cursor-based pagination** — list endpoints accept `limit` and `starting_after` (an opaque cursor) instead of page numbers, matching the Stripe API pattern and avoiding offset drift on live data.
- **Filtering** — list endpoints support query-string filters by `status`, `currency`, `created_after`, `created_before`, and `payment_intent_id`.
- **Idempotency keys** — `POST /v1/payment_intents` and `POST /v1/refunds/…` accept an `Idempotency-Key` header. If a request with the same key from the same merchant arrives again, the original response is returned without re-running business logic. This prevents duplicate charges caused by network retries.
- **Versioned routing** — all resource routes live under `/v1`, making a future `/v2` non-breaking.
- **Input validation with Pydantic** — request bodies are declared as Pydantic models. Currency codes are normalized to lowercase and constrained to exactly 3 characters. Invalid payloads return structured 422 errors automatically.

### Authentication & Authorization

- **API key authentication** — callers pass a raw API key in the `Authorization` header. The server hashes it with SHA-256 and compares it to the stored hash, so plaintext keys are never persisted. The raw key is returned exactly once at creation time.
- **Merchant isolation** — every authenticated call resolves a `merchant_id` from the API key. All reads and writes are scoped to that merchant, preventing one merchant from accessing another's data.
- **Role-based access (admin flag)** — `ApiKey.is_admin` enables admin-only endpoints (risk summary, flagged review, manual dispatch) that return cross-merchant aggregates.
- **FastAPI dependency injection** — `require_api_key` and `require_admin_api_key` are reusable FastAPI `Depends` functions injected per route, keeping auth logic out of route handlers.

### Database & ORM

- **SQLAlchemy ORM** — models, relationships, and queries are all expressed in Python. No raw SQL in application code except the `SELECT 1` health check.
- **Alembic migrations** — schema changes are tracked as versioned migration scripts (`alembic/versions/`). The Docker entrypoint runs `alembic upgrade head` before starting the server so the schema is always current.
- **Session-per-request pattern** — `get_db()` is a generator that yields a `SessionLocal` instance and closes it in a `finally` block, preventing connection leaks.
- **JSONB columns** — `Event.payload`, `WebhookEndpoint.event_types`, and related columns use Postgres `JSONB` for flexible schema-less storage inside an otherwise relational model.
- **Computed properties** — `PaymentIntent.total_refunded` is a Python `@property` that sums confirmed refund amounts at query time rather than storing a derived value.

### Business Logic Patterns

- **Finite state machines** — payment intents follow a strict lifecycle: `requires_payment_method → requires_capture → succeeded | canceled`. Refunds follow `pending → confirmed | declined | canceled`. Services reject transitions that skip states.
- **Double-entry ledger accounting** — every `LedgerEntry` requires at least two `LedgerPosting` rows whose amounts sum to zero (debits equal credits). A capture credits the merchant payable account and debits the cash account; a confirmed refund reverses that entry.
- **Risk scoring** — `risk_service.calculate_risk_score()` combines payment amount, whether the merchant has made prior payments, and recent velocity into a 0–100 score. Scores above a threshold auto-flag the payment intent for manual review.
- **Velocity rate limiting** — `enforce_velocity_limit()` counts a merchant's payment intents within a rolling time window and raises a `RiskRateLimitError` (HTTP 429) when the limit is exceeded.
- **Service layer separation** — routes are thin: they validate input, call a service function, and return a response. All business logic, DB writes, and error raising live in `app/services/`.

### Event-Driven Architecture

- **Event sourcing (lightweight)** — every significant state change (payment created, captured, confirmed, refund declined, etc.) inserts an `Event` row with a `type`, `object_id`, and JSON `payload`. This provides an audit trail and is the trigger for webhook delivery.
- **Webhook fanout** — `create_dispatches_for_event()` queries active `WebhookEndpoint` rows for the merchant, filters by `event_types`, and creates a `WebhookDispatch` row per matching endpoint.
- **Webhook delivery with retries** — `process_pending_dispatches()` (triggered manually via `POST /v1/webhooks/dispatches/process`) iterates due dispatches, POSTs JSON to the endpoint URL via `httpx`, and records each attempt in `WebhookDelivery`. Failed deliveries are retried up to 3 times with a 5-minute backoff delay.
- **HMAC request signing** — outbound webhook payloads are signed with `HMAC-SHA256` using a per-endpoint secret. Callers can verify authenticity with `verify_webhook_signature()` using `hmac.compare_digest` to prevent timing attacks.

### Observability

- **Structured logging** — every log call includes `extra` fields (`method`, `path`, `status_code`, `latency_ms`) emitted as JSON. This makes logs machine-parseable in log aggregation systems (Datadog, Loki, etc.).
- **Request ID propagation** — a UUID is generated per request and attached to the response as `X-Request-ID`. A `contextvars.ContextVar` holds the ID so it can be injected into log records emitted deep in the call stack.
- **In-memory Prometheus-style metrics** — `MetricsStore` tracks request counts and latency histograms per route, exposed at `GET /metrics` in the Prometheus text format. No external metrics library required.
- **Health endpoint** — `GET /health` executes `SELECT 1` against Postgres and returns the app version, suitable for use as a Docker or Kubernetes health probe.

### Testing

- **In-memory SQLite override** — `conftest.py` overrides `DATABASE_URL` to `sqlite:///:memory:` so tests run without a database server. `JSONB` columns are monkeypatched to standard `JSON` for SQLite compatibility.
- **Test client fixture** — `TestClient` wraps the FastAPI app; two API keys (normal + admin) are seeded in `conftest.py` for use in tests.
- **Lifecycle integration tests** — tests exercise the full payment lifecycle: create → confirm → capture → create refund → confirm refund, and assert that ledger balances net to zero after a round-trip.
- **Edge case coverage** — dedicated tests for idempotency, velocity limits (429), partial capture, refund-exceeds-captured-amount rejection, high-value auto-flagging, and webhook signature verification.

### Containerization

- **Multi-service Docker Compose** — `docker-compose.yaml` defines an `app` service (this repo) and a `postgres:16` service. The app depends on a Postgres health check before starting.
- **Bind mount for hot reload** — the repo directory is mounted into `/app` in the container so code changes are reflected without rebuilding the image during development.
- **Migration-first startup** — the compose `command` runs `alembic upgrade head && uvicorn app.main:app --reload`, ensuring the schema is always up to date before the server accepts traffic.