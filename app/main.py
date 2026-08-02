from fastapi import FastAPI

from app.api.routes import payments
from app.core.config import settings
from app.db.database import create_database_if_missing

create_database_if_missing()

app = FastAPI(title=settings.app_name)


@app.get("/")
def root():
    return {"message": "API is running"}


app.include_router(
    payments.router,
    prefix="/v1/payment_intents",
    tags=["payment_intents"],
)