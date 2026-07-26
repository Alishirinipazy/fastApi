from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Integer, SmallInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Car(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "cars"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)

    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="CASCADE"))
    # body-type category, e.g. Sedan, SUV, Crossover, Pickup, Hatchback
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))

    model_name: Mapped[str] = mapped_column(String(255))  # e.g. "207", "Cerato", "Tara"
    model_year: Mapped[int] = mapped_column(Integer)  # سال ساخت/تولید

    # 0 = کارکرده (used), 1 = نو (new)
    condition: Mapped[int] = mapped_column(SmallInteger, default=1)
    mileage_km: Mapped[int] = mapped_column(Integer, default=0)  # کارکرد به کیلومتر، صفر برای خودروی نو
    vin: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

    primary_image: Mapped[str] = mapped_column(String(255))
    primary_image_blur_data_url: Mapped[str] = mapped_column(
        "primary_image_blurDataURL", Text
    )
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int] = mapped_column(Integer, default=0)
    quantity: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[int] = mapped_column(SmallInteger, default=1)

    sale_price: Mapped[int] = mapped_column(Integer, default=0)
    date_on_sale_from: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    date_on_sale_to: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    brand: Mapped["Brand"] = relationship(back_populates="cars")
    category: Mapped["Category"] = relationship(back_populates="cars")
    images: Mapped[list["CarImage"]] = relationship(back_populates="car")
    colors: Mapped[list["CarColor"]] = relationship(back_populates="car")
    inquiries: Mapped[list["Inquiry"]] = relationship(back_populates="car")

    _STATUS_LABELS = {0: "غیر فعال", 1: "فعال"}
    _CONDITION_LABELS = {0: "کارکرده", 1: "نو"}

    @property
    def status_label(self) -> str:
        return self._STATUS_LABELS.get(self.status, str(self.status))

    @property
    def condition_label(self) -> str:
        return self._CONDITION_LABELS.get(self.condition, str(self.condition))

    @property
    def total_quantity(self) -> int:
        """Sum of available quantity across color options. A used car (unique, VIN-based)
        normally has exactly one color row with quantity 1; a new car may have several
        color options each with their own stock count."""
        return sum(color.quantity for color in self.colors)

    @property
    def min_price(self) -> int:
        prices = [color.price for color in self.colors]
        return min(prices) if prices else (self.sale_price or self.price)


class CarImage(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "car_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"))
    image: Mapped[str] = mapped_column(String(255))

    car: Mapped["Car"] = relationship(back_populates="images")


class CarColor(Base, TimestampMixin, SoftDeleteMixin):
    """A color option for a car. For new cars a dealership may stock the same
    model/trim in several colors (each with its own price/quantity); for a
    used car this is normally a single row describing that specific unit's
    actual color, with quantity fixed at 1."""

    __tablename__ = "car_colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    car_id: Mapped[int] = mapped_column(ForeignKey("cars.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))  # e.g. white, black, silver
    color_code: Mapped[str] = mapped_column(String(32))  # e.g. #ffffff
    image: Mapped[str] = mapped_column(String(255))
    price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    car: Mapped["Car"] = relationship(back_populates="colors")
