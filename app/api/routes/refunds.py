from fastapi import APIRouter, Depends, HTTPException

from app.db.database import get_db
from app.services.refunds_service import (
    list_refunds,
    create_refund,
    get_refund,
    confirm_refund,
    decline_refund,
    cancel_refund
)

router = APIRouter()

@router('')
def list_refunds_route():
    pass


@router('')
def create_refund_route():
    pass


@router('')
def get_refund_route():
    pass


@router('')
def confirm_refund_route():
    pass


@router('')
def decline_refund_route():
    pass


@router('')
def cancel_refund_route():
    pass

