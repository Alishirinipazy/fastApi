from pydantic import BaseModel


class ReorderIn(BaseModel):
    ids: list[int]
