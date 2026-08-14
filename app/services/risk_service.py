from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import func

from app.core.config import settings
from app.core.exceptions import RiskRateLimitError
from app.db.models import PaymentIntent


def recent_payment_intent_count(db, merchant_id: str, now: datetime | None = None) -> int:
    now = now or datetime.utcnow()
    window_start = now - timedelta(seconds=settings.merchant_velocity_window_seconds)
    return (
        db.query(func.count(PaymentIntent.id))
        .filter(
            PaymentIntent.merchant_id == merchant_id,
            PaymentIntent.created_at >= window_start,
        )
        .scalar()
        or 0
    )


def enforce_velocity_limit(db, merchant_id: str) -> None:
    if recent_payment_intent_count(db, merchant_id) >= settings.merchant_velocity_limit:
        raise RiskRateLimitError("Too many payment intents created for this merchant")


def calculate_risk_score(db, merchant_id: str, amount: int) -> int:
    prior_count = (
        db.query(func.count(PaymentIntent.id))
        .filter(PaymentIntent.merchant_id == merchant_id)
        .scalar()
        or 0
    )
    score = 5
    if amount >= settings.high_value_payment_threshold:
        score += 60
    elif amount >= settings.high_value_payment_threshold // 2:
        score += 25
    if prior_count == 0:
        score += 20
    if recent_payment_intent_count(db, merchant_id) >= max(settings.merchant_velocity_limit // 2, 1):
        score += 15
    return min(score, 100)
