from pydantic import BaseModel


class BrandIn(BaseModel):
    name: str
