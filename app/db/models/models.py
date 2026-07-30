from sqlalchemy import Column, Integer, String, ForeignKey, TIMESTAMP, DateTime, func
from app.db.database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String, nullable=False)


class Refunds(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, index=True, nullable=False, unique=True)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False)
    amout = Column(Integer, nullable=False)
    status = Column(String, nullable=False)


class Timestamp(Base):
    __tablename__ = "timestamps"

    id = Column(String, primary_key=True, index=True, nullable=False, unique=True)

    refund_id = Column(String, ForeignKey("refunds.id"))
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"))

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())




