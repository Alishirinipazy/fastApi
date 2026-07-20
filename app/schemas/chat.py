from pydantic import BaseModel


class ChatMessageIn(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessageIn]
    product_slug: str | None = None  # set when the customer is chatting from a product page
