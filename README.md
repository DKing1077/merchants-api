# Merchants API

Merchants API is a FastAPI-based backend that processes payment transactions, manages refunds, tracks double-entry ledger accounts, and delivers signed webhook events to registered merchant endpoints.

## What this project does

- Accepts API-key-authenticated requests from merchants
- Creates and captures payment intents with idempotency protection
- Applies real-time risk scoring and velocity checks before processing payments
- Issues and tracks refunds against captured payment intents
- Maintains a double-entry ledger with accounts, entries, and postings
- Emits structured events and delivers them to merchant webhook endpoints with exponential-backoff retries
- Exposes Prometheus-compatible metrics and structured JSON logs per request

## Backend concepts covered

- FastAPI application structure with modular APIRouters
- RESTful route design with JSON request/response handling
- API key authentication with hashed key storage and admin/merchant role separation
- SQLAlchemy ORM modeling with relationships, foreign keys, and column properties
- Idempotency key enforcement to prevent duplicate payment and refund creation
- Risk scoring and merchant velocity-window rate limiting
- Double-entry ledger design with accounts, entries, and postings
- Event-driven webhook dispatch with signed payloads and retry scheduling
- Pydantic schema validation for all request and response bodies
- Structured logging with per-request context injection
- In-process Prometheus-style metrics collection and `/metrics` exposition
- Database migration scaffolding with Alembic
- PostgreSQL integration via SQLAlchemy and JSONB columns for flexible payload storage

## Project structure

```
app/
├── api/
│   └── routes/        # Route handlers: payments, refunds, ledger, risk, webhooks, api_keys, timestamps
├── auth/              # API key dependency and merchant identity resolution
├── core/
│   ├── config.py      # Settings loaded from environment
│   ├── exceptions.py  # Custom exception types
│   └── observability.py  # Structured logging, request-id context, and MetricsStore
├── db/
│   ├── database.py    # SQLAlchemy engine, session factory, and Base
│   └── models/
│       └── models.py  # ORM models: PaymentIntent, Refunds, Event, WebhookEndpoint,
│                      #   WebhookDispatch, WebhookDelivery, LedgerAccount,
│                      #   LedgerEntry, LedgerPosting, ApiKey
├── schemas/           # Pydantic request/response schemas per domain
├── services/          # Business logic: payment, refund, ledger, risk, dispatch, delivery, events
├── tests/             # Pytest test suite
└── main.py            # FastAPI application factory, middleware, and router registration

alembic/               # Database migration scripts
```