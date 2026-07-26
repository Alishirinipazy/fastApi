from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models import Favorite, Car, User
from app.schemas.favorite import FavoriteIn
from app.services.storage import image_url
from app.utils.response import success_response, error_response

router = APIRouter(prefix="/favorites", tags=["favorites"])

CAR_IMAGE_SUBDIR = "cars"


def _serialize(favorite: Favorite) -> dict:
    car = favorite.car
    return {
        "id": favorite.id,
        "car_id": favorite.car_id,
        "car_title": car.title if car else None,
        "car_slug": car.slug if car else None,
        "car_image": image_url(car.primary_image, CAR_IMAGE_SUBDIR) if car else None,
        "min_price": car.min_price if car else None,
    }


@router.get("")
def list_favorites(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    favorites = (
        db.query(Favorite)
        .options(joinedload(Favorite.car).joinedload(Car.colors))
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )
    return success_response([_serialize(f) for f in favorites])


@router.post("")
def add_favorite(
    payload: FavoriteIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    car = db.query(Car).filter(Car.id == payload.car_id).first()
    if car is None:
        return error_response({"car_id": ["خودرو پیدا نشد"]}, 422)

    existing = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.car_id == payload.car_id)
        .first()
    )
    if existing:
        return success_response(_serialize(existing))

    favorite = Favorite(user_id=current_user.id, car_id=payload.car_id)
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return success_response(_serialize(favorite), 201)


@router.delete("/{car_id}")
def remove_favorite(
    car_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    favorite = (
        db.query(Favorite)
        .filter(Favorite.user_id == current_user.id, Favorite.car_id == car_id)
        .first()
    )
    if favorite is None:
        return error_response("این خودرو در لیست علاقه‌مندی‌ها نیست", 404)

    db.delete(favorite)
    db.commit()
    return success_response({"data": ["removed"]})
