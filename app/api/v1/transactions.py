from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Transaction, User
from app.utils.jalali import format_jalali, _MONTHS
from app.utils.pagination import paginate
from app.utils.response import success_response

import jdatetime

admin_router = APIRouter(prefix="/admin-panel", tags=["admin-transactions"])


def _serialize(t: Transaction) -> dict:
    return {
        "id": t.id,
        "order_id": t.order_id,
        "amount": t.amount,
        "status": t.status,
        "trans_id": t.trans_id,
        "created_at": format_jalali(t.created_at),
    }


@admin_router.get("/transactions")
def admin_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(Transaction).order_by(Transaction.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=10)
    return success_response({"transactions": [_serialize(t) for t in items], "links": links, "meta": meta})


@admin_router.get("/transactions/chart")
def admin_chart(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    """
    Successful-transaction totals for the last 12 Jalali months, oldest first -
    mirrors TransactionController::chart()/chartData().
    """
    months = 12
    cutoff = datetime.utcnow() - timedelta(days=31 * months)

    transactions = (
        db.query(Transaction)
        .filter(Transaction.status == 1, Transaction.created_at >= cutoff)
        .all()
    )

    totals: dict[str, int] = {}
    for t in transactions:
        j = jdatetime.datetime.fromgregorian(datetime=t.created_at)
        key = f"{_MONTHS[j.month - 1]} {j.year}"
        totals[key] = totals.get(key, 0) + t.amount

    # build the last 12 Jalali month buckets (oldest first), zero-filled
    now_j = jdatetime.datetime.now()
    buckets = []
    for i in range(months - 1, -1, -1):
        y, m = now_j.year, now_j.month - i
        while m <= 0:
            m += 12
            y -= 1
        key = f"{_MONTHS[m - 1]} {y}"
        buckets.append({"month": key, "value": totals.get(key, 0)})

    return success_response(buckets)
