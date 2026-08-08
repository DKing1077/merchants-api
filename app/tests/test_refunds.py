"""
Tests for the refunds service.

NOTE: The refunds router is not registered in app/main.py, so these tests
exercise the service functions directly via the database session fixture.
"""
import pytest
from app.services import refunds_service
from app.services import payment_service
from app.core.exceptions import RefundNotFoundError, RefundStateError
from app.schemas.refunds_schemas import RefundStatus


def make_payment_intent(db, amount=5000, currency="usd", merchant_id="merchant_1"):
    return payment_service.create_payment_intent(
        db=db, amount=amount, currency=currency, merchant_id=merchant_id
    )


# ---------------------------------------------------------------------------
# list_refunds
# ---------------------------------------------------------------------------


def test_list_refunds_empty(db):
    refunds = refunds_service.list_refunds(db)
    assert refunds == []


# ---------------------------------------------------------------------------
# get_refund – not found
# ---------------------------------------------------------------------------


def test_get_refund_not_found(db):
    with pytest.raises(RefundNotFoundError):
        refunds_service.get_refund("pi_missing", db)


# ---------------------------------------------------------------------------
# create_refund – validation errors (raised before any DB write)
# ---------------------------------------------------------------------------


def test_create_refund_zero_amount_raises(db):
    pi = make_payment_intent(db)
    with pytest.raises(RefundStateError, match="greater than 0"):
        refunds_service.create_refund(pi.id, 0, db)


def test_create_refund_negative_amount_raises(db):
    pi = make_payment_intent(db)
    with pytest.raises(RefundStateError, match="greater than 0"):
        refunds_service.create_refund(pi.id, -100, db)


def test_create_refund_exceeds_payment_amount_raises(db):
    pi = make_payment_intent(db, amount=1000)
    with pytest.raises(RefundStateError, match="greater than payment amount"):
        refunds_service.create_refund(pi.id, 9999, db)


# ---------------------------------------------------------------------------
# confirm / decline / cancel – not found
# ---------------------------------------------------------------------------


def test_confirm_refund_not_found_raises(db):
    with pytest.raises(RefundNotFoundError):
        refunds_service.confirm_refund("pi_missing", db)


def test_decline_refund_not_found_raises(db):
    with pytest.raises(RefundNotFoundError):
        refunds_service.decline_refund("pi_missing", db)


def test_cancel_refund_not_found_raises(db):
    with pytest.raises(RefundNotFoundError):
        refunds_service.cancel_refund("pi_missing", db)
