from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.schemas.webhook_schemas import WebhookEndpointCreate, WebhookEndpointResponse
from app.db.models import WebhookDelivery, WebhookDispatch, WebhookEndpoint
from app.services.delivery import process_pending_dispatches
import uuid
import secrets

router = APIRouter()


@router.post("/endpoints", response_model=WebhookEndpointResponse)
def create_webhook_endpoint(payload: WebhookEndpointCreate, db: Session = Depends(get_db)):
    endpoint = WebhookEndpoint(
        id=str(uuid.uuid4()),
        merchant_id=payload.merchant_id,
        url=str(payload.url),
        event_types=payload.event_types,
        secret=secrets.token_hex(32),
        is_active=True,
    )
    db.add(endpoint)
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.get("/endpoints", response_model=list[WebhookEndpointResponse])
def list_webhook_endpoints(db: Session = Depends(get_db)):
    return db.query(WebhookEndpoint).all()


@router.get("/dispatches")
def list_webhook_dispatches(db: Session = Depends(get_db)):
    return db.query(WebhookDispatch).all()


@router.get("/deliveries")
def list_webhook_deliveries(db: Session = Depends(get_db)):
    return db.query(WebhookDelivery).all()


@router.post("/dispatches/process")
def process_dispatches(db: Session = Depends(get_db)):
    process_pending_dispatches(db)
    return {"message": "dispatches processed"}