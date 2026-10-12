"""
Virtual try-on: the customer picks a product, uploads a photo of themselves,
and an image-edit model shows the product on them.

The customer's photo is processed in memory and never written to disk - the
generated image goes straight back to the browser as a data URL.
"""
import base64
import io
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from PIL import Image, ImageOps

from app.core.config import settings
from app.services.storage import STORAGE_ROOT

MAX_PHOTO_BYTES = 8 * 1024 * 1024
MAX_SIDE = 1024
REQUEST_TIMEOUT = 120.0  # image generation is slow


class TryOnError(Exception):
    """Carries a Persian, customer-facing message and an HTTP status."""

    def __init__(self, message: str, status: int = 502):
        super().__init__(message)
        self.message = message
        self.status = status


# --- per-IP rate limit (in-memory: per worker process, resets on restart) ---
_hits: dict[str, deque] = defaultdict(deque)


def allow_request(client_key: str) -> bool:
    now = time.time()
    window = settings.TRYON_RATE_WINDOW_SECONDS
    hits = _hits[client_key]
    while hits and now - hits[0] > window:
        hits.popleft()
    if len(hits) >= settings.TRYON_RATE_LIMIT:
        return False
    hits.append(now)
    return True


def _to_png(raw: bytes) -> bytes:
    with Image.open(io.BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue()


def prepare_photo(raw: bytes) -> bytes:
    if len(raw) > MAX_PHOTO_BYTES:
        raise TryOnError("حجم عکس بیشتر از ۸ مگابایته، یه عکس کوچیک‌تر انتخاب کن.", 413)
    try:
        return _to_png(raw)
    except Exception as exc:
        raise TryOnError("این فایل عکس معتبری نیست؛ یه عکس JPG یا PNG انتخاب کن.", 422) from exc


def load_product_image(filename: str | None) -> bytes:
    """Reads the product photo straight from local storage (no HTTP round trip)."""
    if not filename:
        raise TryOnError("این محصول عکس نداره.", 422)
    path = Path(STORAGE_ROOT) / "images" / "products" / Path(filename).name
    if not path.is_file():
        raise TryOnError("عکس محصول پیدا نشد.", 404)
    try:
        return _to_png(path.read_bytes())
    except Exception as exc:
        raise TryOnError("عکس محصول قابل خوندن نیست.", 422) from exc


def build_prompt(product_name: str, category: str | None, color_name: str | None) -> str:
    color_part = f" in the color {color_name}" if color_name else ""
    category_part = f" ({category})" if category else ""
    return (
        "The first image is a photo of a person. The second image is a product from an online shop: "
        f"{product_name}{category_part}{color_part}. "
        "Edit the first photo so the person is naturally wearing or using this exact product, "
        "matching the product's real shape, color and details from the second image. "
        "Keep the person's face, body, pose, clothing, background and lighting unchanged; "
        "only add or replace the product, with realistic scale, shadows and perspective. "
        "If the relevant body part is not visible in the photo, keep the photo as it is. "
        "Do not add text, logos or watermarks."
    )


def generate(photo_png: bytes, product_png: bytes, prompt: str) -> str:
    """Returns the result as a data URL. Raises TryOnError on any failure."""
    if not settings.TRYON_ENABLED:
        raise TryOnError("پروب مجازی فعلاً غیرفعاله.", 503)
    if not settings.GAPGPT_API_KEY:
        raise TryOnError("پروب مجازی هنوز راه‌اندازی نشده (کلید API تنظیم نشده).", 503)

    try:
        response = httpx.post(
            settings.TRYON_IMAGES_URL,
            headers={"Authorization": f"Bearer {settings.GAPGPT_API_KEY}"},
            data={"model": settings.TRYON_MODEL, "prompt": prompt, "n": "1", "size": "1024x1024"},
            files=[
                ("image[]", ("photo.png", photo_png, "image/png")),
                ("image[]", ("product.png", product_png, "image/png")),
            ],
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        item = response.json()["data"][0]
    except (httpx.TimeoutException, httpx.ConnectError) as exc:
        raise TryOnError("ساخت عکس طول کشید؛ دوباره امتحان کن.", 504) from exc
    except (httpx.HTTPStatusError, KeyError, IndexError, ValueError) as exc:
        raise TryOnError("ساخت عکس انجام نشد؛ چند لحظه دیگه دوباره امتحان کن.", 502) from exc

    if item.get("b64_json"):
        return f"data:image/png;base64,{item['b64_json']}"

    if item.get("url"):
        try:
            image = httpx.get(item["url"], timeout=30.0)
            image.raise_for_status()
        except httpx.HTTPError as exc:
            raise TryOnError("دریافت عکس ساخته‌شده انجام نشد.", 502) from exc
        encoded = base64.b64encode(image.content).decode()
        return f"data:image/png;base64,{encoded}"

    raise TryOnError("پاسخ نامعتبر از سرویس ساخت عکس.", 502)
