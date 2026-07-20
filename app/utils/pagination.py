import math

from fastapi import Request
from sqlalchemy.orm import Query


def paginate(query: Query, request: Request, page: int, per_page: int) -> tuple[list, dict, dict]:
    """
    Runs `query`, returns (items_for_this_page, links, meta) shaped like
    Laravel's LengthAwarePaginator JSON (the ->response()->getData()->links
    and ->meta the original controllers returned alongside the resource
    collection).
    """
    total = query.order_by(None).count()
    last_page = max(1, math.ceil(total / per_page))
    page = max(1, min(page, last_page))

    items = query.offset((page - 1) * per_page).limit(per_page).all()

    base_url = str(request.url).split("?")[0]

    def page_url(p: int | None) -> str | None:
        if p is None:
            return None
        return f"{base_url}?page={p}"

    links = {
        "first": page_url(1),
        "last": page_url(last_page),
        "prev": page_url(page - 1) if page > 1 else None,
        "next": page_url(page + 1) if page < last_page else None,
    }

    # Laravel's LengthAwarePaginator JSON includes a flat "links" array under
    # meta: [prev-arrow, 1, 2, ..., last_page, next-arrow]. The frontend's
    # pagination UI reads meta.links directly (slicing off the two arrows),
    # so this has to be here, not just the first/last/prev/next block above.
    page_links = [{"url": links["prev"], "label": "&laquo; Previous", "active": False}]
    for p in range(1, last_page + 1):
        page_links.append({"url": page_url(p), "label": str(p), "active": p == page})
    page_links.append({"url": links["next"], "label": "Next &raquo;", "active": False})

    meta = {
        "current_page": page,
        "from": (page - 1) * per_page + 1 if total else None,
        "last_page": last_page,
        "links": page_links,
        "path": base_url,
        "per_page": per_page,
        "to": min(page * per_page, total) if total else None,
        "total": total,
    }
    return items, links, meta
