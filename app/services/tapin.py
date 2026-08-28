"""
Client for Tapin (تاپین) - api.tapin.ir/api/v2/public/. Docs: docs.tapin.ir

Auth: every request needs an `Authorization: JWT <token>` header. The token
is a static, long-lived credential generated manually from the Tapin
dashboard (یکپارچه‌سازی > مدیریت توکن) - there is no login/refresh API call,
so it's just read from settings.TAPIN_TOKEN.

Every endpoint replies with the same envelope:
    {"returns": {"status": 200, "message": "..."}, "entries": {...}}
`_post()` unwraps this and raises TapinError with the API's own message on
anything other than a 200 `returns.status` (which does NOT necessarily mean
the HTTP status code was non-200 - Tapin can return HTTP 200 with a non-200
`returns.status` for validation errors).
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger("tapin")

BASE_URL = "https://api.tapin.ir/api/v2/public"
REQUEST_TIMEOUT = 20.0


class TapinError(Exception):
    """Raised for any Tapin failure - network, HTTP, or an API-level error
    inside a 200 response (bad shop_id, invalid city_code, etc.)."""

    def __init__(self, message: str, status: int | None = None):
        self.status = status
        super().__init__(message)


def _headers() -> dict:
    if not settings.TAPIN_TOKEN:
        raise TapinError("TAPIN_TOKEN تنظیم نشده")
    return {
        "Authorization": f"JWT {settings.TAPIN_TOKEN}",
        "Content-Type": "application/json",
    }


def _post(path: str, payload: dict) -> dict:
    logger.warning("TAPIN REQUEST %s payload=%s", path, payload)
    try:
        response = httpx.post(f"{BASE_URL}{path}", headers=_headers(), json=payload, timeout=REQUEST_TIMEOUT)
    except httpx.RequestError as exc:
        raise TapinError(f"خطا در اتصال به تاپین: {exc}") from exc

    try:
        data = response.json()
    except ValueError as exc:
        raise TapinError(f"پاسخ نامعتبر از تاپین (HTTP {response.status_code})") from exc

    logger.warning("TAPIN RESPONSE %s status=%s body=%s", path, response.status_code, data)

    returns = data.get("returns", {})
    if returns.get("status") != 200:
        raise TapinError(returns.get("message") or "خطای نامشخص از تاپین", status=returns.get("status"))

    return data.get("entries", {})


def get_provinces() -> list[dict]:
    """[{"code": 1, "title": "تهران", "cities": [...]}] for every province."""
    entries = _post("/state/tree/", {})
    return entries if isinstance(entries, list) else entries.get("list", [])


def get_cities(state_code: int, count: int = 200, page: int = 1) -> list[dict]:
    """[{"code": ..., "title": ...}] for cities in one province."""
    entries = _post("/city/list/", {"state_code": state_code, "count": count, "page": page})
    return entries.get("list", [])


def get_packing_boxes() -> list[dict]:
    """[{"pk": 14, "length": 30, "width": 20, "height": 20, "title": "30*20*20 cm"}]"""
    entries = _post("/order/post/packing-box/", {"shop_id": settings.TAPIN_SHOP_ID})
    return entries.get("list", [])


def _order_payload(
    *,
    address: str,
    city_code: int,
    province_code: int,
    first_name: str,
    last_name: str,
    mobile: str,
    postal_code: str | int,
    pay_type: int,
    order_type: int,
    packet_type: int,
    box_id: int,
    package_weight: int,
    products: list[dict],
    phone: str | None = None,
    email: str | None = None,
    description: str | None = None,
    employee_code: int = -1,
    pre_paid_price: int = 0,
    packaging_price: int = 0,
    has_insurance: bool = True,
    content_type: int = 1,
) -> dict:
    return {
        "shop_id": settings.TAPIN_SHOP_ID,
        "address": address,
        "city_code": city_code,
        "province_code": province_code,
        "description": description,
        "email": email,
        "employee_code": employee_code,
        "first_name": first_name,
        "last_name": last_name,
        "mobile": mobile,
        "phone": phone,
        "postal_code": int(str(postal_code).strip()) if str(postal_code).strip().isdigit() else postal_code,
        "pay_type": pay_type,
        "order_type": order_type,
        "pre_paid_price": pre_paid_price,
        "packaging_price": packaging_price,
        "package_weight": package_weight,
        "box_id": box_id,
        "packet_type": packet_type,
        "has_insurance": has_insurance,
        "content_type": content_type,
        "products": products,
    }


def check_price(**kwargs) -> dict:
    """
    Rate quote before placing a real order - same required fields as
    register_order (see _order_payload). Returns Tapin's full price
    breakdown dict (send_price, service_price, total_price, ...).
    """
    return _post("/order/post/check-price/", _order_payload(**kwargs))


def register_order(*, manual_id: str, register_type: int = 1, presenter_code: int | None = None, **kwargs) -> dict:
    """
    Actually creates the order with Tapin - unlike check_price this deducts
    from your Tapin wallet balance (once register_type takes it out of
    "تحت بررسی"/under-review) and issues a real waybill barcode.

    manual_id: YOUR unique order id (e.g. our Order.id) - Tapin uses this
    for idempotency: resending the same manual_id returns the existing
    order instead of creating a duplicate.

    register_type: 0 = تحت بررسی (still editable/deletable, no barcode yet,
    nothing charged), 1 = آماده به پرینت (barcode issued + wallet charged,
    no longer editable), 2 = آماده به ارسال (final, ready for pickup).
    Defaults to 1 since that's the point where you actually want a barcode.
    """
    payload = _order_payload(**kwargs)
    payload["register_type"] = register_type
    payload["manual_id"] = manual_id
    if presenter_code is not None:
        payload["presenter_code"] = presenter_code
    return _post("/order/post/register/", payload)