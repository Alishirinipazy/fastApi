from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Story, User
from app.schemas.reorder import ReorderIn
from app.services.storage import save_upload, delete_upload, image_url
from app.utils.response import success_response, error_response

router = APIRouter(tags=["stories"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-stories"])

IMAGE_SUBDIR = "stories"


def _serialize(story: Story) -> dict:
    return {
        "id": story.id,
        "title": story.title,
        "type": story.type,
        "file": image_url(story.file, IMAGE_SUBDIR),
        "thumbnail": image_url(story.thumbnail, IMAGE_SUBDIR),
        "caption": story.caption,
        "link_url": story.link_url,
        "link_label": story.link_label,
        "is_active": story.is_active,
        "sort": story.sort,
        "expires_at": story.expires_at.isoformat() if story.expires_at else None,
    }


@router.get("/stories")
def index(db: Session = Depends(get_db)):
    """Public - active, non-expired stories only. Mirrors Story::scopeActive()."""
    stories = (
        db.query(Story)
        .filter(
            Story.is_active.is_(True),
            or_(Story.expires_at.is_(None), Story.expires_at > datetime.utcnow()),
        )
        .order_by(Story.sort, Story.created_at.desc())
        .all()
    )
    return success_response([_serialize(s) for s in stories])


@admin_router.get("/stories")
def admin_index(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    stories = db.query(Story).order_by(Story.sort, Story.created_at.desc()).all()
    return success_response([_serialize(s) for s in stories])


@admin_router.post("/stories")
def admin_store(
    type: str = Form(...),
    file: UploadFile = File(...),
    thumbnail: UploadFile | None = File(None),
    title: str | None = Form(None),
    caption: str | None = Form(None),
    link_url: str | None = Form(None),
    link_label: str = Form("مشاهده"),
    is_active: bool = Form(True),
    sort: int = Form(0),
    expires_at: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    if type not in ("image", "video"):
        return error_response({"type": ["type باید image یا video باشد"]}, 422)

    story = Story(
        title=title,
        type=type,
        file=save_upload(file, IMAGE_SUBDIR),
        thumbnail=save_upload(thumbnail, IMAGE_SUBDIR) if thumbnail else None,
        caption=caption,
        link_url=link_url,
        link_label=link_label or "مشاهده",
        is_active=is_active,
        sort=sort,
        expires_at=datetime.fromisoformat(expires_at) if expires_at else None,
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return success_response(_serialize(story), 201)


@admin_router.get("/stories/{story_id}")
def admin_show(story_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        return error_response("استوری پیدا نشد", 404)
    return success_response(_serialize(story))


@admin_router.put("/stories/{story_id}")
@admin_router.post("/stories/{story_id}")
def admin_update(
    story_id: int,
    type: str | None = Form(None),
    file: UploadFile | None = File(None),
    thumbnail: UploadFile | None = File(None),
    title: str | None = Form(None),
    caption: str | None = Form(None),
    link_url: str | None = Form(None),
    link_label: str | None = Form(None),
    is_active: bool | None = Form(None),
    sort: int | None = Form(None),
    expires_at: str | None = Form(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        return error_response("استوری پیدا نشد", 404)

    if type is not None:
        if type not in ("image", "video"):
            return error_response({"type": ["type باید image یا video باشد"]}, 422)
        story.type = type
    if file is not None:
        delete_upload(story.file, IMAGE_SUBDIR)
        story.file = save_upload(file, IMAGE_SUBDIR)
    if thumbnail is not None:
        if story.thumbnail:
            delete_upload(story.thumbnail, IMAGE_SUBDIR)
        story.thumbnail = save_upload(thumbnail, IMAGE_SUBDIR)
    if title is not None:
        story.title = title
    if caption is not None:
        story.caption = caption
    if link_url is not None:
        story.link_url = link_url
    if link_label is not None:
        story.link_label = link_label
    if is_active is not None:
        story.is_active = is_active
    if sort is not None:
        story.sort = sort
    if expires_at is not None:
        story.expires_at = datetime.fromisoformat(expires_at) if expires_at else None

    db.commit()
    return success_response(_serialize(story))


@admin_router.delete("/stories/{story_id}")
def admin_destroy(story_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        return error_response("استوری پیدا نشد", 404)
    db.delete(story)
    db.commit()
    return success_response({"message": "استوری حذف شد"})


@admin_router.patch("/stories/{story_id}/toggle")
def admin_toggle(story_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    story = db.query(Story).filter(Story.id == story_id).first()
    if story is None:
        return error_response("استوری پیدا نشد", 404)
    story.is_active = not story.is_active
    db.commit()
    return success_response(_serialize(story))


@admin_router.post("/stories/reorder")
def admin_reorder(payload: ReorderIn, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    for index, story_id in enumerate(payload.ids):
        db.query(Story).filter(Story.id == story_id).update({"sort": index})
    db.commit()
    return success_response({"message": "ترتیب ذخیره شد"})
