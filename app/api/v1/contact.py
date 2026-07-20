from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import ContactUs, User
from app.schemas.contact import ContactUsIn
from app.utils.jalali import format_jalali
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(tags=["contact"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-contact"])


def _serialize(message: ContactUs) -> dict:
    return {
        "id": message.id,
        "name": message.name,
        "email": message.email,
        "subject": message.subject,
        "text": message.text,
        "created_at": format_jalali(message.created_at),
    }


@router.post("/contact-us")
def store(payload: ContactUsIn, db: Session = Depends(get_db)):
    db.add(ContactUs(name=payload.name, email=payload.email, subject=payload.subject, text=payload.text))
    db.commit()
    return success_response("success", 201)


# ---------------------------------------------------------------------------
# Admin inbox - not in the original Laravel app (ContactUsController only
# had store()), built fresh so submissions are actually readable somewhere.
# ---------------------------------------------------------------------------

@admin_router.get("/contact-us")
def admin_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(ContactUs).order_by(ContactUs.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=10)
    return success_response({"messages": [_serialize(m) for m in items], "links": links, "meta": meta})


@admin_router.get("/contact-us/{message_id}")
def admin_show(message_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    message = db.query(ContactUs).filter(ContactUs.id == message_id).first()
    if message is None:
        return error_response("پیام پیدا نشد", 404)
    return success_response(_serialize(message))


@admin_router.delete("/contact-us/{message_id}")
def admin_destroy(message_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    message = db.query(ContactUs).filter(ContactUs.id == message_id).first()
    if message is None:
        return error_response("پیام پیدا نشد", 404)
    db.delete(message)
    db.commit()
    return success_response({"message": "پیام حذف شد"})
