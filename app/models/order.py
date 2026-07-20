from sqlalchemy import ForeignKey, Integer, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base
from app.models.mixins import TimestampMixin, SoftDeleteMixin


class Order(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    address_id: Mapped[int] = mapped_column(
        ForeignKey("user_addresses.id", ondelete="CASCADE")
    )
    coupon_id: Mapped[int | None] = mapped_column(
        ForeignKey("coupons.id", ondelete="CASCADE"), nullable=True
    )
    shipping_method_id: Mapped[int | None] = mapped_column(
        ForeignKey("shipping_methods.id", ondelete="SET NULL"), nullable=True
    )

    # legacy generic status field kept from the original schema
    status: Mapped[int] = mapped_column(SmallInteger, default=0)

    # 0 pending-payment, 1 paid/awaiting-processing, 2 processing, 3 ready-to-ship,
    # 4 shipped, 5 delivered, 6 cancelled, 7 returned
    order_status: Mapped[int] = mapped_column(SmallInteger, default=0)

    total_amount: Mapped[int] = mapped_column(Integer)
    coupon_amount: Mapped[int] = mapped_column(Integer, default=0)
    shipping_amount: Mapped[int] = mapped_column(Integer, default=0)
    paying_amount: Mapped[int] = mapped_column(Integer)
    payment_status: Mapped[int] = mapped_column(SmallInteger, default=0)

    user: Mapped["User"] = relationship(back_populates="orders")
    address: Mapped["UserAddress"] = relationship(back_populates="orders")
    coupon: Mapped["Coupon"] = relationship(back_populates="orders")
    shipping_method: Mapped["ShippingMethod"] = relationship(back_populates="orders")
    items: Mapped[list["OrderItems"]] = relationship(back_populates="order")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="order")


class OrderItems(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    product_color_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_colors.id", ondelete="SET NULL"), nullable=True
    )
    product_size_id: Mapped[int | None] = mapped_column(
        ForeignKey("product_sizes.id", ondelete="SET NULL"), nullable=True
    )

    price: Mapped[int] = mapped_column(Integer)
    quantity: Mapped[int] = mapped_column(Integer)
    subtotal: Mapped[int] = mapped_column(Integer)

    order: Mapped["Order"] = relationship(back_populates="items")
    product: Mapped["Product"] = relationship(back_populates="order_items")
    color: Mapped["ProductColor"] = relationship()
    size: Mapped["ProductSize"] = relationship()
