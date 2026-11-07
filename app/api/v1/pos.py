"""
In-store sales (فروش حضوری) paid on a physical card reader (کارتخوان).

There is no payment gateway here: the cashier enters the amount on the card
reader, the customer pays, and only then does the cashier confirm in the UI
(optionally typing the receipt reference). That confirmation creates an
already-paid, already-delivered order and takes the goods out of stock.

Everything requires an admin token - the page is not linked from the public
site, but that alone is not protection; these endpoints are.
"""
import re
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.api.v1.payment import _checkout_unit_price
from app.api.v1.products import (
    IMAGE_SUBDIR, _active_products, _has_variants, _is_on_sale, _min_price, _total_quantity, _with_variants,
    _active_colors,
)
from app.db.session import get_db
from app.models import Order, OrderItems, Product, ProductColor, ProductSize, Transaction, User
from app.services.storage import image_url
from app.utils.response import error_response, success_response

admin_router = APIRouter(prefix="/admin-panel/pos", tags=["admin-pos"])

PHONE_RE = re.compile(r"^09\d{9}$")
IRAN_OFFSET = timedelta(hours=3, minutes=30)
DELIVERED = 5  # in-store goods are handed over on the spot


class CartLine(BaseModel):
    product_id: int
    color_id: int | None = None
    size_id: int | None = None
    quantity: int = Field(ge=1, le=100)


class CheckoutIn(BaseModel):
    client_key: str = Field(min_length=8, max_length=64)  # idempotency: a double tap must not sell twice
    items: list[CartLine] = Field(min_length=1, max_length=100)
    expected_total: int = Field(ge=0)  # what the cashier typed into the card reader
    discount: int = Field(default=0, ge=0)
    reference: str | None = Field(default=None, max_length=64)
    customer_phone: str | None = None
    customer_name: str | None = Field(default=None, max_length=255)


def _slim_product(product: Product) -> dict:
    on_sale = _is_on_sale(product)
    regular = _min_price(product)
    return {
        "id": product.id,
        "name": product.name,
        "image": image_url(product.primary_image, IMAGE_SUBDIR),
        "has_variants": _has_variants(product),
        "stock": _total_quantity(product),
        "on_sale": on_sale,
        "regular_price": regular,
        "final_price": product.sale_price if on_sale else regular,
        "price": product.price or 0,
        "colors": [
            {
                "id": c.id,
                "name": c.name,
                "color_code": c.color_code,
                "image": image_url(c.image, IMAGE_SUBDIR),
                "sizes": [
                    {"id": s.id, "size": s.size, "price": s.price, "quantity": s.quantity}
                    for s in c.sizes if s.deleted_at is None
                ],
            }
            for c in _active_colors(product)
        ],
    }


@admin_router.get("/catalog")
def catalog(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    """Every active product, grouped into sections by category - one page, no pagination."""
    products = (
        _with_variants(_active_products(db))
        .options(joinedload(Product.category))
        .filter(Product.status == 1)
        .order_by(Product.name)
        .all()
    )
    sections: dict[int, dict] = {}
    for product in products:
        cat = product.category
        key = cat.id if cat else 0
        section = sections.setdefault(key, {"id": key, "name": cat.name if cat else "سایر", "products": []})
        section["products"].append(_slim_product(product))
    ordered = sorted(sections.values(), key=lambda s: s["name"])
    return success_response({"sections": ordered, "total_products": len(products)})


def _walkin_user(db: Session, phone: str | None, name: str | None) -> User:
    if phone:
        user = db.query(User).filter(User.cellphone == phone).first()
        if user is None:
            user = User(cellphone=phone, name=name or None)
            db.add(user)
            db.flush()
        elif name and not user.name:
            user.name = name
        return user
    user = db.query(User).filter(User.email == "walkin@instore.local").first()
    if user is None:
        user = User(name="مشتری حضوری", email="walkin@instore.local", is_admin=0)
        db.add(user)
        db.flush()
    return user


def _serialize_order(order: Order, lines: list[dict] | None = None) -> dict:
    return {
        "id": order.id,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "total_amount": order.total_amount,
        "discount": order.coupon_amount,
        "paying_amount": order.paying_amount,
        "reference": order.pos_reference,
        "customer_phone": order.user.cellphone if order.user else None,
        "items": lines if lines is not None else [
            {
                "name": i.product.name if i.product else "",
                "color": i.color.name if i.color else None,
                "size": i.size.size if i.size else None,
                "price": i.price,
                "quantity": i.quantity,
                "subtotal": i.subtotal,
            }
            for i in order.items
        ],
    }


@admin_router.post("/checkout")
def checkout(payload: CheckoutIn, db: Session = Depends(get_db), admin: User = Depends(get_current_admin)):
    token = f"pos:{payload.client_key}"
    existing = db.query(Transaction).filter(Transaction.token == token).first()
    if existing is not None:
        order = db.query(Order).filter(Order.id == existing.order_id).first()
        return success_response(_serialize_order(order))

    phone = (payload.customer_phone or "").strip() or None
    if phone and not PHONE_RE.match(phone):
        return error_response("شماره موبایل مشتری درست نیست (مثال: 09121234567)", 422)

    # merge duplicate lines (same product/colour/size)
    merged: dict[tuple, int] = defaultdict(int)
    for line in payload.items:
        merged[(line.product_id, line.color_id, line.size_id)] += line.quantity

    resolved = []  # (product, color, size, qty, unit_price)
    for (product_id, color_id, size_id), qty in merged.items():
        product = _with_variants(_active_products(db)).filter(Product.id == product_id, Product.status == 1).first()
        if product is None:
            return error_response("یکی از محصولات پیدا نشد یا غیرفعاله", 422)

        color = size = None
        if _has_variants(product):
            color = next((c for c in _active_colors(product) if c.id == color_id), None)
            size = next((s for s in color.sizes if s.id == size_id and s.deleted_at is None), None) if color else None
            if color is None or size is None:
                return error_response(f"برای «{product.name}» رنگ و سایز را انتخاب کن", 422)
            if size.quantity < qty:
                return error_response(f"«{product.name}» ({color.name}، سایز {size.size}) فقط {size.quantity} عدد موجودی داره", 422)
        elif (product.quantity or 0) < qty:
            return error_response(f"«{product.name}» فقط {product.quantity or 0} عدد موجودی داره", 422)

        resolved.append((product, color, size, qty, _checkout_unit_price(product, size)))

    total = sum(unit * qty for _, _, _, qty, unit in resolved)
    if payload.discount > total:
        return error_response("تخفیف نمی‌تونه از جمع فاکتور بیشتر باشه", 422)
    paying = total - payload.discount

    if paying != payload.expected_total:
        # prices/stock moved since the cashier built the cart - never charge a different amount than was shown
        return error_response(
            f"مبلغ فاکتور تغییر کرده؛ مبلغ درست {paying:,} تومانه. کارتخوان رو با همین مبلغ دوباره بزن.", 409,
        )

    customer = _walkin_user(db, phone, (payload.customer_name or "").strip() or None)

    order = Order(
        user_id=customer.id,
        address_id=None,
        status=1,
        order_status=DELIVERED,
        payment_status=1,
        total_amount=total,
        coupon_amount=payload.discount,
        shipping_amount=0,
        paying_amount=paying,
        sales_channel="pos",
        payment_method="pos",
        pos_reference=(payload.reference or "").strip() or None,
        cashier_id=admin.id,
    )
    db.add(order)
    db.flush()

    lines = []
    for product, color, size, qty, unit in resolved:
        # atomic "take from stock only if enough is left" - two cashiers (or a website order) can't oversell
        if size is not None:
            stmt = (
                update(ProductSize)
                .where(ProductSize.id == size.id, ProductSize.quantity >= qty)
                .values(quantity=ProductSize.quantity - qty)
            )
        else:
            stmt = (
                update(Product)
                .where(Product.id == product.id, Product.quantity >= qty)
                .values(quantity=Product.quantity - qty)
            )
        if db.execute(stmt).rowcount != 1:
            db.rollback()
            return error_response(f"موجودی «{product.name}» همین الان تموم شد", 409)

        db.add(OrderItems(
            order_id=order.id,
            product_id=product.id,
            product_color_id=color.id if color else None,
            product_size_id=size.id if size else None,
            price=unit,
            quantity=qty,
            subtotal=unit * qty,
        ))
        lines.append({
            "name": product.name,
            "color": color.name if color else None,
            "size": size.size if size else None,
            "price": unit,
            "quantity": qty,
            "subtotal": unit * qty,
        })

    db.add(Transaction(
        user_id=customer.id, order_id=order.id, amount=paying, token=token,
        trans_id=order.pos_reference, status=1,
    ))
    db.commit()
    db.refresh(order)
    return success_response(_serialize_order(order, lines), 201)


@admin_router.get("/orders")
def today_orders(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    """In-store sales since midnight (Iran time) - for the cashier's end-of-day count."""
    now_local = datetime.utcnow() + IRAN_OFFSET
    start_utc = now_local.replace(hour=0, minute=0, second=0, microsecond=0) - IRAN_OFFSET
    orders = (
        db.query(Order)
        .options(joinedload(Order.user), joinedload(Order.items).joinedload(OrderItems.product),
                 joinedload(Order.items).joinedload(OrderItems.color), joinedload(Order.items).joinedload(OrderItems.size))
        .filter(Order.sales_channel == "pos", Order.created_at >= start_utc, Order.deleted_at.is_(None))
        .order_by(Order.id.desc())
        .limit(200)
        .all()
    )
    return success_response({
        "count": len(orders),
        "sum": sum(o.paying_amount for o in orders if o.order_status != 6),
        "orders": [_serialize_order(o) for o in orders],
    })
