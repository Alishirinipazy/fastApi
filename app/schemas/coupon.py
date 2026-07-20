from datetime import datetime

from pydantic import BaseModel


class CouponIn(BaseModel):
    code: str
    percentage: int
    expired_at: datetime


class CouponCheckIn(BaseModel):
    code: str
