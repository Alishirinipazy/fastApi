from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin, get_current_user
from app.db.session import get_db
from app.models import Car, Inquiry, User
from app.schemas.inquiry import InquiryIn, InquiryStatusIn
from app.services.storage import image_url
from app.utils.jalali import format_jalali
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(tags=["inquiries"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-inquiries"])

IMAGE_SUBDIR = "cars"

# status values
STATUS_LIST = {
    0: {"label": "در انتظار بررسی", "color": "secondary", "icon": "clock"},
    1: {"label": "تماس گرفته شد", "color": "info", "icon": "phone"},
    2: {"label": "در حال مذاکره", "color": "warning", "icon": "chat"},
    3: {"label": "بازدید/تست زمان‌بندی شد", "color": "primary", "icon": "calendar"},
    4: {"label": "معامله نهایی شد", "color": "success", "icon": "check-circle"},
    5: {"label": "لغو شد", "color": "danger", "icon": "x-circle"},
    6: {"label": "رد شد", "color": "dark", "icon": "slash-circle"},
}

ALLOWED_TRANSITIONS = {
    0: [1, 5],
    1: [2, 5],
    2: [3, 4, 5],
    3: [4, 5],
    4: [],
    5: [],
    6: [],
}


def _with_relations(query):
    return query.options(
        joinedload(Inquiry.user),
        joinedload(Inquiry.car),
        joinedload(Inquiry.color),
    )


def _serialize(inquiry: Inquiry) -> dict:
    status_info = STATUS_LIST.get(inquiry.status, {"label": "نامشخص", "color": "secondary", "icon": "question"})
    car = inquiry.car

    return {
        "id": inquiry.id,
        "user_id": inquiry.user_id,
        "user_name": inquiry.user.name if inquiry.user else None,
        "user_phone": inquiry.user.cellphone if inquiry.user else None,
        "full_name": inquiry.full_name,
        "phone": inquiry.phone,
        "message": inquiry.message,
        "preferred_contact_time": inquiry.preferred_contact_time,
        "car_id": inquiry.car_id,
        "car_title": car.title if car else None,
        "car_image": image_url(car.primary_image, IMAGE_SUBDIR) if car else None,
        "car_slug": car.slug if car else None,
        "color": (
            {"id": inquiry.color.id, "name": inquiry.color.name, "color_code": inquiry.color.color_code}
            if inquiry.color
            else None
        ),
        "status": inquiry.status,
        "status_label": status_info["label"],
        "status_color": status_info["color"],
        "status_icon": status_info["icon"],
        "allowed_transitions": [
            {"value": s, "label": STATUS_LIST[s]["label"], "color": STATUS_LIST[s]["color"], "icon": STATUS_LIST[s]["icon"]}
            for s in ALLOWED_TRANSITIONS.get(inquiry.status, [])
        ],
        "admin_notes": inquiry.admin_notes,
        "created_at": format_jalali(inquiry.created_at),
    }


# ---------------------------------------------------------------------------
# Customer-facing
# ---------------------------------------------------------------------------

@router.post("/inquiries")
def create_inquiry(
    payload: InquiryIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = db.query(Car).filter(Car.id == payload.car_id).first()
    if car is None:
        return error_response({"car_id": ["خودرو پیدا نشد"]}, 422)

    inquiry = Inquiry(
        user_id=current_user.id,
        car_id=payload.car_id,
        car_color_id=payload.car_color_id,
        full_name=payload.full_name,
        phone=payload.phone,
        message=payload.message,
        preferred_contact_time=payload.preferred_contact_time,
    )
    db.add(inquiry)
    db.commit()
    db.refresh(inquiry)
    inquiry = _with_relations(db.query(Inquiry)).filter(Inquiry.id == inquiry.id).first()
    return success_response(_serialize(inquiry), 201)


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@admin_router.get("/inquiries")
def admin_index(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = _with_relations(db.query(Inquiry)).order_by(Inquiry.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=15)
    return success_response(
        {
            "inquiries": [_serialize(i) for i in items],
            "links": links,
            "meta": meta,
            "status_list": STATUS_LIST,
        }
    )


@admin_router.get("/inquiries/{inquiry_id}")
def admin_show(inquiry_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    inquiry = _with_relations(db.query(Inquiry)).filter(Inquiry.id == inquiry_id).first()
    if inquiry is None:
        return error_response("درخواست پیدا نشد", 404)
    return success_response(_serialize(inquiry))


@admin_router.patch("/inquiries/{inquiry_id}/status")
def admin_update_status(
    inquiry_id: int,
    payload: InquiryStatusIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    inquiry = _with_relations(db.query(Inquiry)).filter(Inquiry.id == inquiry_id).first()
    if inquiry is None:
        return error_response("درخواست پیدا نشد", 404)

    if payload.status not in ALLOWED_TRANSITIONS.get(inquiry.status, []):
        allowed_labels = "، ".join(STATUS_LIST[s]["label"] for s in ALLOWED_TRANSITIONS.get(inquiry.status, []))
        return error_response(
            {"error": [f"این درخواست فقط می‌تواند به این وضعیت‌ها منتقل شود: {allowed_labels}"]}, 422
        )

    inquiry.status = payload.status
    if payload.admin_notes is not None:
        inquiry.admin_notes = payload.admin_notes
    db.commit()
    return success_response(_serialize(inquiry))
