from fastapi import FastAPI
from app.routes import payment_intents

app = FastAPI(title='Merchants Transactions Platform')

@app.get("/")
def root():
    return {"message": "API is running"}

app.include_router(
    payment_intents.router,
    prefix="/v1/payment-intents",
    tags=["Payment Intents"],
)

