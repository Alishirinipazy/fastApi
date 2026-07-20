from sqlalchemy import String, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class User(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    cellphone: Mapped[str | None] = mapped_column(String(32), unique=True, nullable=True)
    otp: Mapped[str | None] = mapped_column(String(16), nullable=True)
    login_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_admin: Mapped[int] = mapped_column(SmallInteger, default=0)

    addresses: Mapped[list["UserAddress"]] = relationship(back_populates="user")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user")
    tokens: Mapped[list["AccessToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
