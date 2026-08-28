from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin, get_current_user
from app.api.v1.products import _is_on_sale
from app.core.config import settings
from app.db.session import get_db
from app.models import Cart, Order, Product, ProductSize, User, UserAddress
from app.services import tapin
from app.services.tapin import TapinError
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/tapin", tags=["tapin"])
admin_router = APIRouter(prefix="/admin-panel/tapin", tags=["admin-tapin"])

# order_type گزینه‌هایی که به مشتری نشون داده می‌شن، با عنوان فارسی و
# تخمین زمان تحویل - این‌ها ثابت‌های خودِ تاپینن، نه چیزی که ما تعریف کنیم.
SHIPPING_TIERS = [
    # این زمان‌ها مستقیم از توضیحات SLA مستندات تاپینه - خودِ اندپوینت
    # check-price هیچ فیلد زمان تحویلی برنمی‌گردونه (فقط اجزای قیمت)، پس
    # این تنها منبعیه که داریم؛ اگه توی پنل تاپین چیزی به‌روزتر دیدید،
    # همینجا عوض کنید.
    {"order_type": 1, "title": "پیشتاز", "eta": "۳ تا ۵ روز کاری"},
    {"order_type": 3, "title": "ویژه", "eta": "حدود ۲۴ ساعت"},
    {"order_type": 5, "title": "اکسپرس", "eta": "۲ تا ۳ روز کاری"},
]


def _split_name(full_name: str | None) -> tuple[str, str]:
    """Tapin wants first_name/last_name separately; we only store one
    combined `name` field - split on the first space as a best effort."""
    parts = (full_name or "مشتری").strip().split(" ", 1)
    return parts[0], (parts[1] if len(parts) > 1 else parts[0])


def cart_to_tapin_products(items) -> tuple[list[dict], int]:
    """
    Builds the `products` list Tapin's check-price/register endpoints want,
    plus a total package_weight estimate, from a list of CartItem or
    OrderItems rows (both have .product/.size/.quantity).

    Every item needs a unit price - reuses the same discount-aware pricing
    as cart.py's _unit_price (sale_price only while date_on_sale_from/to
    say the discount is actually active).
    """
    products = []
    total_weight = 0
    for item in items:
        size = getattr(item, "size", None) or getattr(item, "product_size", None)
        product = item.product
        if hasattr(item, "subtotal"):
            # OrderItems - use the price actually charged at checkout time,
            # not whatever the product/sale happens to be right now.
            unit_price = item.price
        else:
            base = size.price if size is not None else (product.price or 0)
            unit_price = product.sale_price if _is_on_sale(product) else base
        products.append({
            "count": item.quantity,
            "discount": 0,
            "price": unit_price,
            "title": product.name,
            "weight": settings.TAPIN_ITEM_WEIGHT_GRAMS,
            "product_id": None,
        })
        total_weight += settings.TAPIN_ITEM_WEIGHT_GRAMS * item.quantity
    return products, total_weight


class CheckPriceIn(BaseModel):
    address_id: int
    package_weight: int  # گرم - مجموع وزن سفارش، به‌علاوه بسته‌بندی
    box_id: int
    packet_type: int = 2  # 1=پاکت 2=بسته 3=پاکت جوف - پیش‌فرض «بسته»
    order_type: int = 1  # 1=پیشتاز 3=ویژه 5=اکسپرس
    pay_type: int = 1  # 0=COD 1=آنلاین 2=پس‌کرایه 3=رایگان
    products: list[dict]  # [{"count","discount","price","title","weight","product_id"}]


@router.get("/provinces")
def provinces():
    try:
        return success_response(tapin.get_provinces())
    except TapinError as exc:
        return error_response(str(exc), 502)


@router.get("/cities")
def cities(state_code: int):
    try:
        return success_response(tapin.get_cities(state_code))
    except TapinError as exc:
        return error_response(str(exc), 502)


@router.get("/shipping-options")
def shipping_options(
    address_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    برای صفحه‌ی سبد خرید/تسویه‌حساب: بر اساس آدرس انتخاب‌شده (که شهرش رو
    مشخص می‌کنه) و محتویات سبد خرید فعلی کاربر، لیست واقعی روش‌های ارسال
    تاپین با قیمت واقعی هر کدوم رو برمی‌گردونه تا مشتری خودش انتخاب کنه.
    """
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == address_id, UserAddress.user_id == current_user.id)
        .first()
    )
    if address is None:
        return error_response("آدرس پیدا نشد", 404)

    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items))
        .filter(Cart.user_id == current_user.id)
        .first()
    )
    if cart is None or not cart.items:
        return error_response("سبد خرید شما خالی است", 422)

    products, weight = cart_to_tapin_products(cart.items)
    first_name, last_name = _split_name(current_user.name)

    options = []
    errors = []
    for tier in SHIPPING_TIERS:
        try:
            entries = tapin.check_price(
                address=address.address,
                city_code=address.city_id,
                province_code=address.province_id,
                first_name=first_name,
                last_name=last_name,
                mobile=address.cellphone,
                postal_code=address.postal_code,
                pay_type=1,
                order_type=tier["order_type"],
                packet_type=settings.TAPIN_PACKET_TYPE,
                box_id=settings.TAPIN_DEFAULT_BOX_ID,
                package_weight=weight,
                products=products,
            )
            raw_price = entries.get("total_price") or entries.get("send_price") or 0
            options.append({
                "order_type": tier["order_type"],
                "title": tier["title"],
                "eta": tier["eta"],
                "price": raw_price // 10,  # تاپین قیمت رو به ریال برمی‌گردونه؛ همه‌جای این پروژه تومانه
            })
        except TapinError as exc:
            # یه تعرفه ممکنه برای این مقصد اصلاً پشتیبانی نشه - رد می‌شیم،
            # نه این‌که کل لیست رو خراب کنیم.
            errors.append(f"{tier['title']}: {exc}")

    if not options:
        return error_response("در حال حاضر امکان ارسال به این آدرس وجود ندارد: " + "؛ ".join(errors), 502)

    return success_response({"options": options})


@router.post("/check-price")
def check_price(
    payload: CheckPriceIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Rate quote for the logged-in user's saved address - called at checkout
    before payment, to show the real shipping cost instead of a flat
    shipping_methods price.
    """
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == payload.address_id, UserAddress.user_id == current_user.id)
        .first()
    )
    if address is None:
        return error_response("آدرس پیدا نشد", 404)

    first_name, last_name = _split_name(current_user.name)

    try:
        entries = tapin.check_price(
            address=address.address,
            city_code=address.city_id,
            province_code=address.province_id,
            first_name=first_name,
            last_name=last_name,
            mobile=address.cellphone,
            postal_code=address.postal_code,
            pay_type=payload.pay_type,
            order_type=payload.order_type,
            packet_type=payload.packet_type,
            box_id=payload.box_id,
            package_weight=payload.package_weight,
            products=payload.products,
        )
    except TapinError as exc:
        return error_response(str(exc), 502)

    # تاپین همه‌ی مبالغ رو به ریال برمی‌گردونه؛ کل پروژه تومانه.
    for key in ("total_price", "send_price", "service_price", "tax_price", "insurance_price"):
        if key in entries and entries[key] is not None:
            entries[key] = entries[key] // 10

    return success_response(entries)


@admin_router.get("/packing-boxes")
def packing_boxes(_: User = Depends(get_current_admin)):
    try:
        return success_response(tapin.get_packing_boxes())
    except TapinError as exc:
        return error_response(str(exc), 502)


@admin_router.post("/orders/{order_id}/register")
def register_order(
    order_id: int,
    box_id: int,
    package_weight: int,
    packet_type: int = 2,
    register_type: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """
    Manually registers an already-paid order with Tapin from the admin panel
    (deliberately not automatic on every payment - box_id/package_weight
    need a human to actually look at what's being shipped, and
    register_type=1 immediately deducts your Tapin wallet balance and
    issues a real barcode, so this shouldn't fire blindly).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if order is None:
        return error_response("سفارش پیدا نشد", 404)

    address = order.address
    first_name, last_name = _split_name(order.user.name)
    products, _weight = cart_to_tapin_products(order.items)

    try:
        entries = tapin.register_order(
            manual_id=str(order.id),
            register_type=register_type,
            address=address.address,
            city_code=address.city_id,
            province_code=address.province_id,
            first_name=first_name,
            last_name=last_name,
            mobile=address.cellphone,
            postal_code=address.postal_code,
            pay_type=1,
            order_type=1,
            packet_type=packet_type,
            box_id=box_id,
            package_weight=package_weight,
            products=products,
        )
    except TapinError as exc:
        return error_response(str(exc), 502)

    return success_response(entries)