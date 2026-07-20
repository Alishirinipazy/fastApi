import re

from pydantic import BaseModel, field_validator

CELLPHONE_RE = re.compile(r"^(\+98|0)?9\d{9}$")


class LoginRequest(BaseModel):
    cellphone: str

    @field_validator("cellphone")
    @classmethod
    def validate_cellphone(cls, v: str) -> str:
        if not CELLPHONE_RE.match(v):
            raise ValueError("cellphone must be a valid Iranian mobile number")
        return v


class CheckOtpRequest(BaseModel):
    otp: str
    login_token: str

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, v: str) -> str:
        if not re.match(r"^\d{6}$", v):
            raise ValueError("otp must be exactly 6 digits")
        return v


class ResendOtpRequest(BaseModel):
    login_token: str


class AdminLoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: int
    name: str | None
    email: str | None
    cellphone: str | None
    created_at: str  # formatted, see app/api/v1/auth.py

    model_config = {"from_attributes": True}
