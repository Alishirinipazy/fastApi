from pydantic import BaseModel


class PaymentSendIn(BaseModel):
    address_id: int
    # یکی از این دو باید پر باشه: یا انتخاب لجستیک تاپین (روش جدید و اصلی)،
    # یا شناسه‌ی روش ارسال ثابت قدیمی (برای سازگاری، اگه جایی هنوز ازش
    # استفاده می‌شه).
    tapin_order_type: int | None = None
    shipping_method_id: int | None = None
    coupon: str | None = None


class PaymentVerifyIn(BaseModel):
    """Matches the query params Zibal appends to the callback URL redirect:
    ?trackId=...&success=1&status=2&orderId=..."""
    track_id: int
    success: int
    status: int | None = None