from sqlalchemy import Column, Integer, String, ForeignKey

from app.db.database import Base


class PaymentIntent(Base):
    __tablename__ = "payment_intents"

    id = Column(String, primary_key=True, index=True)
    amount = Column(Integer, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String, nullable=False)


class Refunds(Base):
    __tablename__ = "refunds"

    id = Column(String, primary_key=True, index=True)
    payment_intent_id = Column(String, ForeignKey("payment_intents.id"), nullable=False)
    status = Column(String, nullable=False)




