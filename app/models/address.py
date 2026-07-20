from sqlalchemy import String, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class UserAddress(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    address: Mapped[str] = mapped_column(String(255))
    cellphone: Mapped[str] = mapped_column(String(32))
    postal_code: Mapped[str] = mapped_column(String(32))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Laravel migration stores these as plain bigint, no FK constraint defined -
    # kept identical here rather than "fixing" it, to avoid surprising behavior changes.
    province_id: Mapped[int] = mapped_column(BigInteger)
    city_id: Mapped[int] = mapped_column(BigInteger)

    user: Mapped["User"] = relationship(back_populates="addresses")
    orders: Mapped[list["Order"]] = relationship(back_populates="address")
