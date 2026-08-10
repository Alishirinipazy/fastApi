from datetime import datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models import Coupon, Order, User
from app.schemas.coupon import CouponIn, CouponCheckIn
from app.utils.jalali import format_jalali
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(tags=["coupons"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-coupons"])


def _serialize(coupon: Coupon) -> dict:
    return {
        "id": coupon.id,
        "code": coupon.code,
        "percentage": coupon.percentage,
        "expired_at": coupon.expired_at.isoformat() if coupon.expired_at else None,
        "expired_at_jalali": format_jalali(coupon.expired_at),
        "created_at": format_jalali(coupon.created_at),
    }


@router.post("/check-coupon")
def check_coupon(
    payload: CouponCheckIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    coupon = (
        db.query(Coupon)
        .filter(Coupon.code == payload.code, Coupon.expired_at > datetime.utcnow())
        .first()
    )
    if coupon is None:
        return error_response({"error": ["کد تخفیف وارد شده وجود ندارد"]}, 422)

    already_used = (
        db.query(Order)
        .filter(
            Order.user_id == current_user.id,
            Order.coupon_id == coupon.id,
            Order.payment_status == 1,
        )
        .first()
        is not None
    )
    if already_used:
        return error_response({"error": ["شما قبلا از این کد تخفیف استفاده کرده اید"]}, 422)

    return success_response({"percentage": coupon.percentage})


@admin_router.get("/coupons")
def admin_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(Coupon).order_by(Coupon.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=5)
    return success_response({"coupons": [_serialize(c) for c in items], "links": links, "meta": meta})


@admin_router.post("/coupons")
def admin_store(payload: CouponIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    if db.query(Coupon).filter(Coupon.code == payload.code).first():
        return error_response({"code": ["این کد تخفیف قبلا استفاده شده است"]}, 422)

    coupon = Coupon(code=payload.code, percentage=payload.percentage, expired_at=payload.expired_at)
    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return success_response(_serialize(coupon), 201)


@admin_router.get("/coupons/{coupon_id}")
def admin_show(coupon_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if coupon is None:
        return error_response("کد تخفیف پیدا نشد", 404)
    return success_response(_serialize(coupon))


@admin_router.put("/coupons/{coupon_id}")
@admin_router.post("/coupons/{coupon_id}")
def admin_update(coupon_id: int, payload: CouponIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if coupon is None:
        return error_response("کد تخفیف پیدا نشد", 404)

    duplicate = db.query(Coupon).filter(Coupon.code == payload.code, Coupon.id != coupon_id).first()
    if duplicate:
        return error_response({"code": ["این کد تخفیف قبلا استفاده شده است"]}, 422)

    coupon.code = payload.code
    coupon.percentage = payload.percentage
    if payload.expired_at:
        coupon.expired_at = payload.expired_at
    db.commit()
    return success_response(_serialize(coupon))


@admin_router.delete("/coupons/{coupon_id}")
def admin_destroy(coupon_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if coupon is None:
        return error_response("کد تخفیف پیدا نشد", 404)
    db.delete(coupon)
    db.commit()
    return success_response(_serialize(coupon))
