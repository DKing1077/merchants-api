from sqlalchemy import case, func
from fastapi import APIRouter, Depends
from app.auth.dependencies import require_admin_api_key
from app.db.database import get_db
from app.db.models import PaymentIntent

router = APIRouter(prefix="/admin/risk", tags=["risk"])


@router.get("/summary")
def risk_summary_route(db=Depends(get_db), api_key=Depends(require_admin_api_key)):
    rows = (
        db.query(
            PaymentIntent.merchant_id.label("merchant_id"),
            func.count().label("total"),
            func.sum(case((PaymentIntent.is_flagged.is_(True), 1), else_=0)).label("flagged"),
            func.sum(case((PaymentIntent.review_status == "approved", 1), else_=0)).label("approved"),
            func.sum(case((PaymentIntent.review_status == "rejected", 1), else_=0)).label("rejected"),
            func.avg(PaymentIntent.risk_score).label("average_risk_score"),
        )
        .group_by(PaymentIntent.merchant_id)
        .order_by(PaymentIntent.merchant_id)
        .all()
    )
    return [
        {
            "merchant_id": row.merchant_id,
            "total": row.total,
            "flagged": row.flagged or 0,
            "approved": row.approved or 0,
            "rejected": row.rejected or 0,
            "average_risk_score": float(row.average_risk_score or 0),
        }
        for row in rows
    ]
