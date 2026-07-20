from sqlalchemy import String, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Province(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "provinces"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    cities: Mapped[list["City"]] = relationship(back_populates="province")


class City(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "cities"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    province_id: Mapped[int] = mapped_column(ForeignKey("provinces.id", ondelete="CASCADE"))

    province: Mapped["Province"] = relationship(back_populates="cities")
