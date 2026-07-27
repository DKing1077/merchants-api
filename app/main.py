from fastapi import FastAPI

from app.api.routes import payments
from app.core.config import settings
from app.db.database import Base, engine
from app.db.models import PaymentIntent

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
