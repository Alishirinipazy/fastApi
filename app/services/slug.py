import re

from sqlalchemy import func
from sqlalchemy.orm import Session

# Same idea as the Laravel app's slugify(): keep any Unicode letter or digit
# (so Persian text stays Persian, no transliteration), collapse everything
# else to a single delimiter, trim, lowercase.
_NON_WORD_RE = re.compile(r"[^\w]+", re.UNICODE)


def slugify(text: str, delimiter: str = "-") -> str:
    text = text.strip()
    text = _NON_WORD_RE.sub(delimiter, text)
    text = text.strip(delimiter)
    return text.lower()


def make_unique_product_slug(db: Session, name: str) -> str:
    """
    Mirrors ProductController::makeSlug(): base slug, then if it's already
    taken, suffix it with how many rows already match that pattern.
    """
    from app.models import Product

    base = slugify(name)
    count = (
        db.query(func.count(Product.id))
        .filter(Product.slug.op("REGEXP")(f"^{re.escape(base)}(-[0-9]+)?$"))
        .scalar()
    )
    return f"{base}-{count}" if count else base
