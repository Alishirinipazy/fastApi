from fastapi import APIRouter, Depends, Form, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Brand, User
from app.services.slug import make_unique_brand_slug
from app.services.storage import save_upload, delete_upload, image_url
from app.utils.response import success_response, error_response

router = APIRouter(tags=["brands"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-brands"])

IMAGE_SUBDIR = "brands"


def _serialize(brand: Brand) -> dict:
    return {
        "id": brand.id,
        "name": brand.name,
        "slug": brand.slug,
        "logo": image_url(brand.logo, IMAGE_SUBDIR),
    }


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

@router.get("/brands")
def list_brands(db: Session = Depends(get_db)):
    brands = db.query(Brand).order_by(Brand.name).all()
    return success_response([_serialize(b) for b in brands])


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@admin_router.post("/brands")
def admin_store(
    name: str = Form(...),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    if not name.strip():
        return error_response({"name": ["نام الزامی است"]}, 422)
    if db.query(Brand).filter(Brand.name == name).first():
        return error_response({"name": ["این برند قبلا ثبت شده است"]}, 422)

    brand = Brand(
        name=name,
        slug=make_unique_brand_slug(db, name),
        logo=save_upload(logo, IMAGE_SUBDIR) if logo else None,
    )
    db.add(brand)
    db.commit()
    db.refresh(brand)
    return success_response(_serialize(brand), 201)


@admin_router.get("/brands/{brand_id}")
def admin_show(brand_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if brand is None:
        return error_response("برند پیدا نشد", 404)
    return success_response(_serialize(brand))


@admin_router.put("/brands/{brand_id}")
@admin_router.post("/brands/{brand_id}")
def admin_update(
    brand_id: int,
    name: str = Form(...),
    logo: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if brand is None:
        return error_response("برند پیدا نشد", 404)

    if logo is not None:
        if brand.logo:
            delete_upload(brand.logo, IMAGE_SUBDIR)
        brand.logo = save_upload(logo, IMAGE_SUBDIR)

    if name != brand.name:
        brand.slug = make_unique_brand_slug(db, name)
    brand.name = name
    db.commit()
    return success_response(_serialize(brand))


@admin_router.delete("/brands/{brand_id}")
def admin_destroy(brand_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    brand = db.query(Brand).filter(Brand.id == brand_id).first()
    if brand is None:
        return error_response("برند پیدا نشد", 404)
    db.delete(brand)
    db.commit()
    return success_response({"data": ["deleted"]})
