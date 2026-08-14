from __future__ import annotations

from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import DuplicateLedgerEntryError
from app.db.models import LedgerAccount, LedgerEntry, LedgerPosting


def create_ledger_entry(
    db: Session,
    *,
    entry_type: str,
    reference_id: str | None = None,
    description: str | None = None,
    entry_metadata=None,
    postings,
):
    if len(postings) < 2:
        raise ValueError("at least two postings are required")
    if sum(posting["amount"] for posting in postings) != 0:
        raise ValueError("postings must balance to zero")
    if reference_id and (
        db.query(LedgerEntry)
        .filter(
            LedgerEntry.entry_type == entry_type,
            LedgerEntry.reference_id == reference_id,
        )
        .first()
    ):
        raise DuplicateLedgerEntryError("Ledger entry already exists for this reference")

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
    db.flush()
    db.refresh(entry)
    return entry


def get_account(db: Session, account_id: str) -> LedgerAccount:
    account = db.query(LedgerAccount).filter(LedgerAccount.id == account_id).first()
    if not account:
        raise ValueError(f"Account {account_id} not found")
    return account


def get_account_balance(db: Session, account_id: str) -> int:
    return (
        db.query(func.coalesce(func.sum(LedgerPosting.amount), 0))
        .filter(LedgerPosting.account_id == account_id)
        .scalar()
        or 0
    )


def get_account_balance_details(db: Session, account_id: str) -> dict:
    account = get_account(db, account_id)
    return {
        "account_id": account.id,
        "name": account.name,
        "account_type": account.account_type,
        "currency": account.currency,
        "merchant_id": account.merchant_id,
        "balance": get_account_balance(db, account_id),
    }


def list_account_entries(db: Session, account_id: str, limit: int = 20, starting_after: str | None = None) -> dict:
    get_account(db, account_id)
    entry_ids = [
        row[0]
        for row in (
            db.query(LedgerEntry.id)
            .join(LedgerPosting, LedgerPosting.entry_id == LedgerEntry.id)
            .filter(LedgerPosting.account_id == account_id)
            .distinct()
            .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
            .all()
        )
    ]
    if starting_after and starting_after in entry_ids:
        entry_ids = entry_ids[entry_ids.index(starting_after) + 1 :]
    sliced_ids = entry_ids[: limit + 1]
    has_more = len(sliced_ids) > limit
    selected_ids = sliced_ids[:limit]
    if not selected_ids:
        return {"data": [], "has_more": False}

    entries = (
        db.query(LedgerEntry)
        .filter(LedgerEntry.id.in_(selected_ids))
        .order_by(LedgerEntry.created_at.desc(), LedgerEntry.id.desc())
        .all()
    )
    postings_by_entry = defaultdict(list)
    for posting in db.query(LedgerPosting).filter(LedgerPosting.entry_id.in_(selected_ids)).all():
        postings_by_entry[posting.entry_id].append(posting)

    data = []
    for entry in entries:
        data.append(
            {
                "id": entry.id,
                "entry_type": entry.entry_type,
                "reference_id": entry.reference_id,
                "description": entry.description,
                "entry_metadata": entry.entry_metadata,
                "created_at": entry.created_at,
                "postings": postings_by_entry[entry.id],
            }
        )
    return {"data": data, "has_more": has_more}


def get_balance_sheet(db: Session, merchant_id: str) -> list[dict]:
    rows = (
        db.query(
            LedgerAccount,
            func.coalesce(func.sum(LedgerPosting.amount), 0).label("balance"),
        )
        .outerjoin(LedgerPosting, LedgerPosting.account_id == LedgerAccount.id)
        .filter(LedgerAccount.merchant_id == merchant_id)
        .group_by(LedgerAccount.id)
        .order_by(LedgerAccount.account_type, LedgerAccount.currency, LedgerAccount.created_at.desc())
        .all()
    )
    grouped: dict[tuple[str, str], dict] = {}
    for account, balance in rows:
        key = (account.account_type, account.currency)
        group = grouped.setdefault(
            key,
            {
                "account_type": account.account_type,
                "currency": account.currency,
                "accounts": [],
                "total_balance": 0,
            },
        )
        account_row = {
            "account_id": account.id,
            "name": account.name,
            "account_type": account.account_type,
            "currency": account.currency,
            "merchant_id": account.merchant_id,
            "balance": balance,
        }
        group["accounts"].append(account_row)
        group["total_balance"] += balance
    return list(grouped.values())
