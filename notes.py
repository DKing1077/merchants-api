from datetime import datetime

from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import create_engine, DateTime, func
from sqlalchemy import Column, Integer, String, Float

engine = create_engine('sqlite:///example.db')
base = declarative_base()
session = sessionmaker(bind=engine)

db = session()
base.metadata.create_all(engine)


class payment_intent(base):
    __tablename__ = 'payment_intents'
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String(20), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), nullable=False)
    status = Column(String(20), nullable=False)

    is_flagged = Column(Integer, default=0)  # 0 for False, 1 for True
    review_status = Column(Integer, default=0)
    review_reason = Column(DateTime, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class refund(base):
    __tablename__ = 'refunds'
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String(20), nullable=False)
    payment_intent_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    status = Column(String(20), nullable=False)

    is_flagged = Column(Integer, default=0)  # 0 for False, 1 for True
    review_status = Column(Integer, default=0)
    review_reason = Column(DateTime, nullable=False)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class Event(base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    type = Column(String(20), nullable=False)
    object_id = Column(Integer, nullable=False)
    payload = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class WebhookEndpoint(base):
    __tablename__ = 'webhook_endpoints'
    id = Column(Integer, primary_key=True)
    url = Column(String(255), nullable=False)
    secret = Column(String(255), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class WebhookDispatch(base):
    __tablename__ = 'webhook_dispatches'
    id = Column(Integer, primary_key=True)
    webhook_endpoint_id = Column(Integer, nullable=False)
    event_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    response_code = Column(Integer, nullable=True)
    response_body = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class WebhookDelivery(base):
    __tablename__ = 'webhook_deliveries'
    id = Column(Integer, primary_key=True)
    webhook_dispatch_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    response_code = Column(Integer, nullable=True)
    response_body = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class LedgerAccount(base):
    __tablename__ = 'ledger_accounts'
    id = Column(Integer, primary_key=True)
    merchant_id = Column(String(20), nullable=False)
    balance = Column(Float, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

class LedgerEntry(base):
    __tablename__ = 'ledger_entries'
    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)

class LedgerPosting(base):
    __tablename__ = 'ledger_postings'
    id = Column(Integer, primary_key=True)
    entry_id = Column(Integer, nullable=False)
    status = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)









