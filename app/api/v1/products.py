import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Product, ProductImage, ProductColor, ProductSize, Category, User, Order, OrderItems
from app.schemas.product import ProductSizeIn
from app.services.slug import make_unique_product_slug
from app.services.storage import save_upload, image_url
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(tags=["products"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-products"])

IMAGE_SUBDIR = "products"

STATUS_LABELS = {0: "غیر فعال", 1: "فعال"}


def _with_variants(query):
    return query.options(
        joinedload(Product.images),
        joinedload(Product.colors).joinedload(ProductColor.sizes),
    )


def _total_quantity(product: Product) -> int:
    return sum(size.quantity for color in product.colors for size in color.sizes)


def _min_price(product: Product) -> int:
    prices = [size.price for color in product.colors for size in color.sizes]
    return min(prices) if prices else 0


def _serialize_size(size: ProductSize) -> dict:
    return {
        "id": size.id,
        "size": size.size,
        "price": size.price,
        "quantity": size.quantity,
        "available": size.quantity > 0,
    }


def _serialize_color(color: ProductColor) -> dict:
    return {
        "id": color.id,
        "name": color.name,
        "color_code": color.color_code,
        "image": image_url(color.image, IMAGE_SUBDIR),
        "sizes": [_serialize_size(s) for s in color.sizes],
    }


def _serialize_product(product: Product) -> dict:
    return {
        "id": product.id,
        "name": product.name,
        "slug": product.slug,
        "category": product.category.name if product.category else None,
        "category_id": product.category_id,
        "primary_image": image_url(product.primary_image, IMAGE_SUBDIR),
        "status_value": product.status,
        "status": STATUS_LABELS.get(product.status, product.status),
        "description": product.description,
        "total_quantity": _total_quantity(product),
        "min_price": _min_price(product),
        "price": _min_price(product),  # kept for backwards compatibility, as in the Laravel resource
        "quantity": _total_quantity(product),
        "sale_price": product.sale_price or 0,
        "date_on_sale_from": product.date_on_sale_from,
        "date_on_sale_to": product.date_on_sale_to,
        "images": [
            {"id": img.id, "product_id": img.product_id, "primary_image": image_url(img.image, IMAGE_SUBDIR)}
            for img in product.images
        ],
        "colors": [_serialize_color(c) for c in product.colors],
    }


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

@router.get("/products")
def list_products(request: Request, page: int = 1, db: Session = Depends(get_db)):
    query = _with_variants(db.query(Product)).order_by(Product.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=6)
    return success_response({"products": [_serialize_product(p) for p in items], "links": links, "meta": meta})


@router.get("/products/products-tabs")
def products_tabs(db: Session = Depends(get_db)):
    categories = db.query(Category).all()
    tab_list = [c.name for c in categories]
    tab_panel = []
    for category in categories:
        products = (
            _with_variants(db.query(Product))
            .filter(Product.category_id == category.id)
            .limit(9)
            .all()
        )
        tab_panel.append([_serialize_product(p) for p in products])
    return success_response({"tabList": tab_list, "tabPanel": tab_panel})


@router.get("/random-products")
def random_products(count: int, db: Session = Depends(get_db)):
    products = _with_variants(db.query(Product)).order_by(func.rand()).limit(count).all()
    return success_response([_serialize_product(p) for p in products])


@router.get("/menu")
def menu(
    request: Request,
    page: int = 1,
    category: int | None = None,
    sort_by: str | None = None,
    search: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    color: str | None = None,
    size: str | None = None,
    db: Session = Depends(get_db),
):
    query = _with_variants(db.query(Product))

    if category is not None:
        query = query.filter(Product.category_id == category)

    if search and search.strip():
        query = query.filter(Product.name.ilike(f"%{search.strip()}%"))

    if price_min is not None or price_max is not None:
        query = query.join(Product.colors).join(ProductColor.sizes)
        if price_min is not None:
            query = query.filter(ProductSize.price >= price_min)
        if price_max is not None:
            query = query.filter(ProductSize.price <= price_max)
        query = query.distinct()

    if color:
        query = query.join(Product.colors).filter(ProductColor.name == color).distinct()

    if size:
        query = (
            query.join(Product.colors)
            .join(ProductColor.sizes)
            .filter(ProductSize.size == size)
            .distinct()
        )

    if sort_by == "max":
        query = query.order_by(Product.created_at.desc())
    elif sort_by == "min":
        query = query.order_by(Product.created_at.asc())
    elif sort_by == "bestseller":
        # rank by units sold across paid orders - ties fall back to newest first
        sold = (
            db.query(OrderItems.product_id, func.sum(OrderItems.quantity).label("sold"))
            .join(Order, Order.id == OrderItems.order_id)
            .filter(Order.payment_status == 1)
            .group_by(OrderItems.product_id)
            .subquery()
        )
        query = query.outerjoin(sold, sold.c.product_id == Product.id).order_by(
            func.coalesce(sold.c.sold, 0).desc(), Product.created_at.desc()
        )

    items, links, meta = paginate(query, request, page, per_page=6)
    return success_response({"products": [_serialize_product(p) for p in items], "links": links, "meta": meta})


@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db)):
    """
    Metadata to populate a product-listing filter sidebar: categories (with
    how many products are in each), the overall price range, and the
    distinct colors/sizes that actually exist across products - so the UI
    only ever offers filters that can return results.

    This wasn't actually implemented in the original Laravel app either
    (referenced in routes/api.php, no matching CategoryController method) -
    built fresh here to power app/api/v1/products.py's /menu filters above.
    """
    categories = (
        db.query(Category.id, Category.name, Category.parent_id, func.count(Product.id).label("count"))
        .outerjoin(Product, Product.category_id == Category.id)
        .group_by(Category.id, Category.name, Category.parent_id)
        .order_by(Category.name)
        .all()
    )

    price_row = db.query(func.min(ProductSize.price), func.max(ProductSize.price)).first()
    price_min, price_max = price_row if price_row else (0, 0)

    colors = (
        db.query(ProductColor.name, ProductColor.color_code)
        .distinct()
        .order_by(ProductColor.name)
        .all()
    )

    sizes = [row[0] for row in db.query(ProductSize.size).distinct().all()]
    sizes.sort(key=lambda s: (len(s), s))  # numeric-ish sizes sort naturally, e.g. "9" before "10"

    return success_response({
        "categories": [
            {"id": c.id, "name": c.name, "parent_id": c.parent_id, "product_count": c.count}
            for c in categories
        ],
        "price_range": {"min": price_min or 0, "max": price_max or 0},
        "colors": [{"name": name, "color_code": color_code} for name, color_code in colors],
        "sizes": sizes,
    })


@router.get("/products/{slug}")
def show_product(slug: str, db: Session = Depends(get_db)):
    product = _with_variants(db.query(Product)).filter(Product.slug == slug).first()
    if product is None:
        return error_response("محصول پیدا نشد", 404)
    return success_response(_serialize_product(product))


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@admin_router.get("/products")
def admin_index(request: Request, page: int = 1, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    query = _with_variants(db.query(Product)).order_by(Product.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=6)
    return success_response({"products": [_serialize_product(p) for p in items], "links": links, "meta": meta})


@admin_router.post("/products")
def admin_store(
    name: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    status: int = Form(1),
    primary_image: UploadFile = File(...),
    images: list[UploadFile] | None = File(None),
    # JSON string: [{"name": "...", "color_code": "#000", "sizes": [{"size":"40","price":100,"quantity":5}]}]
    colors_json: str | None = Form(None),
    # one file per entry in colors_json, same order
    colors_images: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    primary_image_name = save_upload(primary_image, IMAGE_SUBDIR)

    product = Product(
        name=name,
        slug=make_unique_product_slug(db, name),
        category_id=category_id,
        primary_image=primary_image_name,
        primary_image_blur_data_url="",
        description=description,
        status=status,
    )
    db.add(product)
    db.flush()  # get product.id before adding children

    for image in images or []:
        db.add(ProductImage(product_id=product.id, image=save_upload(image, IMAGE_SUBDIR)))

    if colors_json:
        colors_data = json.loads(colors_json)
        color_images = colors_images or []
        for index, color_data in enumerate(colors_data):
            if index >= len(color_images):
                return error_response(
                    {"colors_images": [f"تصویر رنگ شماره {index} ارسال نشده"]}, 422
                )
            color_image_name = save_upload(color_images[index], IMAGE_SUBDIR)
            color = ProductColor(
                product_id=product.id,
                name=color_data["name"],
                color_code=color_data["color_code"],
                image=color_image_name,
            )
            db.add(color)
            db.flush()
            for size_data in color_data.get("sizes", []):
                db.add(
                    ProductSize(
                        product_color_id=color.id,
                        size=size_data["size"],
                        price=size_data["price"],
                        quantity=size_data["quantity"],
                    )
                )

    db.commit()
    db.refresh(product)
    product = _with_variants(db.query(Product)).filter(Product.id == product.id).first()
    return success_response(_serialize_product(product), 201)


@admin_router.get("/products/{product_id}")
def admin_show(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    product = _with_variants(db.query(Product)).filter(Product.id == product_id).first()
    if product is None:
        return error_response("محصول پیدا نشد", 404)
    return success_response(_serialize_product(product))


@admin_router.put("/products/{product_id}")
@admin_router.post("/products/{product_id}")
def admin_update(
    product_id: int,
    name: str = Form(...),
    category_id: int = Form(...),
    description: str = Form(...),
    status: int = Form(1),
    price: int | None = Form(None),
    quantity: int | None = Form(None),
    sale_price: int | None = Form(None),
    date_on_sale_from: str | None = Form(None),
    date_on_sale_to: str | None = Form(None),
    primary_image: UploadFile | None = File(None),
    images: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    """Accepts both PUT and POST (some clients spoof PUT via a _method form field)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return error_response("محصول پیدا نشد", 404)

    if primary_image is not None:
        product.primary_image = save_upload(primary_image, IMAGE_SUBDIR)

    if name != product.name:
        product.slug = make_unique_product_slug(db, name)
    product.name = name
    product.category_id = category_id
    product.description = description
    product.status = status
    if price is not None:
        product.price = price
    if quantity is not None:
        product.quantity = quantity
    if sale_price is not None:
        product.sale_price = sale_price
    if date_on_sale_from:
        product.date_on_sale_from = datetime.fromisoformat(date_on_sale_from)
    if date_on_sale_to:
        product.date_on_sale_to = datetime.fromisoformat(date_on_sale_to)

    if images:
        for old_image in list(product.images):
            db.delete(old_image)
        db.flush()
        for image in images:
            db.add(ProductImage(product_id=product.id, image=save_upload(image, IMAGE_SUBDIR)))

    db.commit()
    product = _with_variants(db.query(Product)).filter(Product.id == product_id).first()
    return success_response(_serialize_product(product))


@admin_router.delete("/products/{product_id}")
def admin_destroy(product_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return error_response("محصول پیدا نشد", 404)
    db.delete(product)
    db.commit()
    return success_response({"data": ["deleted"]})


# ---------------------------------------------------------------------------
# Colors / sizes - standalone CRUD (separate from inline creation on the
# product itself, for managing variants on an existing product)
# ---------------------------------------------------------------------------

@admin_router.post("/products/{product_id}/colors")
def admin_add_color(
    product_id: int,
    name: str = Form(...),
    color_code: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return error_response("محصول پیدا نشد", 404)

    color = ProductColor(
        product_id=product_id,
        name=name,
        color_code=color_code,
        image=save_upload(image, IMAGE_SUBDIR),
    )
    db.add(color)
    db.commit()
    db.refresh(color)
    return success_response(_serialize_color(color), 201)


@admin_router.delete("/products/{product_id}/colors/{color_id}")
def admin_delete_color(
    product_id: int,
    color_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    color = (
        db.query(ProductColor)
        .filter(ProductColor.id == color_id, ProductColor.product_id == product_id)
        .first()
    )
    if color is None:
        return error_response("رنگ پیدا نشد", 404)
    db.delete(color)
    db.commit()
    return success_response({"data": ["deleted"]})


@admin_router.post("/products/{product_id}/colors/{color_id}/sizes")
def admin_add_size(
    product_id: int,
    color_id: int,
    payload: ProductSizeIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    color = (
        db.query(ProductColor)
        .filter(ProductColor.id == color_id, ProductColor.product_id == product_id)
        .first()
    )
    if color is None:
        return error_response("رنگ پیدا نشد", 404)

    size = ProductSize(
        product_color_id=color_id,
        size=payload.size,
        price=payload.price,
        quantity=payload.quantity,
    )
    db.add(size)
    db.commit()
    db.refresh(size)
    return success_response(_serialize_size(size), 201)


@admin_router.put("/products/{product_id}/colors/{color_id}/sizes/{size_id}")
def admin_update_size(
    product_id: int,
    color_id: int,
    size_id: int,
    payload: ProductSizeIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    size = (
        db.query(ProductSize)
        .join(ProductColor)
        .filter(
            ProductSize.id == size_id,
            ProductSize.product_color_id == color_id,
            ProductColor.product_id == product_id,
        )
        .first()
    )
    if size is None:
        return error_response("سایز پیدا نشد", 404)

    size.size = payload.size
    size.price = payload.price
    size.quantity = payload.quantity
    db.commit()
    return success_response(_serialize_size(size))


@admin_router.delete("/products/{product_id}/colors/{color_id}/sizes/{size_id}")
def admin_delete_size(
    product_id: int,
    color_id: int,
    size_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    size = (
        db.query(ProductSize)
        .join(ProductColor)
        .filter(
            ProductSize.id == size_id,
            ProductSize.product_color_id == color_id,
            ProductColor.product_id == product_id,
        )
        .first()
    )
    if size is None:
        return error_response("سایز پیدا نشد", 404)
    db.delete(size)
    db.commit()
    return success_response({"data": ["deleted"]})
