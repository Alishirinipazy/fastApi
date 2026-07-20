import re

from pydantic import BaseModel, field_validator

CELLPHONE_RE = re.compile(r"^(\+98|0)?9\d{9}$")


class UserCreateIn(BaseModel):
    name: str
    email: str
    cellphone: str
    password: str
    is_admin: bool | None = None

    @field_validator("cellphone")
    @classmethod
    def validate_cellphone(cls, v: str) -> str:
        if not CELLPHONE_RE.match(v):
            raise ValueError("cellphone must be a valid Iranian mobile number")
        return v


class UserUpdateIn(BaseModel):
    name: str
    email: str
    cellphone: str
    password: str | None = None
    is_admin: bool | None = None

    @field_validator("cellphone")
    @classmethod
    def validate_cellphone(cls, v: str) -> str:
        if not CELLPHONE_RE.match(v):
            raise ValueError("cellphone must be a valid Iranian mobile number")
        return v
