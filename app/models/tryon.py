from datetime import date

from sqlalchemy import Date, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models.mixins import TimestampMixin


class TryOnUsage(Base, TimestampMixin):
    """
    One row = the user's single AI try-on for that (Iran-time) day. The unique
    (user_id, day) constraint is what enforces "one per day": two simultaneous
    requests can't both insert, so the second one is refused.
    """
    __tablename__ = "tryon_usage"
    __table_args__ = (UniqueConstraint("user_id", "day", name="uq_tryon_usage_user_day"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
