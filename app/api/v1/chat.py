from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from sqlalchemy.orm import Session

from app.api.deps import get_current_user_optional
from app.db.session import get_db
from app.models import User
from app.schemas.chat import ChatRequest
from app.api.v1 import products as catalog
from app.models import Product
from app.services import try_on
from app.services.ai_assistant import run_assistant
from app.utils.response import success_response, error_response

router = APIRouter(tags=["chat"])


@router.post("/chat")
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    AI shopping assistant. Works for guests (search/browse) and logged-in
    users (search/browse + add to cart). The client sends the full
    conversation each time (stateless) - same pattern as any other Claude
    API integration; there's no server-side chat history storage here.
    """
    messages = [{"role": m.role, "content": m.content} for m in payload.messages]
    result = run_assistant(db, current_user, messages, product_slug=payload.product_slug)
    return success_response(result)


@router.post("/chat/try-on")
def virtual_try_on(
    request: Request,
    product_slug: str = Form(...),
    color_id: int | None = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """
    Virtual try-on: shows the chosen product on the customer's own photo.
    Guests can use it too; it is rate-limited per client IP because every
    call costs an image-generation request.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    client_key = forwarded.split(",")[0].strip() or (request.client.host if request.client else "unknown")
    if not try_on.allow_request(client_key):
        return error_response("تعداد دفعات امتحان کردن زیاد شد؛ چند دقیقه دیگه دوباره امتحان کن.", 429)

    product = (
        catalog._with_variants(catalog._active_products(db))
        .filter(Product.slug == product_slug, Product.status == 1)
        .first()
    )
    if product is None:
        return error_response("محصول پیدا نشد", 404)

    color = next((c for c in catalog._active_colors(product) if c.id == color_id), None)

    try:
        photo_png = try_on.prepare_photo(photo.file.read())
        # when the customer picked a color, that color's own photo is the best reference
        product_png = try_on.load_product_image(color.image if color else product.primary_image)
        prompt = try_on.build_prompt(
            product.name, product.category.name if product.category else None, color.name if color else None
        )
        image = try_on.generate(photo_png, product_png, prompt)
    except try_on.TryOnError as exc:
        return error_response(exc.message, exc.status)

    return success_response({"image": image})
