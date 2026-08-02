import io
import time
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, ImageOps

from app.core.config import settings

# Mirrors Laravel's storage/app/public/images/{products,categories} + the
# public/storage symlink. Served at /storage via StaticFiles in app/main.py.
#
# STORAGE_ROOT is configurable (see app/core/config.py) because it MUST
# match wherever the persistent volume is actually mounted in production -
# on Runflare that's /storage, not the project-relative default below which
# only lives inside the container's ephemeral filesystem.
STORAGE_ROOT = (
    Path(settings.STORAGE_ROOT)
    if settings.STORAGE_ROOT
    else Path(__file__).resolve().parent.parent.parent / "storage"
)

# Any image wider/taller than this gets downscaled (keeps aspect ratio).
# 2000px is comfortably larger than any product/category display size on
# the site, so this only trims oversized camera/phone uploads.
MAX_DIMENSION = 2000
WEBP_QUALITY = 82  # visually near-lossless for photos, ~60-80% smaller than source


def _unique_filename(ext: str) -> str:
    """Mirrors Carbon::now()->microsecond . '.' . $file->extension()."""
    microsecond = int(time.time() * 1_000_000) % 1_000_000
    return f"{microsecond}.{ext}"


def _convert_to_webp(raw: bytes) -> bytes:
    """Resize (if needed) and re-encode an image as compressed WebP."""
    with Image.open(io.BytesIO(raw)) as img:
        img = ImageOps.exif_transpose(img)  # respect camera rotation before resizing

        if img.width > MAX_DIMENSION or img.height > MAX_DIMENSION:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)

        # Preserve transparency where it exists (logos/PNGs), otherwise flatten to RGB
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        buffer = io.BytesIO()
        img.save(buffer, format="WEBP", quality=WEBP_QUALITY, method=6)
        return buffer.getvalue()


def save_upload(upload: UploadFile, subdir: str) -> str:
    """
    Saves an uploaded file under storage/images/<subdir>/ and returns just
    the generated filename (what gets stored in the DB column) - same
    convention the Laravel controllers used.

    Image uploads (jpg/png/etc.) are automatically compressed and re-encoded
    as WebP. Non-image uploads (e.g. story videos) are stored unchanged.

    Whether a file "is an image" is decided by actually trying to decode it
    with Pillow rather than trusting the client-supplied content_type header -
    that header isn't reliably preserved by every upstream proxy (e.g. when
    a request is relayed through a Node FormData/Blob without an explicit
    mime type), so it can't be trusted as the sole signal.
    """
    target_dir = STORAGE_ROOT / "images" / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    raw = upload.file.read()

    try:
        raw = _convert_to_webp(raw)
        ext = "webp"
    except Exception:
        # Not a decodable image (e.g. a story video) - store the original
        # bytes untouched.
        ext = (upload.filename or "").rsplit(".", 1)[-1].lower() if "." in (upload.filename or "") else "bin"

    filename = _unique_filename(ext)
    destination = target_dir / filename

    with destination.open("wb") as f:
        f.write(raw)

    return filename


def delete_upload(filename: str, subdir: str) -> None:
    path = STORAGE_ROOT / "images" / subdir / filename
    if path.exists():
        path.unlink()


def image_url(filename: str | None, subdir: str) -> str | None:
    """Mirrors asset('storage/images/products/' . $filename)."""
    if not filename:
        return None
    return f"https://api.slipperpaz.ir/storage/images/{subdir}/{filename}"