from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.api.v1.auth import _serialize_user
from app.core.security import hash_password
from app.db.session import get_db
from app.models import User
from app.schemas.user import UserCreateIn, UserUpdateIn
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

admin_router = APIRouter(prefix="/admin-panel", tags=["admin-users"])


@admin_router.get("/users")
def admin_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(User).order_by(User.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=5)
    return success_response({"users": [_serialize_user(u) for u in items], "links": links, "meta": meta})


@admin_router.get("/users/{user_id}")
def admin_show(user_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return error_response("کاربر پیدا نشد", 404)
    return success_response(_serialize_user(user))


@admin_router.post("/users")
def admin_store(payload: UserCreateIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    if db.query(User).filter(User.email == payload.email).first():
        return error_response({"email": ["این ایمیل قبلا استفاده شده است"]}, 422)
    if db.query(User).filter(User.cellphone == payload.cellphone).first():
        return error_response({"cellphone": ["این شماره تماس قبلا استفاده شده است"]}, 422)

    user = User(
        name=payload.name,
        email=payload.email,
        cellphone=payload.cellphone,
        password=hash_password(payload.password),
        is_admin=1 if payload.is_admin else 0,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return success_response(_serialize_user(user))


@admin_router.put("/users/{user_id}")
@admin_router.post("/users/{user_id}")
def admin_update(
    user_id: int,
    payload: UserUpdateIn,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return error_response("کاربر پیدا نشد", 404)

    duplicate_email = db.query(User).filter(User.email == payload.email, User.id != user_id).first()
    if duplicate_email:
        return error_response({"email": ["این ایمیل قبلا استفاده شده است"]}, 422)
    duplicate_phone = db.query(User).filter(User.cellphone == payload.cellphone, User.id != user_id).first()
    if duplicate_phone:
        return error_response({"cellphone": ["این شماره تماس قبلا استفاده شده است"]}, 422)

    user.name = payload.name
    user.email = payload.email
    user.cellphone = payload.cellphone
    if payload.password:
        user.password = hash_password(payload.password)
    if payload.is_admin is not None:
        if user.id == current_admin.id and not payload.is_admin:
            return error_response({"is_admin": ["نمی‌توانید دسترسی ادمین خودتان را حذف کنید"]}, 422)
        user.is_admin = 1 if payload.is_admin else 0
    db.commit()
    return success_response(_serialize_user(user))


@admin_router.delete("/users/{user_id}")
def admin_destroy(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return error_response("کاربر پیدا نشد", 404)
    if user.id == current_admin.id:
        return error_response({"error": ["نمی‌توانید حساب خودتان را حذف کنید"]}, 422)
    db.delete(user)
    db.commit()
    return success_response(_serialize_user(user))
