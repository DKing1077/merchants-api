import hashlib
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import ApiKey


def require_api_key(
    authorization: str | None = Header(default=None, alias="Authorization"),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    key_hash = hashlib.sha256(authorization.encode()).hexdigest()

    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.key_hash == key_hash, ApiKey.is_active == True)
        .first()
    )
    if not api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return api_key

