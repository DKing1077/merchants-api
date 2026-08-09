from fastapi import APIRouter, Depends, HTTPException, Query
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


@router.put("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
def update_webhook_endpoint(
    endpoint_id: str,
    payload: WebhookEndpointCreate,
    db: Session = Depends(get_db),):
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    endpoint.merchant_id = payload.merchant_id
    endpoint.url = str(payload.url)
    endpoint.event_types = payload.event_types

    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.delete("/endpoints/{endpoint_id}")
def delete_webhook_endpoint(endpoint_id: str, db: Session = Depends(get_db)):
    endpoint = db.query(WebhookEndpoint).filter(WebhookEndpoint.id == endpoint_id).first()
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")

    db.delete(endpoint)
    db.commit()
    return {"message": "webhook endpoint deleted"}


@router.get("/dispatches")
def list_webhook_dispatches(
    merchant_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    db: Session = Depends(get_db),):
    query = db.query(WebhookDispatch)

    if merchant_id:
        query = query.join(
            WebhookEndpoint,
            WebhookEndpoint.id == WebhookDispatch.webhook_endpoint_id,
        ).filter(WebhookEndpoint.merchant_id == merchant_id)

    if status:
        query = query.filter(WebhookDispatch.status == status)

    return query.all()


@router.get("/deliveries")
def list_webhook_deliveries(db: Session = Depends(get_db)):
    return db.query(WebhookDelivery).all()


@router.post("/dispatches/process")
def process_dispatches(db: Session = Depends(get_db)):
    process_pending_dispatches(db)
    return {"message": "dispatches processed"}