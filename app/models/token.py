from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


class AccessToken(Base):
    """
    Opaque bearer token, stored hashed - same idea as Laravel Sanctum's
    personal_access_tokens table. 'abilities' plays the role Sanctum's
    token abilities played (e.g. ["user"] or ["admin"]) and is what the
    admin-panel routes check instead of Sanctum's `ability:admin` middleware.
    """

    __tablename__ = "access_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), default="myApp")
    abilities: Mapped[list] = mapped_column(JSON, default=list)

    last_used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="tokens")
