from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.api.v1.auth import _serialize_user
from app.api.v1.orders import _serialize_order, _with_order_relations
from app.db.session import get_db
from app.models import City, Order, Province, Transaction, User, UserAddress
from app.schemas.profile import ProfileInfoIn, AddressIn, AddressEditIn, AddressDeleteIn
from app.utils.jalali import format_jalali
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/profile", tags=["profile"])
user_router = APIRouter(tags=["profile"])


@user_router.get("/user/addresses")
def user_addresses(current_user: User = Depends(get_current_user)):
    return success_response([_serialize_address(a) for a in current_user.addresses])


def _serialize_address(address: UserAddress) -> dict:
    return {
        "id": address.id,
        "title": address.title,
        "address": address.address,
        "cellphone": address.cellphone,
        "postal_code": address.postal_code,
        "province_id": address.province_id,
        "city_id": address.city_id,
    }


def _serialize_transaction(t: Transaction) -> dict:
    return {
        "id": t.id,
        "order_id": t.order_id,
        "amount": t.amount,
        "status": t.status,
        "trans_id": t.trans_id,
        "created_at": format_jalali(t.created_at),
    }


@router.get("/info")
def info(current_user: User = Depends(get_current_user)):
    return success_response(_serialize_user(current_user))


@router.post("/info/edit")
def edit_info(
    payload: ProfileInfoIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    duplicate = (
        db.query(User).filter(User.email == payload.email, User.id != current_user.id).first()
    )
    if duplicate:
        return error_response({"email": ["این ایمیل قبلا استفاده شده است"]}, 422)

    current_user.name = payload.name
    current_user.email = payload.email
    db.commit()
    return success_response(_serialize_user(current_user))


@router.get("/addresses")
def addresses(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return success_response({
        "addresses": [_serialize_address(a) for a in current_user.addresses],
        "provinces": [{"id": p.id, "name": p.name} for p in db.query(Province).all()],
        "cities": [{"id": c.id, "name": c.name, "province_id": c.province_id} for c in db.query(City).all()],
    })


@router.post("/addresses/create")
def create_address(
    payload: AddressIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = UserAddress(user_id=current_user.id, **payload.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return success_response(_serialize_address(address))


@router.post("/addresses/edit")
def edit_address(
    payload: AddressEditIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == payload.address_id, UserAddress.user_id == current_user.id)
        .first()
    )
    if address is None:
        return error_response({"address_id": ["آدرس پیدا نشد"]}, 422)

    for field, value in payload.model_dump(exclude={"address_id"}).items():
        setattr(address, field, value)
    db.commit()
    return success_response(_serialize_address(address))


@router.post("/addresses/delete")
def delete_address(
    payload: AddressDeleteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    address = (
        db.query(UserAddress)
        .filter(UserAddress.id == payload.address_id, UserAddress.user_id == current_user.id)
        .first()
    )
    if address is None:
        return error_response({"address_id": ["آدرس پیدا نشد"]}, 422)

    db.delete(address)
    db.commit()
    return success_response(_serialize_address(address))


@router.get("/orders")
def my_orders(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = _with_order_relations(db.query(Order)).filter(Order.user_id == current_user.id).order_by(
        Order.created_at.desc()
    )
    items, links, meta = paginate(query, request, page, per_page=8)
    return success_response(
        {"orders": [_serialize_order(o, with_items=True) for o in items], "links": links, "meta": meta}
    )


@router.get("/transactions")
def my_transactions(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.id).order_by(
        Transaction.created_at.desc()
    )
    items, links, meta = paginate(query, request, page, per_page=8)
    return success_response(
        {"transactions": [_serialize_transaction(t) for t in items], "links": links, "meta": meta}
    )
