import json
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Form, UploadFile, File
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.models import Car, CarImage, CarColor, Category, Brand, User, Inquiry
from app.schemas.car import CarColorIn
from app.services.slug import make_unique_car_slug
from app.services.storage import save_upload, image_url
from app.utils.pagination import paginate
from app.utils.response import success_response, error_response

router = APIRouter(tags=["cars"])
admin_router = APIRouter(prefix="/admin-panel", tags=["admin-cars"])

IMAGE_SUBDIR = "cars"

STATUS_LABELS = {0: "غیر فعال", 1: "فعال"}
CONDITION_LABELS = {0: "کارکرده", 1: "نو"}


def _with_variants(query):
    return query.options(
        joinedload(Car.images),
        joinedload(Car.colors),
        joinedload(Car.brand),
    )


def _total_quantity(car: Car) -> int:
    return sum(color.quantity for color in car.colors)


def _min_price(car: Car) -> int:
    prices = [color.price for color in car.colors]
    return min(prices) if prices else (car.sale_price or car.price)


def _serialize_color(color: CarColor) -> dict:
    return {
        "id": color.id,
        "name": color.name,
        "color_code": color.color_code,
        "image": image_url(color.image, IMAGE_SUBDIR),
        "price": color.price,
        "quantity": color.quantity,
        "available": color.quantity > 0,
    }


def _serialize_car(car: Car) -> dict:
    return {
        "id": car.id,
        "title": car.title,
        "slug": car.slug,
        "brand": car.brand.name if car.brand else None,
        "brand_id": car.brand_id,
        "category": car.category.name if car.category else None,
        "category_id": car.category_id,
        "model_name": car.model_name,
        "model_year": car.model_year,
        "condition_value": car.condition,
        "condition": CONDITION_LABELS.get(car.condition, car.condition),
        "mileage_km": car.mileage_km,
        "vin": car.vin,
        "primary_image": image_url(car.primary_image, IMAGE_SUBDIR),
        "status_value": car.status,
        "status": STATUS_LABELS.get(car.status, car.status),
        "description": car.description,
        "total_quantity": _total_quantity(car),
        "min_price": _min_price(car),
        "price": _min_price(car),  # kept for backwards compatibility
        "quantity": _total_quantity(car),
        "sale_price": car.sale_price or 0,
        "date_on_sale_from": car.date_on_sale_from,
        "date_on_sale_to": car.date_on_sale_to,
        "images": [
            {"id": img.id, "car_id": img.car_id, "primary_image": image_url(img.image, IMAGE_SUBDIR)}
            for img in car.images
        ],
        "colors": [_serialize_color(c) for c in car.colors],
    }


# ---------------------------------------------------------------------------
# Public
# ---------------------------------------------------------------------------

@router.get("/cars")
def list_cars(request: Request, page: int = 1, db: Session = Depends(get_db)):
    query = _with_variants(db.query(Car)).order_by(Car.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=6)
    return success_response({"cars": [_serialize_car(c) for c in items], "links": links, "meta": meta})


@router.get("/random-cars")
def random_cars(count: int, db: Session = Depends(get_db)):
    cars = _with_variants(db.query(Car)).order_by(func.rand()).limit(count).all()
    return success_response([_serialize_car(c) for c in cars])


@router.get("/menu")
def menu(
    request: Request,
    page: int = 1,
    category: int | None = None,
    brand: int | None = None,
    condition: str | None = None,  # "new" or "used"
    year_min: int | None = None,
    year_max: int | None = None,
    sort_by: str | None = None,
    search: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    color: str | None = None,
    db: Session = Depends(get_db),
):
    query = _with_variants(db.query(Car))

    if category is not None:
        query = query.filter(Car.category_id == category)

    if brand is not None:
        query = query.filter(Car.brand_id == brand)

    if condition in ("new", "used"):
        query = query.filter(Car.condition == (1 if condition == "new" else 0))

    if year_min is not None:
        query = query.filter(Car.model_year >= year_min)
    if year_max is not None:
        query = query.filter(Car.model_year <= year_max)

    if search and search.strip():
        query = query.filter(Car.title.ilike(f"%{search.strip()}%"))

    if price_min is not None or price_max is not None:
        query = query.join(Car.colors)
        if price_min is not None:
            query = query.filter(CarColor.price >= price_min)
        if price_max is not None:
            query = query.filter(CarColor.price <= price_max)
        query = query.distinct()

    if color:
        query = query.join(Car.colors).filter(CarColor.name == color).distinct()

    if sort_by == "max":
        query = query.order_by(Car.created_at.desc())
    elif sort_by == "min":
        query = query.order_by(Car.created_at.asc())
    elif sort_by == "year_new":
        query = query.order_by(Car.model_year.desc())
    elif sort_by == "year_old":
        query = query.order_by(Car.model_year.asc())
    elif sort_by == "mileage":
        query = query.order_by(Car.mileage_km.asc())
    elif sort_by == "bestseller":
        # rank by closed deals - ties fall back to newest first
        sold = (
            db.query(Inquiry.car_id, func.count(Inquiry.id).label("sold"))
            .filter(Inquiry.status == 4)  # deal closed / sold
            .group_by(Inquiry.car_id)
            .subquery()
        )
        query = query.outerjoin(sold, sold.c.car_id == Car.id).order_by(
            func.coalesce(sold.c.sold, 0).desc(), Car.created_at.desc()
        )

    items, links, meta = paginate(query, request, page, per_page=6)
    return success_response({"cars": [_serialize_car(c) for c in items], "links": links, "meta": meta})


@router.get("/filter-options")
def filter_options(db: Session = Depends(get_db)):
    """
    Metadata to populate a car-listing filter sidebar: categories/brands
    (with how many cars each has), the overall price/year range, and the
    distinct colors that actually exist - so the UI only ever offers
    filters that can return results.
    """
    categories = (
        db.query(Category.id, Category.name, Category.parent_id, func.count(Car.id).label("count"))
        .outerjoin(Car, Car.category_id == Category.id)
        .group_by(Category.id, Category.name, Category.parent_id)
        .order_by(Category.name)
        .all()
    )

    brands = (
        db.query(Brand.id, Brand.name, func.count(Car.id).label("count"))
        .outerjoin(Car, Car.brand_id == Brand.id)
        .group_by(Brand.id, Brand.name)
        .order_by(Brand.name)
        .all()
    )

    price_row = db.query(func.min(CarColor.price), func.max(CarColor.price)).first()
    price_min, price_max = price_row if price_row else (0, 0)

    year_row = db.query(func.min(Car.model_year), func.max(Car.model_year)).first()
    year_min, year_max = year_row if year_row else (0, 0)

    colors = (
        db.query(CarColor.name, CarColor.color_code)
        .distinct()
        .order_by(CarColor.name)
        .all()
    )

    return success_response({
        "categories": [
            {"id": c.id, "name": c.name, "parent_id": c.parent_id, "car_count": c.count}
            for c in categories
        ],
        "brands": [{"id": b.id, "name": b.name, "car_count": b.count} for b in brands],
        "price_range": {"min": price_min or 0, "max": price_max or 0},
        "year_range": {"min": year_min or 0, "max": year_max or 0},
        "colors": [{"name": name, "color_code": color_code} for name, color_code in colors],
        "conditions": [{"value": 1, "label": "نو"}, {"value": 0, "label": "کارکرده"}],
    })


@router.get("/cars/{slug}")
def show_car(slug: str, db: Session = Depends(get_db)):
    car = _with_variants(db.query(Car)).filter(Car.slug == slug).first()
    if car is None:
        return error_response("خودرو پیدا نشد", 404)
    return success_response(_serialize_car(car))


# ---------------------------------------------------------------------------
# Admin panel
# ---------------------------------------------------------------------------

@admin_router.get("/cars")
def admin_index(request: Request, page: int = 1, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    query = _with_variants(db.query(Car)).order_by(Car.created_at.desc())
    items, links, meta = paginate(query, request, page, per_page=6)
    return success_response({"cars": [_serialize_car(c) for c in items], "links": links, "meta": meta})


@admin_router.post("/cars")
def admin_store(
    title: str = Form(...),
    brand_id: int = Form(...),
    category_id: int = Form(...),
    model_name: str = Form(...),
    model_year: int = Form(...),
    condition: int = Form(1),
    mileage_km: int = Form(0),
    vin: str | None = Form(None),
    description: str = Form(...),
    status: int = Form(1),
    primary_image: UploadFile = File(...),
    images: list[UploadFile] | None = File(None),
    # JSON string: [{"name": "...", "color_code": "#000", "price": 1200000000, "quantity": 1}]
    colors_json: str | None = Form(None),
    # one file per entry in colors_json, same order
    colors_images: list[UploadFile] | None = File(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    primary_image_name = save_upload(primary_image, IMAGE_SUBDIR)

    car = Car(
        title=title,
        slug=make_unique_car_slug(db, title),
        brand_id=brand_id,
        category_id=category_id,
        model_name=model_name,
        model_year=model_year,
        condition=condition,
        mileage_km=mileage_km,
        vin=vin or None,
        primary_image=primary_image_name,
        primary_image_blur_data_url="",
        description=description,
        status=status,
    )
    db.add(car)
    db.flush()  # get car.id before adding children

    for image in images or []:
        db.add(CarImage(car_id=car.id, image=save_upload(image, IMAGE_SUBDIR)))

    if colors_json:
        colors_data = json.loads(colors_json)
        color_images = colors_images or []
        for index, color_data in enumerate(colors_data):
            if index >= len(color_images):
                return error_response(
                    {"colors_images": [f"تصویر رنگ شماره {index} ارسال نشده"]}, 422
                )
            color_image_name = save_upload(color_images[index], IMAGE_SUBDIR)
            db.add(
                CarColor(
                    car_id=car.id,
                    name=color_data["name"],
                    color_code=color_data["color_code"],
                    image=color_image_name,
                    price=color_data["price"],
                    quantity=color_data.get("quantity", 1),
                )
            )

    db.commit()
    db.refresh(car)
    car = _with_variants(db.query(Car)).filter(Car.id == car.id).first()
    return success_response(_serialize_car(car), 201)


@admin_router.get("/cars/{car_id}")
def admin_show(car_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    car = _with_variants(db.query(Car)).filter(Car.id == car_id).first()
    if car is None:
        return error_response("خودرو پیدا نشد", 404)
    return success_response(_serialize_car(car))


@admin_router.put("/cars/{car_id}")
@admin_router.post("/cars/{car_id}")
def admin_update(
    car_id: int,
    title: str = Form(...),
    brand_id: int = Form(...),
    category_id: int = Form(...),
    model_name: str = Form(...),
    model_year: int = Form(...),
    condition: int = Form(1),
    mileage_km: int = Form(0),
    vin: str | None = Form(None),
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
    car = db.query(Car).filter(Car.id == car_id).first()
    if car is None:
        return error_response("خودرو پیدا نشد", 404)

    if primary_image is not None:
        car.primary_image = save_upload(primary_image, IMAGE_SUBDIR)

    if title != car.title:
        car.slug = make_unique_car_slug(db, title)
    car.title = title
    car.brand_id = brand_id
    car.category_id = category_id
    car.model_name = model_name
    car.model_year = model_year
    car.condition = condition
    car.mileage_km = mileage_km
    car.vin = vin or None
    car.description = description
    car.status = status
    if price is not None:
        car.price = price
    if quantity is not None:
        car.quantity = quantity
    if sale_price is not None:
        car.sale_price = sale_price
    if date_on_sale_from:
        car.date_on_sale_from = datetime.fromisoformat(date_on_sale_from)
    if date_on_sale_to:
        car.date_on_sale_to = datetime.fromisoformat(date_on_sale_to)

    if images:
        for old_image in list(car.images):
            db.delete(old_image)
        db.flush()
        for image in images:
            db.add(CarImage(car_id=car.id, image=save_upload(image, IMAGE_SUBDIR)))

    db.commit()
    car = _with_variants(db.query(Car)).filter(Car.id == car_id).first()
    return success_response(_serialize_car(car))


@admin_router.delete("/cars/{car_id}")
def admin_destroy(car_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_admin)):
    car = db.query(Car).filter(Car.id == car_id).first()
    if car is None:
        return error_response("خودرو پیدا نشد", 404)
    db.delete(car)
    db.commit()
    return success_response({"data": ["deleted"]})


# ---------------------------------------------------------------------------
# Colors - standalone CRUD (separate from inline creation on the car itself,
# for managing color options on an existing car)
# ---------------------------------------------------------------------------

@admin_router.post("/cars/{car_id}/colors")
def admin_add_color(
    car_id: int,
    payload: CarColorIn,
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    car = db.query(Car).filter(Car.id == car_id).first()
    if car is None:
        return error_response("خودرو پیدا نشد", 404)

    color = CarColor(
        car_id=car_id,
        name=payload.name,
        color_code=payload.color_code,
        image=save_upload(image, IMAGE_SUBDIR),
        price=payload.price,
        quantity=payload.quantity,
    )
    db.add(color)
    db.commit()
    db.refresh(color)
    return success_response(_serialize_color(color), 201)


@admin_router.put("/cars/{car_id}/colors/{color_id}")
def admin_update_color(
    car_id: int,
    color_id: int,
    payload: CarColorIn,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    color = (
        db.query(CarColor)
        .filter(CarColor.id == color_id, CarColor.car_id == car_id)
        .first()
    )
    if color is None:
        return error_response("رنگ پیدا نشد", 404)

    color.name = payload.name
    color.color_code = payload.color_code
    color.price = payload.price
    color.quantity = payload.quantity
    db.commit()
    return success_response(_serialize_color(color))


@admin_router.delete("/cars/{car_id}/colors/{color_id}")
def admin_delete_color(
    car_id: int,
    color_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_admin),
):
    color = (
        db.query(CarColor)
        .filter(CarColor.id == color_id, CarColor.car_id == car_id)
        .first()
    )
    if color is None:
        return error_response("رنگ پیدا نشد", 404)
    db.delete(color)
    db.commit()
    return success_response({"data": ["deleted"]})
