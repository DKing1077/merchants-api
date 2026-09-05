from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.auth.dependencies import require_api_key
from app.core.exceptions import DuplicateLedgerEntryError
from app.db.database import get_db
from app.db.models import LedgerAccount
from app.schemas.ledger_schemas import (
    BalanceSheetGroup,
    LedgerAccountBalanceResponse,
    LedgerAccountCreate,
    LedgerAccountResponse,
    LedgerEntryCreate,
    LedgerEntryResponse
)
from app.services.ledger_service import (
    create_ledger_entry,
    get_account_balance_details,
    get_balance_sheet,
    list_account_entries,
)

router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.post("/accounts", response_model=LedgerAccountResponse)
def create_account(payload: LedgerAccountCreate, db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    merchant_id = payload.merchant_id or api_key.merchant_id
    if merchant_id != api_key.merchant_id:
        raise HTTPException(status_code=403, detail="merchant mismatch")
    account = LedgerAccount(
        name=payload.name,
        account_type=payload.account_type,
        currency=payload.currency.lower(),
        merchant_id=merchant_id,
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.post("/entries", response_model=LedgerEntryResponse)
def create_entry(payload: LedgerEntryCreate, db: Session = Depends(get_db)):
    try:
        entry = create_ledger_entry(
            db=db,
            entry_type=payload.entry_type,
            reference_id=payload.reference_id,
            description=payload.description,
            entry_metadata=payload.entry_metadata,
            postings=[posting.model_dump() for posting in payload.postings],
        )
        db.commit()
        db.refresh(entry)
        return entry
    except DuplicateLedgerEntryError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/accounts", response_model=list[LedgerAccountResponse])
def list_accounts(db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    return db.query(LedgerAccount).filter(LedgerAccount.merchant_id == api_key.merchant_id).all()


@router.get("/accounts/{account_id}/balance", response_model=LedgerAccountBalanceResponse)
def get_balance(account_id: str, db: Session = Depends(get_db)):
    try:
        return get_account_balance_details(db=db, account_id=account_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/accounts/{account_id}/entries")
def get_account_entries(account_id: str, limit: int = Query(default=20, ge=1, le=100),
    starting_after: str | None = Query(default=None), db: Session = Depends(get_db)):
    try:
        return list_account_entries(db=db, account_id=account_id, limit=limit, starting_after=starting_after)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/merchant/{merchant_id}/balance_sheet", response_model=list[BalanceSheetGroup])
def get_merchant_balance_sheet(merchant_id: str, db: Session = Depends(get_db), api_key=Depends(require_api_key)):
    if merchant_id != api_key.merchant_id:
        raise HTTPException(status_code=403, detail="merchant mismatch")
    return get_balance_sheet(db=db, merchant_id=merchant_id)