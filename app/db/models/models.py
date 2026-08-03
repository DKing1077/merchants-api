from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy import Column, DateTime, String, Text, Boolean
from sqlalchemy import Integer, ForeignKey, func
from datetime import datetime
from app.db.database import Base
import uuid


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String, primary_key=True, index=True)
    merchant_id = Column(String, nullable=False, index=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String, nullable=False)
    idempotency_key = Column(String, unique=True, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class Refunds(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, index=True, nullable=False, unique=True)
    merchant_id = Column(String, nullable=False, index=True)
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


class WebhookEndpoint(Base):
    __tablename__ = "webhook_endpoints"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id = Column(String, nullable=False, index=True)
    url = Column(Text, nullable=False)
    event_types = Column(JSONB, nullable=False)
    secret = Column(String, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


class WebhookDispatch(Base):
    __tablename__ = "webhook_dispatches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_id = Column(String, ForeignKey("events.id"), nullable=False, index=True)
    webhook_endpoint_id = Column(String, ForeignKey("webhook_endpoints.id"), nullable=False, index=True)
    payload = Column(JSONB, nullable=False)
    status = Column(String, default="pending", nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    webhook_dispatch_id = Column(String, ForeignKey("webhook_dispatches.id"), nullable=False, index=True)
    attempt_number = Column(Integer, default=1, nullable=False)
    response_status = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    status = Column(String, default="pending", nullable=False)
    next_retry_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)