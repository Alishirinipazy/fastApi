from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Brand(Base, TimestampMixin, SoftDeleteMixin):
    """A car manufacturer, e.g. Peugeot, Iran Khodro, Toyota, Kia."""

    __tablename__ = "brands"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    slug: Mapped[str] = mapped_column(String(255), unique=True)
    logo: Mapped[str | None] = mapped_column(String(255), nullable=True)

    cars: Mapped[list["Car"]] = relationship(back_populates="brand")
