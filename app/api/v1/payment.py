from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.v1.products import _is_on_sale
from app.api.v1.tapin import cart_to_tapin_products, _split_name
from app.core.config import settings
from app.db.session import get_db
from app.models import (
    Cart, Coupon, Order, OrderItems, Product, ProductSize, ShippingMethod, Transaction, User, UserAddress,
)
from app.schemas.payment import PaymentSendIn, PaymentVerifyIn
from app.services import tapin
from app.services.tapin import TapinError
from app.services.zibal import zibal
from app.utils.response import success_response, error_response

router = APIRouter(tags=["payment"])


def _checkout_unit_price(product: Product, size: ProductSize | None) -> int:
    """Same discount logic as the cart endpoints (app/api/v1/cart.py's
    _unit_price) - kept here too since checkout recomputes prices from the
    DB independently rather than trusting the cart's cached values."""
    base = size.price if size is not None else (product.price or 0)
    return product.sale_price if _is_on_sale(product) else base


@router.post("/payment/send")
def send(
    payload: PaymentSendIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Turns the logged-in user's cart into a paid checkout attempt.

    One deliberate change from the Laravel app: PaymentController::send()
    took the cart as a raw array in the request body. Since this rewrite has
    a real server-side cart (app/models/cart.py), checkout reads from that
    instead of trusting a client-supplied cart - same net effect, one fewer
    place for client and server to disagree about what's actually in the cart.
    """
    cart = (
        db.query(Cart)
        .options(joinedload(Cart.items))
        .filter(Cart.user_id == current_user.id)
        .first()
    )
    if cart is None or not cart.items:
        return error_response({"error": ["سبد خرید شما خالی است"]}, 422)

    address = db.query(UserAddress).filter(UserAddress.id == payload.address_id).first()
    if address is None:
        return error_response({"error": ["آدرس وارد شده حذف یا وجود ندارد"]}, 422)

    if not payload.tapin_order_type and not payload.shipping_method_id:
        return error_response({"error": ["روش ارسال را انتخاب کنید"]}, 422)

    shipping = None
    if payload.shipping_method_id:
        shipping = (
            db.query(ShippingMethod)
            .filter(ShippingMethod.id == payload.shipping_method_id, ShippingMethod.is_active.is_(True))
            .first()
        )
        if shipping is None:
            return error_response({"error": ["روش ارسال انتخاب‌شده فعال نیست"]}, 422)

    # validate stock + compute total from current DB prices (never trust cached cart prices)
    total_amount = 0
    for item in cart.items:
        if item.product_size_id is not None:
            size = db.query(ProductSize).filter(ProductSize.id == item.product_size_id).first()
            if size is None:
                return error_response({"error": [f"سایز انتخاب‌شده دیگر موجود نیست"]}, 422)
            if size.quantity < item.quantity:
                return error_response({"error": [f"موجودی سایز {size.size} کافی نیست"]}, 422)
            product = size.color.product
        else:
            size = None
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product is None:
                return error_response({"error": ["محصول انتخاب‌شده دیگر موجود نیست"]}, 422)
            if (product.quantity or 0) < item.quantity:
                return error_response({"error": [f"موجودی {product.name} کافی نیست"]}, 422)
        total_amount += _checkout_unit_price(product, size) * item.quantity

    coupon = None
    coupon_amount = 0
    if payload.coupon:
        coupon = (
            db.query(Coupon)
            .filter(Coupon.code == payload.coupon, Coupon.expired_at > datetime.utcnow())
            .first()
        )
        if coupon is None:
            return error_response({"error": ["کد تخفیف وارد شده وجود ندارد"]}, 422)

        already_used = (
            db.query(Order)
            .filter(Order.user_id == current_user.id, Order.coupon_id == coupon.id, Order.payment_status == 1)
            .first()
            is not None
        )
        if already_used:
            return error_response({"error": ["شما قبلاً از این کد تخفیف استفاده کرده‌اید"]}, 422)

        coupon_amount = (total_amount * coupon.percentage) // 100

    shipping_amount = shipping.price if shipping else None
    if payload.tapin_order_type:
        products, weight = cart_to_tapin_products(cart.items)
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
                pay_type=1,
                order_type=payload.tapin_order_type,
                packet_type=settings.TAPIN_PACKET_TYPE,
                box_id=settings.TAPIN_DEFAULT_BOX_ID,
                package_weight=weight,
                products=products,
            )
        except TapinError as exc:
            return error_response({"error": [f"خطا در استعلام قیمت ارسال: {exc}"]}, 422)
        raw_price = entries.get("total_price") or entries.get("send_price")
        shipping_amount = raw_price // 10 if raw_price else None  # تاپین ریال برمی‌گردونه، اینجا تومانه
        if not shipping_amount:
            return error_response({"error": ["قیمت ارسال برای این مقصد دریافت نشد"]}, 422)

    paying_amount = (total_amount - coupon_amount) + shipping_amount

    result = zibal.request(
        amount_rials=paying_amount * 10,  # DB amounts are Toman - Zibal wants Rial
        callback_url=settings.PAYMENT_CALLBACK_URL,
        mobile=current_user.cellphone or "",
        description=f"سفارش فروشگاه - کاربر #{current_user.id}",
    )

    if result.get("result") != 100:
        return error_response(result.get("message", "خطا در اتصال به درگاه پرداخت"), 422)

    track_id = result["trackId"]

    # create the order + items + pending transaction now, mark paid on verify
    order = Order(
        user_id=current_user.id,
        address_id=payload.address_id,
        shipping_method_id=payload.shipping_method_id,
        tapin_order_type=payload.tapin_order_type,
        coupon_id=coupon.id if coupon else None,
        order_status=0,  # pending payment
        total_amount=total_amount,
        coupon_amount=coupon_amount,
        shipping_amount=shipping_amount,
        paying_amount=paying_amount,
    )
    db.add(order)
    db.flush()  # get order.id without committing yet

    for item in cart.items:
        if item.product_size_id is not None:
            size = db.query(ProductSize).filter(ProductSize.id == item.product_size_id).first()
            product = size.color.product
        else:
            size = None
            product = db.query(Product).filter(Product.id == item.product_id).first()
        unit_price = _checkout_unit_price(product, size)
        db.add(OrderItems(
            order_id=order.id,
            product_id=item.product_id,
            product_color_id=item.product_color_id,
            product_size_id=item.product_size_id,
            price=unit_price,
            quantity=item.quantity,
            subtotal=unit_price * item.quantity,
        ))

    # Zibal's trackId is an integer; stored as text in the same `token`
    # column pay.ir's opaque string token used to live in - no migration needed.
    db.add(Transaction(user_id=current_user.id, order_id=order.id, amount=paying_amount, token=str(track_id)))
    db.commit()

    return success_response({"url": zibal.start_url(track_id)})


@router.post("/payment/verify")
def verify(payload: PaymentVerifyIn, db: Session = Depends(get_db)):
    if not payload.success:
        return success_response({"status": False, "error": "پرداخت توسط شما لغو شد یا ناموفق بود"})

    transaction = db.query(Transaction).filter(Transaction.token == str(payload.track_id)).first()
    if transaction is None:
        return error_response("تراکنش پیدا نشد", 404)

    # already processed - verify can legitimately get hit more than once
    # (user refreshing the callback page, etc), so this is idempotent rather
    # than an error.
    if transaction.status == 1:
        return success_response({"status": True, "refNumber": transaction.trans_id})

    result = zibal.verify(payload.track_id)

    # 100 = freshly verified success. 201 = "already verified" from Zibal's
    # side (e.g. a race with a previous verify call) - still a success, just
    # means Zibal beat us to it; our own transaction.status check above is
    # what actually prevents double-processing the order.
    if result.get("result") not in (100, 201):
        return error_response({"error": [result.get("message", "تراکنش با خطا مواجه شد")]}, 422)

    ref_number = str(result.get("refNumber", ""))
    transaction.status = 1
    transaction.trans_id = ref_number

    order = db.query(Order).filter(Order.id == transaction.order_id).first()
    order.status = 1
    order.payment_status = 1
    order.order_status = 1  # paid

    for item in order.items:
        if item.product_size_id:
            size = db.query(ProductSize).filter(ProductSize.id == item.product_size_id).first()
            if size:
                size.quantity = max(0, size.quantity - item.quantity)
        else:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                product.quantity = max(0, (product.quantity or 0) - item.quantity)

    # اگه مشتری موقع تسویه‌حساب یکی از روش‌های ارسال تاپین رو انتخاب کرده،
    # همین الان سفارش رو در تاپین ثبت می‌کنیم تا بارکد واقعی صادر بشه.
    # عمداً توی try/except جداگونه‌ست: اگه تاپین خطا بده یا در دسترس نباشه،
    # نباید جلوی موفقیت پرداخت/سفارش رو بگیره - فقط پیام خطا ذخیره می‌شه تا
    # از پنل ادمین دستی دوباره امتحان بشه.
    if order.tapin_order_type:
        try:
            address = order.address
            first_name, last_name = _split_name(order.user.name)
            products, weight = cart_to_tapin_products(order.items)
            entries = tapin.register_order(
                manual_id=str(order.id),
                register_type=1,
                address=address.address,
                city_code=address.city_id,
                province_code=address.province_id,
                first_name=first_name,
                last_name=last_name,
                mobile=address.cellphone,
                postal_code=address.postal_code,
                pay_type=1,
                order_type=order.tapin_order_type,
                packet_type=settings.TAPIN_PACKET_TYPE,
                box_id=settings.TAPIN_DEFAULT_BOX_ID,
                package_weight=weight,
                products=products,
            )
            order.tapin_order_id = str(entries.get("order_id") or entries.get("id") or "")
            order.tapin_barcode = entries.get("barcode")
        except TapinError as exc:
            order.tapin_register_error = str(exc)[:255]

    # empty the cart now that it's turned into a paid order
    cart = db.query(Cart).filter(Cart.user_id == order.user_id).first()
    if cart:
        cart.items.clear()

    db.commit()
    return success_response({"status": True, "refNumber": ref_number})