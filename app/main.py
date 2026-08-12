from fastapi import FastAPI
from app.api.routes import payments
from app.api.routes import refunds
from app.api.routes import timestamps
from app.api.routes import webhooks
from app.api.routes import ledger
import app.db.models.models
from app.core.config import settings
from app.db.database import create_database_if_missing, Base, engine

create_database_if_missing()
Base.metadata.create_all(bind=engine)
app = FastAPI(title=settings.app_name)


@app.get("/")
def root():
    return {"message": "API is running"}


app.include_router(
    payments.router,
    prefix="/v1/payment_intents",
    tags=["payment_intents"],
)

app.include_router(
    refunds.router,
    prefix="/v1/refunds",
    tags=["refunds"],
)

app.include_router(
    webhooks.router,
    prefix="/v1/webhooks",
    tags=["webhooks"],
)

app.include_router(
    ledger.router,
    prefix="/v1",
    tags=["ledger"],
)

app.include_router(
    timestamps.router,
    prefix="/v1/timestamps",
    tags=["timestamps"],
)

