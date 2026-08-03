from app.db.models.models import WebhookDispatch, WebhookEndpoint


def create_dispatches_for_event(db, merchant_id: str, event):
    endpoints = (
        db.query(WebhookEndpoint)
        .filter(WebhookEndpoint.merchant_id == merchant_id)
        .filter(WebhookEndpoint.is_active.is_(True))
        .all()
    )
    dispatches = []
    for endpoint in endpoints:
        if event.type in endpoint.event_types:
            dispatch = WebhookDispatch(
                event_id=event.id,
                webhook_endpoint_id=endpoint.id,
                payload=event.payload,
                status="pending",
            )
            db.add(dispatch)
            dispatches.append(dispatch)
    db.flush()
    return dispatches


def list_dispatches(db):
    return db.query(WebhookDispatch).all()

