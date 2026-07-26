from pydantic import BaseModel


class FavoriteIn(BaseModel):
    car_id: int
