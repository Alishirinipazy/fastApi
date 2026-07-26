import re

from pydantic import BaseModel, field_validator

CELLPHONE_RE = re.compile(r"^(\+98|0)?9\d{9}$")


class InquiryIn(BaseModel):
    car_id: int
    car_color_id: int | None = None
    full_name: str
    phone: str
    message: str | None = None
    preferred_contact_time: str | None = None

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v: str) -> str:
        if not CELLPHONE_RE.match(v):
            raise ValueError("phone must be a valid Iranian mobile number")
        return v


class InquiryStatusIn(BaseModel):
    status: int
    admin_notes: str | None = None
