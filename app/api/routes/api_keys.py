import hashlib
import secrets
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ApiKey
from app.schemas.api_key_schemas import ApiKeyCreate, ApiKeyResponse

router = APIRouter(prefix="/v1/api_keys", tags=["api_keys"])


@router.post("", response_model=ApiKeyResponse)
def create_api_key(payload: ApiKeyCreate, db: Session = Depends(get_db)):
    raw_key = secrets.token_hex(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()

    api_key = ApiKey(
        id=str(uuid.uuid4()),
        key_hash=key_hash,
        merchant_id=payload.merchant_id,
        is_active=True,
        is_admin=payload.is_admin,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

    return ApiKeyResponse(
        id=api_key.id,
        merchant_id=api_key.merchant_id,
        api_key=raw_key,
        is_active=api_key.is_active,
        is_admin=api_key.is_admin,
        created_at=api_key.created_at,
    )