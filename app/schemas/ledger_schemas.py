from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class LedgerPostingCreate(BaseModel):
    account_id: str
    amount: int
    currency: str = Field(..., min_length=3, max_length=3)


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


class LedgerBalanceResponse(BaseModel):
    account_id: str
    balance: int