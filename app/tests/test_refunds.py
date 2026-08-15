import pytest

from app.db.models import PaymentIntent
from app.schemas.refunds_schemas import RefundStatus
from app.services import payment_service, refunds_service
from app.core.exceptions import RefundStateError


MERCHANT_ID = "merchant_1"


def make_captured_payment_intent(db, amount=1_000):
    payment_intent = payment_service.create_payment_intent(
        db=db,
        amount=amount,
        currency="usd",
        merchant_id=MERCHANT_ID,
    )
    payment_service.confirm_payment_intent(db, payment_intent.id, MERCHANT_ID)
    return payment_service.capture_payment_intent(db, payment_intent.id, MERCHANT_ID)


def test_create_refund_requires_captured_funds(db):
    payment_intent = payment_service.create_payment_intent(
        db=db,
        amount=1_000,
        currency="usd",
        merchant_id=MERCHANT_ID,
    )
    with pytest.raises(RefundStateError, match="captured funds"):
        refunds_service.create_refund(db, payment_intent.id, 100, merchant_id=MERCHANT_ID)


def test_create_refund_respects_captured_amount(db):
    payment_intent = make_captured_payment_intent(db, amount=900)
    refunds_service.create_refund(db, payment_intent.id, 400, merchant_id=MERCHANT_ID)
    with pytest.raises(RefundStateError, match="captured amount"):
        refunds_service.create_refund(db, payment_intent.id, 600, merchant_id=MERCHANT_ID)


def test_confirm_refund_updates_total_refunded(db):
    payment_intent = make_captured_payment_intent(db)
    refund = refunds_service.create_refund(db, payment_intent.id, 250, merchant_id=MERCHANT_ID)
    confirmed = refunds_service.confirm_refund(refund.id, db, MERCHANT_ID)

    refreshed = db.query(PaymentIntent).filter(PaymentIntent.id == payment_intent.id).first()
    assert confirmed.status == RefundStatus.confirmed
    assert refreshed.total_refunded == 250
