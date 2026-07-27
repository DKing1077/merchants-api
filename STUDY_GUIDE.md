# Merchants API — Study Guide

A complete reference for the project's directory layout, each layer's role, and the exact code patterns used throughout.

---

## 1. Project Directory Tree

```
merchants-api/
├── app/
│   ├── main.py                          # App entry point — wires everything together
│   ├── api/
│   │   └── routes/
│   │       └── payment_intents.py       # HTTP route handlers for /v1/payment_intents
│   ├── core/
│   │   └── exceptions.py               # Custom domain exception classes
│   ├── db/
│   │   ├── database.py                  # SQLAlchemy engine, session factory, get_db()
│   │   └── models/
│   │       ├── __init__.py              # Re-exports models so main.py can import them
│   │       └── payment_intent.py        # ORM table definition for payment_intents
│   ├── schemas/
│   │   └── payment_intents.py           # Pydantic request/response schemas + enum
│   ├── services/
│   │   └── payment_service.py           # Business logic — all DB reads/writes live here
│   └── tests/
│       └── test_payment_intents.py      # pytest tests using FastAPI TestClient
├── notes/                               # Personal reference / scratch notes
│   ├── layout.txt                       # Plain-English description of each layer
│   ├── fastapi_sample.py                # FastAPI quick-reference snippets
│   ├── fastapi_sample2.py               # SQLAlchemy + Celery + async snippets
│   ├── async.py                         # asyncio basics
│   └── websockets.py                    # WebSocket patterns
├── curl.txt                             # Ready-to-run curl commands for manual testing
├── dev.sh                               # One-command app launcher (uvicorn)
├── instructions.txt                     # Full feature roadmap and build order
├── projectidea                          # Original project concept notes
├── requirements.txt                     # Python dependencies
└── README.md                            # One-line project description
```

---

## 2. Layer Responsibilities (what goes where)

| Layer | File location | What belongs here |
|---|---|---|
| **main.py** | `app/main.py` | Create `FastAPI()` app, create DB tables, mount routers |
| **Routes** | `app/api/routes/` | HTTP handlers (`@router.get/post`), read path params/body, call services, map exceptions → HTTP status codes |
| **Schemas** | `app/schemas/` | Pydantic `BaseModel` for request input and response shape; field validators; enums |
| **Services** | `app/services/` | All business logic; DB queries via `Session`; raise domain exceptions |
| **Models** | `app/db/models/` | SQLAlchemy ORM class, column definitions, table name |
| **Database** | `app/db/database.py` | Engine, `SessionLocal`, `Base`, `get_db()` dependency |
| **Exceptions** | `app/core/exceptions.py` | Plain Python `Exception` subclasses (no HTTP knowledge) |
| **Tests** | `app/tests/` | pytest functions using `TestClient`; one file per resource |

**Golden rule (from `instructions.txt`):**
> model → schema → service → routes → tests

---

## 3. Key Code — File by File

### `app/main.py`
```python
from fastapi import FastAPI
from app.api.routes import payment_intents
from app.core.config import settings
from app.db.database import Base, engine
from app.db.models import PaymentIntent          # must import so Base knows the table

Base.metadata.create_all(bind=engine)            # creates tables on startup

app = FastAPI(title=settings.app_name)

@app.get("/")
def root():
    return {"message": "API is running"}

app.include_router(
    payment_intents.router,
    prefix="/v1/payment_intents",
    tags=["payment_intents"],
)
```

### `app/db/database.py`
```python
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():                # FastAPI dependency — yields a session, always closes it
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### `app/db/models/payment_intent.py`
```python
from sqlalchemy import Column, Integer, String
from app.db.database import Base

class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id       = Column(String,    primary_key=True, index=True)
    amount   = Column(Integer,   nullable=False)
    currency = Column(String(3), nullable=False)
    status   = Column(String,    nullable=False)
```

### `app/db/models/__init__.py`
```python
from app.db.models.payment_intent import PaymentIntent   # re-export so main.py works
```

### `app/schemas/payment_intents.py`
```python
from enum import Enum
from pydantic import BaseModel, Field, field_validator

class PaymentIntentStatus(str, Enum):
    requires_payment_method = "requires_payment_method"
    succeeded = "succeeded"
    canceled  = "canceled"

class PaymentIntentCreate(BaseModel):
    amount:   int = Field(..., gt=0, description="Amount in smallest currency unit")
    currency: str = Field(..., min_length=3, max_length=3, description="ISO currency code")

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: str) -> str:
        return value.strip().lower()

class PaymentIntentResponse(BaseModel):
    id:       str
    amount:   int
    currency: str
    status:   PaymentIntentStatus
```

### `app/core/exceptions.py`
```python
class PaymentIntentNotFoundError(Exception):
    pass

class InvalidPaymentIntentStateError(Exception):
    pass
```

### `app/services/payment_service.py`
```python
from sqlalchemy.orm import Session
from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.db.models.payment_intent import PaymentIntent
from app.schemas.payment_intents import PaymentIntentStatus

def create_payment_intent(db: Session, amount: int, currency: str):
    count = db.query(PaymentIntent).count()
    pi = PaymentIntent(
        id=f"pi_{count + 1}",
        amount=amount,
        currency=currency,
        status=PaymentIntentStatus.requires_payment_method.value,
    )
    db.add(pi); db.commit(); db.refresh(pi)
    return pi

def get_payment_intent(db: Session, payment_intent_id: str):
    pi = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent_id).first()
    if not pi:
        raise PaymentIntentNotFoundError(f"Payment intent {payment_intent_id} not found")
    return pi

def list_payment_intents(db: Session):
    return db.query(PaymentIntent).all()

def confirm_payment_intent(db: Session, payment_intent_id: str):
    pi = get_payment_intent(db, payment_intent_id)
    if pi.status == PaymentIntentStatus.canceled.value:
        raise InvalidPaymentIntentStateError(f"Cannot confirm canceled payment intent {payment_intent_id}")
    pi.status = PaymentIntentStatus.succeeded.value
    db.commit(); db.refresh(pi)
    return pi

def cancel_payment_intent(db: Session, payment_intent_id: str):
    pi = get_payment_intent(db, payment_intent_id)
    if pi.status == PaymentIntentStatus.succeeded.value:
        raise InvalidPaymentIntentStateError(f"Cannot cancel succeeded payment intent {payment_intent_id}")
    pi.status = PaymentIntentStatus.canceled.value
    db.commit(); db.refresh(pi)
    return pi
```

### `app/api/routes/payment_intents.py`
```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.exceptions import InvalidPaymentIntentStateError, PaymentIntentNotFoundError
from app.db.database import get_db
from app.schemas.payment_intents import PaymentIntentCreate, PaymentIntentResponse
from app.services.payment_service import (
    cancel_payment_intent, confirm_payment_intent,
    create_payment_intent, get_payment_intent, list_payment_intents,
)

router = APIRouter()

@router.get("/")
def list_payment_intents_route(db: Session = Depends(get_db)):
    return {"payment_intents": list_payment_intents(db)}

@router.post("/", response_model=PaymentIntentResponse)
def create_payment_intent_route(payload: PaymentIntentCreate, db: Session = Depends(get_db)):
    return create_payment_intent(db, payload.amount, payload.currency)

@router.get("/{payment_intent_id}", response_model=PaymentIntentResponse)
def get_payment_intent_route(payment_intent_id: str, db: Session = Depends(get_db)):
    try:
        return get_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

@router.post("/{payment_intent_id}/confirm", response_model=PaymentIntentResponse)
def confirm_payment_intent_route(payment_intent_id: str, db: Session = Depends(get_db)):
    try:
        return confirm_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

@router.post("/{payment_intent_id}/cancel", response_model=PaymentIntentResponse)
def cancel_payment_intent_route(payment_intent_id: str, db: Session = Depends(get_db)):
    try:
        return cancel_payment_intent(db, payment_intent_id)
    except PaymentIntentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except InvalidPaymentIntentStateError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
```

---

## 4. Payment Intent State Machine

```
          CREATE
            │
            ▼
  requires_payment_method
       │           │
    confirm      cancel
       │           │
       ▼           ▼
   succeeded    canceled

Rules enforced in services:
  - Cannot confirm a canceled intent  → 409
  - Cannot cancel a succeeded intent  → 409
```

---

## 5. HTTP API Reference

| Method | URL | Description | Success |
|---|---|---|---|
| `GET` | `/` | Health check | 200 `{"message": "API is running"}` |
| `POST` | `/v1/payment_intents/` | Create a payment intent | 200 `PaymentIntentResponse` |
| `GET` | `/v1/payment_intents/` | List all payment intents | 200 `{"payment_intents": [...]}` |
| `GET` | `/v1/payment_intents/{id}` | Get one payment intent | 200 `PaymentIntentResponse` |
| `POST` | `/v1/payment_intents/{id}/confirm` | Confirm → `succeeded` | 200 `PaymentIntentResponse` |
| `POST` | `/v1/payment_intents/{id}/cancel` | Cancel → `canceled` | 200 `PaymentIntentResponse` |

**Error codes:**
- `404` — resource not found (`PaymentIntentNotFoundError`)
- `409` — invalid state transition (`InvalidPaymentIntentStateError`)
- `422` — request validation failed (Pydantic)

---

## 6. How to Run

```bash
# Start the server (auto-reloads on file changes)
./dev.sh
# equivalent: uvicorn app.main:app --reload

# Interactive docs (Swagger UI)
http://127.0.0.1:8000/docs
```

---

## 7. Syntax Patterns to Memorize

### Define an API Router
```python
from fastapi import APIRouter
router = APIRouter()
```

### Inject a DB session in a route
```python
from fastapi import Depends
from sqlalchemy.orm import Session
from app.db.database import get_db

@router.get("/")
def my_route(db: Session = Depends(get_db)):
    ...
```

### Add + commit + refresh (create)
```python
db.add(obj)
db.commit()
db.refresh(obj)
return obj
```

### Query one row, raise if missing
```python
obj = db.query(Model).filter(Model.id == id).first()
if not obj:
    raise MyNotFoundError(...)
```

### Map domain exception → HTTP error
```python
try:
    return service_function(db, ...)
except MyNotFoundError as exc:
    raise HTTPException(status_code=404, detail=str(exc))
except MyStateError as exc:
    raise HTTPException(status_code=409, detail=str(exc))
```

### Pydantic schema with validation
```python
from pydantic import BaseModel, Field, field_validator

class MyCreate(BaseModel):
    amount: int = Field(..., gt=0)
    currency: str = Field(..., min_length=3, max_length=3)

    @field_validator("currency")
    @classmethod
    def normalize(cls, v: str) -> str:
        return v.strip().lower()
```

### String Enum for status values
```python
from enum import Enum

class MyStatus(str, Enum):
    pending  = "pending"
    done     = "done"
    canceled = "canceled"
```

### Mount a router in main.py
```python
app.include_router(my_router, prefix="/v1/resource", tags=["resource"])
```

### Test with TestClient
```python
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create():
    response = client.post("/v1/resource/", json={"field": "value"})
    assert response.status_code == 200
    assert response.json()["field"] == "value"
```

---

## 8. Adding a New Feature (the pattern)

Follow this order every time (from `instructions.txt`):

1. **Model** — add a SQLAlchemy class in `app/db/models/`; export it from `__init__.py`
2. **Schema** — add Pydantic `Create` and `Response` models in `app/schemas/`
3. **Service** — add functions in `app/services/`; raise custom exceptions for business-rule errors
4. **Routes** — add handlers in `app/api/routes/`; catch exceptions, return `HTTPException`
5. **Register** — `app.include_router(...)` in `main.py` if it's a new route group
6. **Tests** — add a test file in `app/tests/`
7. **curl** — add manual test commands to `curl.txt`
