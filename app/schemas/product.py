from pydantic import BaseModel


class ProductSizeIn(BaseModel):
    size: str
    price: int
    quantity: int = 0
