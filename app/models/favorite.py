from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class Favorite(Base, TimestampMixin):
    """
    A user's saved/bookmarked car. Replaces the shop's server-side Cart:
    a car marketplace with an inquiry-based purchase flow doesn't need
    quantities or checkout, just a way for a customer to save listings
    they're interested in and come back to later.
    """

    __tablename__ = "favorites"
    __table_args__ = (
        UniqueConstraint("user_id", "car_id", name="uq_favorite_user_car"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"))

    user: Mapped["User"] = relationship()
    car: Mapped["Car"] = relationship()
