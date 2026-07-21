from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Order, User
from app.services.storage import image_url
from app.utils.jalali import format_jalali
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

admin_router = APIRouter(prefix="/admin-panel", tags=["admin-orders"])

IMAGE_SUBDIR = "products"

# order_status values - mirrors Order::statusList() in the Laravel model
STATUS_LIST = {
    0: {"label": "در انتظار پرداخت", "color": "secondary", "icon": "clock"},
    1: {"label": "پرداخت شده", "color": "info", "icon": "credit-card"},
    2: {"label": "در حال پردازش", "color": "warning", "icon": "gear"},
    3: {"label": "آماده ارسال", "color": "primary", "icon": "box"},
    4: {"label": "ارسال شد", "color": "info", "icon": "truck"},
    5: {"label": "تحویل داده شد", "color": "success", "icon": "check-circle"},
    6: {"label": "لغو شد", "color": "danger", "icon": "x-circle"},
    7: {"label": "مرجوع شد", "color": "dark", "icon": "arrow-return-right"},
}

# mirrors Order::allowedTransitions()
ALLOWED_TRANSITIONS = {
    0: [6],
    1: [2, 6],
    2: [3, 6],
    3: [4, 6],
    4: [5, 7],
    5: [7],
    6: [],
    7: [],
}


def _with_order_relations(query):
    return query.options(
        joinedload(Order.user),
        joinedload(Order.shipping_method),
        joinedload(Order.items),
    )


def _serialize_order_item(item) -> dict:
    product = item.product
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": product.name if product else None,
        "product_primary_image": image_url(product.primary_image, IMAGE_SUBDIR) if product else None,
        "color": (
            {
                "id": item.color.id,
                "name": item.color.name,
                "color_code": item.color.color_code,
                "image": image_url(item.color.image, IMAGE_SUBDIR),
            }
            if item.color
            else None
        ),
        "size": (
            {"id": item.size.id, "size": item.size.size, "price": item.size.price}
            if item.size
            else None
        ),
        "price": item.price,
        "quantity": item.quantity,
        "subtotal": item.subtotal,
    }


def _serialize_order(order: Order, with_items: bool = False) -> dict:
    status_info = STATUS_LIST.get(order.order_status, {"label": "نامشخص", "color": "secondary", "icon": "question"})
    address = order.address

    data = {
        "id": order.id,
        "user_id": order.user_id,
        "user_name": order.user.name if order.user else None,
        "user_phone": order.user.cellphone if order.user else None,
        "address_title": address.address if address else None,
        "payment_status": order.payment_status,
        "order_status": order.order_status,
        "status_label": status_info["label"],
        "status_color": status_info["color"],
        "status_icon": status_info["icon"],
        "allowed_transitions": [
            {"value": s, "label": STATUS_LIST[s]["label"], "color": STATUS_LIST[s]["color"], "icon": STATUS_LIST[s]["icon"]}
            for s in ALLOWED_TRANSITIONS.get(order.order_status, [])
        ],
        "total_amount": order.total_amount,
        "coupon_amount": order.coupon_amount,
        "shipping_amount": order.shipping_amount,
        "paying_amount": order.paying_amount,
        "shipping_method": (
            {
                "id": order.shipping_method.id,
                "name": order.shipping_method.name,
                "delivery_days": order.shipping_method.delivery_days,
                "price": order.shipping_method.price,
            }
            if order.shipping_method
            else None
        ),
        "created_at": format_jalali(order.created_at),
    }
    if with_items:
        data["order_items"] = [_serialize_order_item(i) for i in order.items]
    return data


class OrderStatusIn(BaseModel):
    status: int


@admin_router.get("/orders")
def admin_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = _with_order_relations(db.query(Order)).order_by(Order.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=15)
    return success_response(
        {
            "orders": [_serialize_order(o, with_items=True) for o in items],
            "links": links,
            "meta": meta,
            "status_list": STATUS_LIST,
        }
    )


@admin_router.get("/orders/{order_id}")
def admin_show(order_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    order = _with_order_relations(db.query(Order)).filter(Order.id == order_id).first()
    if order is None:
        return error_response("سفارش پیدا نشد", 404)
    return success_response(_serialize_order(order, with_items=True))


@admin_router.patch("/orders/{order_id}/status")
def admin_update_status(
    order_id: int,
    payload: OrderStatusIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    order = _with_order_relations(db.query(Order)).filter(Order.id == order_id).first()
    if order is None:
        return error_response("سفارش پیدا نشد", 404)

    if payload.status not in ALLOWED_TRANSITIONS.get(order.order_status, []):
        allowed_labels = "، ".join(STATUS_LIST[s]["label"] for s in ALLOWED_TRANSITIONS.get(order.order_status, []))
        return error_response(
            {"error": [f"این سفارش فقط می‌تواند به این وضعیت‌ها منتقل شود: {allowed_labels}"]}, 422
        )

    order.order_status = payload.status
    db.commit()
    return success_response(_serialize_order(order, with_items=True))
