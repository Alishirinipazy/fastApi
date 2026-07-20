from datetime import datetime

from sqlalchemy import String, Text, Boolean, SmallInteger, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class ContactUs(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contact_us"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255))
    subject: Mapped[str] = mapped_column(String(255))
    text: Mapped[str] = mapped_column(Text)


class Slider(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "sliders"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file: Mapped[str] = mapped_column(String(255))
    link: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)


class Story(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "stories"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[str] = mapped_column(Enum("image", "video", name="story_type"))
    file: Mapped[str] = mapped_column(String(255))
    thumbnail: Mapped[str | None] = mapped_column(String(255), nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_url: Mapped[str | None] = mapped_column(String(255), nullable=True)
    link_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort: Mapped[int] = mapped_column(SmallInteger, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
