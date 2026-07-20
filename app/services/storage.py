import time
from pathlib import Path

from fastapi import UploadFile

# Mirrors Laravel's storage/app/public/images/{products,categories} + the
# public/storage symlink. Served at /storage via StaticFiles in app/main.py.
STORAGE_ROOT = Path(__file__).resolve().parent.parent.parent / "storage"


def _unique_filename(upload: UploadFile) -> str:
    """Mirrors Carbon::now()->microsecond . '.' . $file->extension()."""
    ext = (upload.filename or "").rsplit(".", 1)[-1].lower() if "." in (upload.filename or "") else "bin"
    microsecond = int(time.time() * 1_000_000) % 1_000_000
    return f"{microsecond}.{ext}"


def save_upload(upload: UploadFile, subdir: str) -> str:
    """
    Saves an uploaded file under storage/images/<subdir>/ and returns just
    the generated filename (what gets stored in the DB column) - same
    convention the Laravel controllers used.
    """
    target_dir = STORAGE_ROOT / "images" / subdir
    target_dir.mkdir(parents=True, exist_ok=True)

    filename = _unique_filename(upload)
    destination = target_dir / filename

    with destination.open("wb") as f:
        f.write(upload.file.read())

    return filename


def delete_upload(filename: str, subdir: str) -> None:
    path = STORAGE_ROOT / "images" / subdir / filename
    if path.exists():
        path.unlink()


def image_url(filename: str | None, subdir: str) -> str | None:
    """Mirrors asset('storage/images/products/' . $filename)."""
    if not filename:
        return None
    return f"/storage/images/{subdir}/{filename}"
