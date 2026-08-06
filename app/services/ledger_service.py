from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.models import LedgerEntry, LedgerPosting


def create_ledger_entry(db, *, entry_type, reference_id=None,
                        description=None, entry_metadata=None, postings):
    if len(postings) < 2:
        raise ValueError("at least two postings are required")

    if sum(posting["amount"] for posting in postings) != 0:
        raise ValueError("postings must balance to zero")

    entry = LedgerEntry(
        entry_type=entry_type,
        reference_id=reference_id,
        description=description,
        entry_metadata=entry_metadata,
    )
    db.add(entry)
    db.flush()

    for posting in postings:
        db.add(
            LedgerPosting(
                entry_id=entry.id,
                account_id=posting["account_id"],
                amount=posting["amount"],
                currency=posting["currency"],
            )
        )

    db.commit()
    db.refresh(entry)
    return entry


def get_account_balance(db: Session, account_id: str) -> int:
    balance = (
        db.query(func.coalesce(func.sum(LedgerPosting.amount), 0))
        .filter(LedgerPosting.account_id == account_id)
        .scalar()
    )
    return balance