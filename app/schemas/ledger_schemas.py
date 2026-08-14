from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LedgerAccountCreate(BaseModel):
    name: str
    account_type: str
    currency: str = Field(..., min_length=3, max_length=3)
    merchant_id: str | None = None


class LedgerAccountResponse(BaseModel):
    id: str
    name: str
    account_type: str
    currency: str
    merchant_id: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerPostingCreate(BaseModel):
    account_id: str
    amount: int
    currency: str = Field(..., min_length=3, max_length=3)


class LedgerPostingResponse(BaseModel):
    id: str
    account_id: str
    amount: int
    currency: str
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerEntryCreate(BaseModel):
    entry_type: str
    reference_id: str | None = None
    description: str | None = None
    entry_metadata: dict[str, Any] | None = None
    postings: list[LedgerPostingCreate]


class LedgerEntryResponse(BaseModel):
    id: str
    entry_type: str
    reference_id: str | None
    description: str | None
    entry_metadata: dict[str, Any] | None
    created_at: datetime

    model_config = {"from_attributes": True}


class LedgerEntryWithPostingsResponse(LedgerEntryResponse):
    postings: list[LedgerPostingResponse]


class LedgerAccountBalanceResponse(BaseModel):
    account_id: str
    name: str
    account_type: str
    currency: str
    merchant_id: str
    balance: int


class BalanceSheetGroup(BaseModel):
    account_type: str
    currency: str
    accounts: list[LedgerAccountBalanceResponse]
    total_balance: int
