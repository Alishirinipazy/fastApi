from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import ShippingMethod, User
from app.schemas.shipping import ShippingMethodIn
from app.utils.response import success_response, error_response

router = APIRouter(tags=["shipping"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-shipping"])


def _serialize(method: ShippingMethod) -> dict:
    return {
        "id": method.id,
        "name": method.name,
        "price": method.price,
        "delivery_days": method.delivery_days,
        "is_active": method.is_active,
    }


@router.get("/shipping-methods")
def index(db: Session = Depends(get_db)):
    """Public - active shipping methods only, cheapest first (used at checkout)."""
    methods = (
        db.query(ShippingMethod)
        .filter(ShippingMethod.is_active.is_(True))
        .order_by(ShippingMethod.price)
        .all()
    )
    return success_response([_serialize(m) for m in methods])


@admin_router.get("/shipping-methods")
def admin_index(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    methods = db.query(ShippingMethod).order_by(ShippingMethod.price).all()
    return success_response([_serialize(m) for m in methods])


@admin_router.post("/shipping-methods")
def admin_store(payload: ShippingMethodIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    method = ShippingMethod(
        name=payload.name,
        price=payload.price,
        delivery_days=payload.delivery_days,
        is_active=payload.is_active if payload.is_active is not None else True,
    )
    db.add(method)
    db.commit()
    db.refresh(method)
    return success_response(_serialize(method), 201)


@admin_router.get("/shipping-methods/{method_id}")
def admin_show(method_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if method is None:
        return error_response("روش ارسال پیدا نشد", 404)
    return success_response(_serialize(method))


@admin_router.put("/shipping-methods/{method_id}")
@admin_router.post("/shipping-methods/{method_id}")
def admin_update(
    method_id: int,
    payload: ShippingMethodIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if method is None:
        return error_response("روش ارسال پیدا نشد", 404)

    method.name = payload.name
    method.price = payload.price
    method.delivery_days = payload.delivery_days
    if payload.is_active is not None:
        method.is_active = payload.is_active
    db.commit()
    return success_response(_serialize(method))


@admin_router.delete("/shipping-methods/{method_id}")
def admin_destroy(method_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if method is None:
        return error_response("روش ارسال پیدا نشد", 404)
    db.delete(method)
    db.commit()
    return success_response({"message": "روش ارسال حذف شد"})


@admin_router.patch("/shipping-methods/{method_id}/toggle")
def admin_toggle(method_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    method = db.query(ShippingMethod).filter(ShippingMethod.id == method_id).first()
    if method is None:
        return error_response("روش ارسال پیدا نشد", 404)
    method.is_active = not method.is_active
    db.commit()
    return success_response(_serialize(method))
