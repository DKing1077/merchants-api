from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import secrets
import uuid
from app.auth.dependencies import require_api_key
from app.db.database import get_db
from app.db.models import WebhookDelivery, WebhookDispatch, WebhookEndpoint
from app.schemas.webhook_schemas import (
    WebhookDispatchDetailResponse,
    WebhookDispatchResponse,
    WebhookDeliveryResponse,
    WebhookEndpointCreate,
    WebhookEndpointResponse,
)
from app.services.delivery import process_pending_dispatches

router = APIRouter()


def _get_endpoint_for_merchant(db: Session, endpoint_id: str, merchant_id: str) -> WebhookEndpoint:
    endpoint = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.id == endpoint_id, WebhookEndpoint.merchant_id == merchant_id)
        .first()
    )
    if not endpoint:
        raise HTTPException(status_code=404, detail="Webhook endpoint not found")
    return endpoint


@router.post("/endpoints", response_model=WebhookEndpointResponse)
def create_webhook_endpoint(payload: WebhookEndpointCreate, db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    if payload.merchant_id != api_key.merchant_id:
        raise HTTPException(status_code=403, detail="merchant mismatch")
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
def list_webhook_endpoints(db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    return db.query(WebhookEndpoint).filter(WebhookEndpoint.merchant_id == api_key.merchant_id).all()


@router.put("/endpoints/{endpoint_id}", response_model=WebhookEndpointResponse)
def update_webhook_endpoint(endpoint_id: str, payload: WebhookEndpointCreate,
    db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    if payload.merchant_id != api_key.merchant_id:
        raise HTTPException(status_code=403, detail="merchant mismatch")
    endpoint = _get_endpoint_for_merchant(db, endpoint_id, api_key.merchant_id)
    endpoint.merchant_id = payload.merchant_id
    endpoint.url = str(payload.url)
    endpoint.event_types = payload.event_types
    db.commit()
    db.refresh(endpoint)
    return endpoint


@router.delete("/endpoints/{endpoint_id}")
def delete_webhook_endpoint(endpoint_id: str, db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    endpoint = _get_endpoint_for_merchant(db, endpoint_id, api_key.merchant_id)
    db.delete(endpoint)
    db.commit()
    return {"message": "webhook endpoint deleted"}


@router.get("/endpoints/{endpoint_id}/deliveries", response_model=list[WebhookDeliveryResponse])
def list_endpoint_deliveries(endpoint_id: str, db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    _get_endpoint_for_merchant(db, endpoint_id, api_key.merchant_id)
    return (
        db.query(WebhookDelivery)
        .join(WebhookDispatch, WebhookDispatch.id == WebhookDelivery.webhook_dispatch_id)
        .filter(WebhookDispatch.webhook_endpoint_id == endpoint_id)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .all()
    )


@router.get("/dispatches", response_model=list[WebhookDispatchResponse])
def list_webhook_dispatches(status: str | None = Query(default=None), db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    query = db.query(WebhookDispatch).join(
        WebhookEndpoint,
        WebhookEndpoint.id == WebhookDispatch.webhook_endpoint_id,
    ).filter(WebhookEndpoint.merchant_id == api_key.merchant_id)
    if status:
        query = query.filter(WebhookDispatch.status == status)
    return query.order_by(WebhookDispatch.created_at.desc(), WebhookDispatch.id.desc()).all()


@router.get("/dispatches/{dispatch_id}", response_model=WebhookDispatchDetailResponse)
def get_webhook_dispatch(dispatch_id: str, db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    dispatch = (
        db.query(WebhookDispatch)
        .join(WebhookEndpoint, WebhookEndpoint.id == WebhookDispatch.webhook_endpoint_id)
        .filter(
            WebhookDispatch.id == dispatch_id,
            WebhookEndpoint.merchant_id == api_key.merchant_id,
        )
        .first()
    )
    if not dispatch:
        raise HTTPException(status_code=404, detail="Webhook dispatch not found")
    deliveries = (
        db.query(WebhookDelivery)
        .filter(WebhookDelivery.webhook_dispatch_id == dispatch.id)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .all()
    )
    return {
        "id": dispatch.id,
        "event_id": dispatch.event_id,
        "webhook_endpoint_id": dispatch.webhook_endpoint_id,
        "payload": dispatch.payload,
        "status": dispatch.status,
        "next_retry_at": dispatch.next_retry_at,
        "created_at": dispatch.created_at,
        "deliveries": deliveries,
    }


@router.get("/deliveries", response_model=list[WebhookDeliveryResponse])
def list_webhook_deliveries(db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    return (
        db.query(WebhookDelivery)
        .join(WebhookDispatch, WebhookDispatch.id == WebhookDelivery.webhook_dispatch_id)
        .join(WebhookEndpoint, WebhookEndpoint.id == WebhookDispatch.webhook_endpoint_id)
        .filter(WebhookEndpoint.merchant_id == api_key.merchant_id)
        .order_by(WebhookDelivery.created_at.desc(), WebhookDelivery.id.desc())
        .all()
    )


@router.post("/dispatches/process")
def process_dispatches(db: Session = Depends(get_db)):
    process_pending_dispatches(db)
    return {"message": "dispatches processed"}