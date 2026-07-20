from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Slider, User
from app.schemas.reorder import ReorderIn
from app.services.storage import save_upload, delete_upload, image_url
from app.utils.response import success_response, error_response

router = APIRouter(tags=["sliders"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-sliders"])

IMAGE_SUBDIR = "sliders"


def _serialize(slider: Slider) -> dict:
    return {
        "id": slider.id,
        "title": slider.title,
        "file": image_url(slider.file, IMAGE_SUBDIR),
        "link": slider.link,
        "is_active": slider.is_active,
        "sort": slider.sort,
    }


@router.get("/sliders")
def index(db: Session = Depends(get_db)):
    """Public - active sliders only, in display order."""
    sliders = (
        db.query(Slider)
        .filter(Slider.is_active.is_(True))
        .order_by(Slider.sort, Slider.created_at.desc())
        .all()
    )
    return success_response([_serialize(s) for s in sliders])


@admin_router.get("/sliders")
def admin_index(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    sliders = db.query(Slider).order_by(Slider.sort, Slider.created_at.desc()).all()
    return success_response([_serialize(s) for s in sliders])


@admin_router.post("/sliders")
def admin_store(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    link: str | None = Form(None),
    is_active: bool = Form(True),
    sort: int = Form(0),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    slider = Slider(
        title=title,
        file=save_upload(file, IMAGE_SUBDIR),
        link=link,
        is_active=is_active,
        sort=sort,
    )
    db.add(slider)
    db.commit()
    db.refresh(slider)
    return success_response(_serialize(slider), 201)


@admin_router.get("/sliders/{slider_id}")
def admin_show(slider_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    slider = db.query(Slider).filter(Slider.id == slider_id).first()
    if slider is None:
        return error_response("اسلاید پیدا نشد", 404)
    return success_response(_serialize(slider))


@admin_router.put("/sliders/{slider_id}")
@admin_router.post("/sliders/{slider_id}")
def admin_update(
    slider_id: int,
    file: UploadFile | None = File(None),
    title: str | None = Form(None),
    link: str | None = Form(None),
    is_active: bool | None = Form(None),
    sort: int | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    slider = db.query(Slider).filter(Slider.id == slider_id).first()
    if slider is None:
        return error_response("اسلاید پیدا نشد", 404)

    if file is not None:
        delete_upload(slider.file, IMAGE_SUBDIR)
        slider.file = save_upload(file, IMAGE_SUBDIR)
    if title is not None:
        slider.title = title
    if link is not None:
        slider.link = link
    if is_active is not None:
        slider.is_active = is_active
    if sort is not None:
        slider.sort = sort

    db.commit()
    return success_response(_serialize(slider))


@admin_router.delete("/sliders/{slider_id}")
def admin_destroy(slider_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    slider = db.query(Slider).filter(Slider.id == slider_id).first()
    if slider is None:
        return error_response("اسلاید پیدا نشد", 404)
    db.delete(slider)
    db.commit()
    return success_response({"message": "اسلاید با موفقیت حذف شد"})


@admin_router.patch("/sliders/{slider_id}/toggle")
def admin_toggle(slider_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    slider = db.query(Slider).filter(Slider.id == slider_id).first()
    if slider is None:
        return error_response("اسلاید پیدا نشد", 404)
    slider.is_active = not slider.is_active
    db.commit()
    return success_response(_serialize(slider))


@admin_router.post("/sliders/reorder")
def admin_reorder(payload: ReorderIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    for index, slider_id in enumerate(payload.ids):
        db.query(Slider).filter(Slider.id == slider_id).update({"sort": index})
    db.commit()
    return success_response({"message": "ترتیب ذخیره شد"})
