from pydantic import BaseModel


class PaymentSendIn(BaseModel):
    address_id: int
    shipping_method_id: int
    coupon: str | None = None


class PaymentVerifyIn(BaseModel):
    """Matches the query params Zibal appends to the callback URL redirect:
    ?trackId=...&success=1&status=2&orderId=..."""
    track_id: int
    success: int
    status: int | None = None
