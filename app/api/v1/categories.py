from fastapi import APIRouter, Depends, Form, Request, UploadFile, File,Query
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Category, User
from app.services.storage import save_upload, delete_upload, image_url
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(tags=["categories"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-categories"])

IMAGE_SUBDIR = "categories"


def _serialize(category: Category, with_children=False, with_parent=False, with_products=False) -> dict:
    data = {
        "id": category.id,
        "parent_id": category.parent_id,
        "parent_name": category.parent.name if category.parent_id and category.parent else None,
        "name": category.name,
        "description": category.description,
        "image": image_url(category.image, IMAGE_SUBDIR),
    }
    if with_children:
        data["children"] = [_serialize(c) for c in category.children]
    if with_parent:
        data["parent"] = _serialize(category.parent) if category.parent_id and category.parent else None
    if with_products:
        # Local import avoids a circular import with app/api/v1/products.py
        from app.api.v1.products import _serialize_product

        data["products"] = [_serialize_product(p) for p in category.products]
    return data


def _get_or_404(db: Session, category_id: int) -> Category | None:
    return db.query(Category).filter(Category.id == category_id).first()


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

@router.get("/categories")
def list_categories(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    return success_response([_serialize(c) for c in categories])


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@admin_router.get("/categories")
def admin_index(
    request: Request,
    page: int = Query(1, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    query = db.query(Category).order_by(Category.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=10)
    return success_response({"categories": [_serialize(c) for c in items], "links": links, "meta": meta})


@admin_router.get("/categories-list")
def admin_list(db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    categories = db.query(Category).all()
    return success_response([_serialize(c) for c in categories])


@admin_router.post("/categories")
def admin_store(
    name: str = Form(...),
    description: str | None = Form(None),
    parent_id: int | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    if not name.strip():
        return error_response({"name": ["نام الزامی است"]}, 422)

    if parent_id is not None and _get_or_404(db, parent_id) is None:
        return error_response({"parent_id": ["دسته‌بندی والد پیدا نشد"]}, 422)

    image_name = save_upload(image, IMAGE_SUBDIR) if image else None

    category = Category(
        name=name,
        description=description,
        parent_id=parent_id,
        image=image_name,
    )
    db.add(category)
    db.commit()
    db.refresh(category)

    return success_response(_serialize(category), 201)


@admin_router.get("/categories/{category_id}")
def admin_show(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    category = _get_or_404(db, category_id)
    if category is None:
        return error_response("دسته‌بندی پیدا نشد", 404)
    return success_response(_serialize(category))


@admin_router.put("/categories/{category_id}")
@admin_router.post("/categories/{category_id}")
def admin_update(
    category_id: int,
    name: str = Form(...),
    description: str | None = Form(None),
    parent_id: int | None = Form(None),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Accepts both PUT and POST (some clients spoof PUT via a _method form field)."""
    category = _get_or_404(db, category_id)
    if category is None:
        return error_response("دسته‌بندی پیدا نشد", 404)

    if not name.strip():
        return error_response({"name": ["نام الزامی است"]}, 422)

    if parent_id is not None:
        if parent_id == category_id:
            return error_response({"parent_id": ["یک دسته‌بندی نمی‌تواند والد خودش باشد"]}, 422)
        if _get_or_404(db, parent_id) is None:
            return error_response({"parent_id": ["دسته‌بندی والد پیدا نشد"]}, 422)

    if image is not None:
        if category.image:
            delete_upload(category.image, IMAGE_SUBDIR)
        category.image = save_upload(image, IMAGE_SUBDIR)

    category.name = name
    category.description = description
    category.parent_id = parent_id
    db.commit()

    return success_response(_serialize(category))


@admin_router.delete("/categories/{category_id}")
def admin_destroy(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    category = _get_or_404(db, category_id)
    if category is None:
        return error_response("دسته‌بندی پیدا نشد", 404)

    db.delete(category)
    db.commit()
    return success_response({"data": ["deleted"]})


@admin_router.get("/categories/{category_id}/children")
def admin_children(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    category = (
        db.query(Category).options(joinedload(Category.children)).filter(Category.id == category_id).first()
    )
    if category is None:
        return error_response("دسته‌بندی پیدا نشد", 404)
    return success_response(_serialize(category, with_children=True))


@admin_router.get("/categories/{category_id}/parent")
def admin_parent(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    category = (
        db.query(Category).options(joinedload(Category.parent)).filter(Category.id == category_id).first()
    )
    if category is None:
        return error_response("دسته‌بندی پیدا نشد", 404)
    return success_response(_serialize(category, with_parent=True))


@admin_router.get("/categories/{category_id}/products")
def admin_products(category_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    category = (
        db.query(Category)
        .options(joinedload(Category.products))
        .filter(Category.id == category_id)
        .first()
    )
    if category is None:
        return error_response("دسته‌بندی پیدا نشد", 404)
    return success_response(_serialize(category, with_products=True))
