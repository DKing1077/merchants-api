import hashlib

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ApiKey

api_key_header = APIKeyHeader(name="Authorization", auto_error=False)


def require_api_key(
    authorization: str | None = Security(api_key_header),
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


def require_admin_api_key(
    api_key: ApiKey = Depends(require_api_key),
):
    if not api_key.is_admin:
        raise HTTPException(status_code=403, detail="admin access required")
    return api_key