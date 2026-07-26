from pydantic import BaseModel


class CarColorIn(BaseModel):
    name: str
    color_code: str
    price: int
    quantity: int = 1
