from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


class TimestampMixin:
    """Mirrors Laravel's $table->timestamps()."""

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )


class SoftDeleteMixin:
    """Mirrors Laravel's $table->softDeletes() (SoftDeletes trait)."""

    deleted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, default=None)
