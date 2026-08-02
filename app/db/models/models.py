from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy import Integer, ForeignKey, func
from datetime import datetime
from app.db.database import Base
import uuid


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
    amount = Column(Integer, nullable=False)
    status = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Event(Base):
    __tablename__ = "events"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String, nullable=False, index=True)
    object_id = Column(String, nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)







