from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Cart, CartItem, ProductSize, User
from app.schemas.cart import CartItemIn, CartItemUpdate
from app.services.storage import image_url
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/cart", tags=["cart"])

PRODUCT_IMAGE_SUBDIR = "products"


def _get_or_create_cart(db: Session, user: User) -> Cart:
    cart = (
        db.query(Cart)
        .options(
            joinedload(Cart.items).joinedload(CartItem.product),
            joinedload(Cart.items).joinedload(CartItem.color),
            joinedload(Cart.items).joinedload(CartItem.size),
        )
        .filter(Cart.user_id == user.id)
        .first()
    )
    if cart is None:
        cart = Cart(user_id=user.id)
        db.add(cart)
        db.commit()
        db.refresh(cart)
    return cart


def _unit_price(item: CartItem) -> int:
    if item.size is not None:
        return item.size.price
    return item.product.sale_price or item.product.price


def _serialize_item(item: CartItem) -> dict:
    unit_price = _unit_price(item)
    return {
        "id": item.id,
        "product_id": item.product_id,
        "product_name": item.product.name,
        "product_image": image_url(item.product.primary_image, PRODUCT_IMAGE_SUBDIR),
        "product_color_id": item.product_color_id,
        "color_name": item.color.name if item.color else None,
        "color_code": item.color.color_code if item.color else None,
        "color_image": image_url(item.color.image, PRODUCT_IMAGE_SUBDIR) if item.color else None,
        "product_size_id": item.product_size_id,
        "size": item.size.size if item.size else None,
        "unit_price": unit_price,
        "quantity": item.quantity,
        "subtotal": unit_price * item.quantity,
        "in_stock": (item.size.quantity if item.size else item.product.quantity) >= item.quantity,
    }


def _serialize_cart(cart: Cart) -> dict:
    items = [_serialize_item(i) for i in cart.items]
    return {
        "id": cart.id,
        "items": items,
        "items_count": sum(i["quantity"] for i in items),
        "total_amount": sum(i["subtotal"] for i in items),
    }


@router.get("")
def view_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart = _get_or_create_cart(db, current_user)
    return success_response(_serialize_cart(cart))


@router.post("/items")
def add_item(
    payload: CartItemIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.quantity < 1:
        return error_response({"quantity": ["تعداد باید حداقل ۱ باشد"]}, 422)

    if payload.product_size_id is not None:
        size = db.query(ProductSize).filter(ProductSize.id == payload.product_size_id).first()
        if size is None:
            return error_response({"product_size_id": ["سایز پیدا نشد"]}, 422)
        if size.quantity < payload.quantity:
            return error_response({"quantity": ["موجودی کافی نیست"]}, 422)

    cart = _get_or_create_cart(db, current_user)

    existing = (
        db.query(CartItem)
        .filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == payload.product_id,
            CartItem.product_color_id == payload.product_color_id,
            CartItem.product_size_id == payload.product_size_id,
        )
        .first()
    )
    if existing:
        existing.quantity += payload.quantity
    else:
        db.add(
            CartItem(
                cart_id=cart.id,
                product_id=payload.product_id,
                product_color_id=payload.product_color_id,
                product_size_id=payload.product_size_id,
                quantity=payload.quantity,
            )
        )
    db.commit()

    cart = _get_or_create_cart(db, current_user)
    return success_response(_serialize_cart(cart), 201)


@router.patch("/items/{item_id}")
def update_item(
    item_id: int,
    payload: CartItemUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(db, current_user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        return error_response("آیتم سبد خرید پیدا نشد", 404)

    if payload.quantity < 1:
        return error_response({"quantity": ["تعداد باید حداقل ۱ باشد"]}, 422)

    item.quantity = payload.quantity
    db.commit()

    cart = _get_or_create_cart(db, current_user)
    return success_response(_serialize_cart(cart))


@router.delete("/items/{item_id}")
def remove_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cart = _get_or_create_cart(db, current_user)
    item = next((i for i in cart.items if i.id == item_id), None)
    if item is None:
        return error_response("آیتم سبد خرید پیدا نشد", 404)

    db.delete(item)
    db.commit()

    cart = _get_or_create_cart(db, current_user)
    return success_response(_serialize_cart(cart))


@router.delete("")
def clear_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart = _get_or_create_cart(db, current_user)
    for item in list(cart.items):
        db.delete(item)
    db.commit()
    return success_response({"data": ["cart cleared"]})
