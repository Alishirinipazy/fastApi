from pydantic import BaseModel


class CategoryOut(BaseModel):
    id: int
    parent_id: int | None
    name: str
    description: str | None
    image: str | None  # already a full URL by the time it's serialized

    model_config = {"from_attributes": True}


class CategoryDetailOut(CategoryOut):
    children: list["CategoryOut"] = []
    parent: CategoryOut | None = None
