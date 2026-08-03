from app.db.models import Event


def create_event(db, event_type: str, object_id: str, payload: dict) -> Event:
    event = Event(
        type=event_type,
        object_id=object_id,
        payload=payload,
    )
    db.add(event)
    db.flush()
    db.refresh(event)
    return event

