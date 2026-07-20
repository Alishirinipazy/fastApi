import re

from pydantic import BaseModel, field_validator

CELLPHONE_RE = re.compile(r"^(\+98|0)?9\d{9}$")
POSTAL_CODE_RE = re.compile(r"^\d{5}[ -]?\d{5}$")


class ProfileInfoIn(BaseModel):
    name: str
    email: str


class AddressIn(BaseModel):
    title: str
    cellphone: str
    postal_code: str
    province_id: int
    city_id: int
    address: str

    @field_validator("cellphone")
    @classmethod
    def validate_cellphone(cls, v: str) -> str:
        if not CELLPHONE_RE.match(v):
            raise ValueError("cellphone must be a valid Iranian mobile number")
        return v

    @field_validator("postal_code")
    @classmethod
    def validate_postal_code(cls, v: str) -> str:
        if not POSTAL_CODE_RE.match(v):
            raise ValueError("postal_code must be a valid 10-digit postal code")
        return v


class AddressEditIn(AddressIn):
    address_id: int


class AddressDeleteIn(BaseModel):
    address_id: int
