from datetime import datetime

from sqlalchemy import String, Text, ForeignKey, Integer, SmallInteger, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin

class Product(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    slug: Mapped[str] = mapped_column(String(255), unique=True)

    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id", ondelete="CASCADE"))

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

    category: Mapped["Category"] = relationship(back_populates="products")
    
    # ───── تغییرات مهم اینجا ─────
    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan"
    )
    colors: Mapped[list["ProductColor"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan"
    )
    order_items: Mapped[list["OrderItems"]] = relationship(
        back_populates="product"
)

class ProductImage(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "product_images"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    image: Mapped[str] = mapped_column(String(255))

    product: Mapped["Product"] = relationship(back_populates="images")


class ProductColor(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "product_colors"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(255))
    color_code: Mapped[str] = mapped_column(String(32))
    image: Mapped[str] = mapped_column(String(255))

    product: Mapped["Product"] = relationship(back_populates="colors")
    
    sizes: Mapped[list["ProductSize"]] = relationship(
        back_populates="color",
        cascade="all, delete-orphan"          # اضافه کنید
    )

class ProductSize(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "product_sizes"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_color_id: Mapped[int] = mapped_column(
        ForeignKey("product_colors.id", ondelete="CASCADE")
    )
    size: Mapped[str] = mapped_column(String(32))  # e.g. 39, 40, 41
    price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer, default=0)

    color: Mapped["ProductColor"] = relationship(back_populates="sizes")
