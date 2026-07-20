from pydantic import BaseModel


class CartItemIn(BaseModel):
    product_id: int
    product_color_id: int | None = None
    product_size_id: int | None = None
    quantity: int = 1


class CartItemUpdate(BaseModel):
    quantity: int
