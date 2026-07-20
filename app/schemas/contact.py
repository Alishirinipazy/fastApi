from pydantic import BaseModel


class ContactUsIn(BaseModel):
    name: str
    email: str
    subject: str
    text: str
