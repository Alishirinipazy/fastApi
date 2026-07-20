from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin


class Cart(Base, TimestampMixin):
    """
    NOTE: there was no CartController/cart table in the Laravel app - the
    frontend kept the cart in its own store (stores/cart.js) and only hit
    the API at checkout to create an Order directly. This is new server-side
    persistence added for this rewrite so the cart survives across devices;
    say if a stateless/client-only cart is preferred instead.
    """

    __tablename__ = "carts"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)

    user: Mapped["User"] = relationship()
    items: Mapped[list["CartItem"]] = relationship(
        back_populates="cart", cascade="all, delete-orphan"
    )


class CartItem(Base, TimestampMixin):
    __tablename__ = "cart_items"
    __table_args__ = (
        UniqueConstraint(
            "cart_id", "product_id", "product_color_id", "product_size_id",
            name="uq_cart_item_variant",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    product_color_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_colors.id", ondelete="CASCADE"), nullable=True
    )
    product_size_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_sizes.id", ondelete="CASCADE"), nullable=True
    )
    quantity: Mapped[int] = mapped_column(Integer, default=1)

    cart: Mapped["Cart"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship()
    color: Mapped["ProductColor"] = relationship()
    size: Mapped["ProductSize"] = relationship()
