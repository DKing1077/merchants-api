from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, func
from app.db.database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Refunds(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, index=True, nullable=False, unique=True)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False)
    amout = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)





