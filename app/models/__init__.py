# Import every model here so that:
#   1) string-based relationship() references (e.g. "User", "Order") resolve correctly
#   2) Base.metadata has every table registered for Alembic autogenerate / create_all
from app.models.user import User
from app.models.token import AccessToken
from app.models.location import Province, City
from app.models.address import UserAddress
from app.models.category import Category
from app.models.product import Product, ProductImage, ProductColor, ProductSize
from app.models.coupon import Coupon
from app.models.shipping import ShippingMethod
from app.models.order import Order, OrderItems
from app.models.transaction import Transaction
from app.models.content import ContactUs, Slider, Story
from app.models.cart import Cart, CartItem

__all__ = [
    "User",
    "AccessToken",
    "Province",
    "City",
    "UserAddress",
    "Category",
    "Product",
    "ProductImage",
    "ProductColor",
    "ProductSize",
    "Coupon",
    "ShippingMethod",
    "Order",
    "OrderItems",
    "Transaction",
    "ContactUs",
    "Slider",
    "Story",
    "Cart",
    "CartItem",
]
