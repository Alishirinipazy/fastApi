from pydantic import BaseModel


class ShippingMethodIn(BaseModel):
    name: str
    price: int
    delivery_days: int
    is_active: bool | None = None
