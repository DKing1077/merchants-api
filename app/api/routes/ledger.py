from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import LedgerAccount
from app.schemas.ledger_schemas import (
    LedgerBalanceResponse,
    LedgerEntryCreate,
    LedgerEntryResponse,
    LedgerAccountCreate,
    LedgerAccountResponse,
)
from app.services.ledger_service import create_ledger_entry, get_account_balance
router = APIRouter(prefix="/ledger", tags=["Ledger"])


@router.post("/accounts", response_model=LedgerAccountResponse)
def create_account(payload: LedgerAccountCreate, db: Session = Depends(get_db)):
    account = LedgerAccount(**payload.model_dump())
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/accounts", response_model=list[LedgerAccountResponse])
def list_accounts(db: Session = Depends(get_db)):
    return db.query(LedgerAccount).all()


@router.post("/entries", response_model=LedgerEntryResponse)
def create_entry(payload: LedgerEntryCreate, db: Session = Depends(get_db)):
    try:
        return create_ledger_entry(
            db=db,
            entry_type=payload.entry_type,
            reference_id=payload.reference_id,
            description=payload.description,
            entry_metadata=payload.entry_metadata,
            postings=[posting.model_dump() for posting in payload.postings],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/{account_id}/balance", response_model=LedgerBalanceResponse)
def get_balance(account_id: str, db: Session = Depends(get_db)):
    try:
        balance = get_account_balance(db=db, account_id=account_id)
        return LedgerBalanceResponse(account_id=account_id, balance=balance)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


