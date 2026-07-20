from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_current_admin
from app.core.config import settings
from app.core.security import (
    generate_otp,
    generate_login_token,
    generate_plain_access_token,
    hash_access_token,
    hash_password,
    verify_password,
)
from app.db.session import get_db
from app.models import User, AccessToken
from app.schemas.auth import (
    LoginRequest,
    CheckOtpRequest,
    ResendOtpRequest,
    AdminLoginRequest,
)
from app.services.sms import sms_service
from app.utils.jalali import format_jalali
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/auth", tags=["auth"])


def _serialize_user(user: User) -> dict:
    """Mirrors UserResource::toArray(), plus is_admin (added for admin user management)."""
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "cellphone": user.cellphone,
        "is_admin": bool(user.is_admin),
        "created_at": format_jalali(user.created_at),
    }


def _issue_token(db: Session, user: User, abilities: list[str]) -> str:
    """Mirrors $user->createToken('myApp', [...])->plainTextToken."""
    plain = generate_plain_access_token()
    expires_at = None
    if settings.TOKEN_EXPIRE_MINUTES:
        expires_at = datetime.utcnow() + timedelta(minutes=settings.TOKEN_EXPIRE_MINUTES)

    token = AccessToken(
        user_id=user.id,
        token_hash=hash_access_token(plain),
        name="myApp",
        abilities=abilities,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    return plain


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    otp_code = generate_otp()
    login_token = generate_login_token()

    user = db.query(User).filter(User.cellphone == payload.cellphone).first()
    if user:
        user.otp = otp_code
        user.login_token = login_token
    else:
        user = User(cellphone=payload.cellphone, otp=otp_code, login_token=login_token)
        db.add(user)
    db.commit()
    db.refresh(user)

    sms_service.send_otp(user.cellphone, otp_code)

    return success_response({"login_token": login_token}, 200)


@router.post("/check-otp")
def check_otp(payload: CheckOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login_token == payload.login_token).first()
    if user is None:
        return error_response({"login_token": ["invalid login_token"]}, 422)

    if user.otp != payload.otp:
        return error_response({"otp": ["کد ورود نادرست است"]}, 422)

    token = _issue_token(db, user, ["user"])
    return success_response({"user": _serialize_user(user), "token": token}, 200)


@router.post("/resend-otp")
def resend_otp(payload: ResendOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.login_token == payload.login_token).first()
    if user is None:
        return error_response({"login_token": ["invalid login_token"]}, 422)

    otp_code = generate_otp()
    login_token = generate_login_token()
    user.otp = otp_code
    user.login_token = login_token
    db.commit()

    sms_service.send_otp(user.cellphone, otp_code)

    return success_response({"login_token": login_token}, 200)


@router.post("/me")
def me(current_user: User = Depends(get_current_user)):
    return success_response(_serialize_user(current_user), 200)


@router.post("/logout")
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    db.query(AccessToken).filter(AccessToken.user_id == current_user.id).delete()
    db.commit()
    return success_response({"data": ["logged out"]}, 200)


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

admin_router = APIRouter(prefix="/admin-panel/auth", tags=["admin-auth"])


@admin_router.post("/login")
def login_admin(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()

    if not user:
        return error_response({"user": ["کاربر مورد نظر پیدا نشد"]}, 422)
    if user.is_admin == 0:
        return error_response({"user": ["کاربر مورد نظر پیدا نشد"]}, 422)
    if not verify_password(payload.password, user.password or ""):
        return error_response({"password": ["پسورد اشتباه است"]}, 422)

    token = _issue_token(db, user, ["admin"])
    return success_response({"user": _serialize_user(user), "token": token}, 200)


@admin_router.post("/me")
def me_admin(current_admin: User = Depends(get_current_admin)):
    return success_response(_serialize_user(current_admin), 200)


@admin_router.post("/logout")
def logout_admin(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    db.query(AccessToken).filter(AccessToken.user_id == current_admin.id).delete()
    db.commit()
    return success_response({"data": ["logged out"]}, 200)
