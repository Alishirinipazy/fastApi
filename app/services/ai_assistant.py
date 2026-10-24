import json
import re

import httpx
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Product, ProductColor, ProductSize, Cart, CartItem, Category, User
from app.services.storage import image_url

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
GAPGPT_URL = "https://api.gapgpt.app/v1/chat/completions"
IMAGE_SUBDIR = "products"
MAX_TOOL_ROUNDS = 5
REQUEST_TIMEOUT = 25.0


class AssistantUnavailable(Exception):
    """Raised when the underlying AI provider can't be reached / errors out
    after retrying - caught by run_assistant's callers to return a graceful
    Persian message instead of a raw 500."""


def _post_with_retry(url: str, headers: dict, payload: dict) -> dict:
    """
    POSTs to the AI provider with one retry on transient network failures
    (timeout / connection error) - a single hiccup shouldn't kill the whole
    turn. Does NOT retry on 4xx/5xx from the provider itself (rate limits,
    bad request, etc.) since retrying those immediately rarely helps and
    just adds latency; those are raised straight away.
    """
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = httpx.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response.json()
        except (httpx.TimeoutException, httpx.ConnectError, httpx.ReadError) as exc:
            last_error = exc
            continue  # one retry for network-level issues only
        except httpx.HTTPStatusError as exc:
            raise AssistantUnavailable(f"provider returned {exc.response.status_code}") from exc
    raise AssistantUnavailable("provider unreachable after retry") from last_error

SYSTEM_PROMPT = """\
اسم تو پازیه، دستیار خرید هوشمند فروشگاه اسلیپر پازه. وظیفه‌ات کمک به مشتری برای پیدا کردن و خرید محصول مناسبه، مخصوصاً راهنمایی سایز.

قوانین مهم:
- هیچ‌وقت قیمت، موجودی، رنگ یا سایز رو از خودت نساز - همیشه از ابزارهای search_products یا get_product_details استفاده کن و فقط بر اساس نتیجه‌شون جواب بده.
- اگه چیزی توی نتایج جستجو پیدا نشد، صادقانه بگو که همچین محصولی نداریم؛ محصول جایگزین پیشنهاد بده اگه مرتبط بود.
- اگه مشتری خواست چیزی رو به سبد خرید اضافه کنه ولی رنگ یا سایز رو نگفته، اول بپرس.
- راهنمای سایز: سایزهای دمپایی معمولاً با سایز کفش معمولی یکسانه؛ اگه بین دو سایز مردده، سایز بزرگ‌تر رو پیشنهاد بده.
- همیشه به فارسی و خودمونی ولی محترمانه جواب بده. کوتاه و مفید باش (حداکثر چند جمله)، از توضیحات اضافی خودداری کن.
- اگه ابزار add_to_cart جواب داد که کاربر لاگین نیست، بهش بگو باید اول وارد حساب کاربریش بشه.
- هیچ‌وقت وانمود نکن که سفارش رو نهایی کردی یا پرداختی انجام شده - فقط افزودن به سبد خرید در توان توئه.
- اگه سوال کاملاً خارج از حوزه فروشگاه بود، مودبانه برگرد به موضوع خرید.
- هدفت اینه مشتری خیلی راحت چیزی که می‌خواد رو پیدا کنه: اگه درخواستش کلیه (مثلاً «یه دمپایی می‌خوام»)، یک سوال کوتاه بپرس (برای چه کسی؟ بودجه؟ رنگ؟) و هم‌زمان چند گزینه نشون بده. وقتی محصولی پیدا کردی، حداکثر ۴ تا رو معرفی کن؛ کارت‌های محصول خودکار زیر پیامت نشون داده می‌شن، پس مشخصات رو تکرار نکن.
- اگه محصولی تخفیف داره (on_sale)، حتماً درصد تخفیفش رو بگو. اگه مشتری ارزون‌تر، پرفروش‌تر یا تخفیف‌دار خواست، از پارامتر sort و on_sale_only ابزار search_products استفاده کن.
- به مشتری بگو روی هر کارت محصول دکمه «پرو مجازی» هست و می‌تونه عکس خودش رو بذاره و ببینه محصول بهش میاد یا نه.
"""

TOOLS = [
    {
        "name": "search_products",
        "description": "جستجوی محصولات فروشگاه بر اساس متن آزاد، دسته‌بندی، رنگ، سایز، سقف قیمت و مرتب‌سازی. همیشه قبل از معرفی هر محصولی این رو صدا بزن.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "متن جستجو، مثلا 'دمپایی خونگی' یا خالی برای همه"},
                "category": {"type": "string", "description": "نام دسته‌بندی، مثلا 'بچگانه'، اختیاری"},
                "color": {"type": "string", "description": "نام رنگ مورد نظر، اختیاری"},
                "size": {"type": "string", "description": "سایز مورد نظر، اختیاری"},
                "max_price": {"type": "integer", "description": "سقف قیمت به تومان، اختیاری"},
                "sort": {
                    "type": "string",
                    "enum": ["newest", "cheapest", "expensive", "bestseller", "discount"],
                    "description": "مرتب‌سازی نتایج؛ پیش‌فرض newest",
                },
                "on_sale_only": {"type": "boolean", "description": "فقط محصولات تخفیف‌دار"},
            },
        },
    },
    {
        "name": "get_product_details",
        "description": "گرفتن جزئیات کامل یک محصول (همه رنگ‌ها، سایزها، قیمت و موجودی هر کدوم) با slug محصول که از search_products به‌دست میاد.",
        "input_schema": {
            "type": "object",
            "properties": {"slug": {"type": "string"}},
            "required": ["slug"],
        },
    },
    {
        "name": "add_to_cart",
        "description": "اضافه کردن یک محصول (با رنگ و سایز مشخص) به سبد خرید کاربر لاگین‌کرده.",
        "input_schema": {
            "type": "object",
            "properties": {
                "product_id": {"type": "integer"},
                "product_color_id": {"type": "integer"},
                "product_size_id": {"type": "integer"},
                "quantity": {"type": "integer", "default": 1},
            },
            "required": ["product_id", "product_color_id", "product_size_id"],
        },
    },
]


def _product_card(serialized: dict) -> dict:
    """The slim shape the chat widget renders (and the model reads) for a product,
    built from the same serializer the storefront uses so price / discount /
    stock always match what the product page shows."""
    return {
        "id": serialized["id"],
        "slug": serialized["slug"],
        "name": serialized["name"],
        "category": serialized["category"],
        "image": serialized["primary_image"],
        "min_price": serialized["regular_price"],
        "regular_price": serialized["regular_price"],
        "final_price": serialized["final_price"],
        "on_sale": serialized["on_sale"],
        "discount_percent": serialized["discount_percent"],
        "in_stock": serialized["total_quantity"] > 0,
        "colors": [
            {"name": c["name"], "color_code": c["color_code"]} for c in serialized["colors"]
        ][:6],
    }


def _run_search_products(db: Session, args: dict) -> dict:
    # Imported here: products.py is an API module, and importing it at module
    # load would couple the two files' import order for no benefit.
    from app.api.v1 import products as catalog

    def candidates(query_text: str | None, require_all: bool, category_ids: list[int] | None):
        q = catalog._with_variants(catalog._active_products(db)).filter(Product.status == 1)
        if category_ids:
            q = q.filter(Product.category_id.in_(category_ids))
        tokens = [t for t in re.split(r"\s+", (query_text or "").strip()) if t]
        if tokens:
            conds = [
                or_(Product.name.ilike(f"%{t}%"), Product.description.ilike(f"%{t}%"))
                for t in tokens
            ]
            q = q.filter(and_(*conds) if require_all else or_(*conds))
        return q.order_by(Product.created_at.desc()).limit(80).all()

    category_ids: list[int] | None = None
    if args.get("category"):
        cats = db.query(Category).filter(Category.name.ilike(f"%{args['category'].strip()}%")).all()
        if cats:
            category_ids = []
            for c in cats:
                category_ids += catalog._category_and_descendant_ids(db, c.id)

    def passes_filters(p: Product) -> bool:
        colors = catalog._active_colors(p)
        if args.get("color"):
            wanted = args["color"].strip()
            if not any(wanted in c.name for c in colors):
                return False
        if args.get("size"):
            wanted = str(args["size"]).strip()
            if not any(
                s.size == wanted and s.deleted_at is None and s.quantity > 0
                for c in colors
                for s in c.sizes
            ):
                return False
        if args.get("max_price"):
            if catalog._serialize_product(p)["final_price"] > int(args["max_price"]):
                return False
        if args.get("on_sale_only") and not catalog._is_on_sale(p):
            return False
        return True

    query_text = args.get("query")
    products = [p for p in candidates(query_text, True, category_ids) if passes_filters(p)]
    # Several words that don't ALL appear in one product ("دمپایی خونگی نرم")
    # shouldn't return nothing - fall back to any-word matching.
    if not products and query_text and len(query_text.split()) > 1:
        products = [p for p in candidates(query_text, False, category_ids) if passes_filters(p)]

    fallback_used = False
    has_filters = any(args.get(k) for k in ("color", "size", "max_price", "on_sale_only"))
    if not products and has_filters:
        # Nothing matches every filter: show the closest by text/category only,
        # so the customer is never left with an empty answer.
        products = candidates(query_text, True, category_ids)
        fallback_used = bool(products)

    cards = [(_p, _product_card(catalog._serialize_product(_p))) for _p in products]

    sort = args.get("sort") or "newest"
    if sort == "cheapest":
        cards.sort(key=lambda pc: pc[1]["final_price"])
    elif sort == "expensive":
        cards.sort(key=lambda pc: pc[1]["final_price"], reverse=True)
    elif sort == "discount":
        cards.sort(key=lambda pc: pc[1]["discount_percent"], reverse=True)
    elif sort == "bestseller":
        rank = {pid: i for i, pid in enumerate(catalog._bestseller_ids(db, 200))}
        cards.sort(key=lambda pc: rank.get(pc[1]["id"], len(rank)))
    # in-stock products first, otherwise keep the chosen order (sort is stable)
    cards.sort(key=lambda pc: not pc[1]["in_stock"])

    return {
        "results": [card for _, card in cards[:8]],
        "note": "دقیقاً با این فیلترها چیزی نبود؛ این‌ها نزدیک‌ترین موارد بر اساس متن جستجو هستن." if fallback_used else None,
    }


def _run_get_product_details(db: Session, args: dict) -> dict:
    from app.api.v1 import products as catalog

    product = (
        catalog._with_variants(catalog._active_products(db))
        .filter(Product.slug == args.get("slug", ""))
        .first()
    )
    if product is None:
        return {"error": "محصول با این slug پیدا نشد"}

    serialized = catalog._serialize_product(product)
    return {
        **_product_card(serialized),
        "description": serialized["description"],
        "colors": [
            {
                "id": c["id"],
                "name": c["name"],
                "color_code": c["color_code"],
                "sizes": [
                    {"id": s["id"], "size": s["size"], "price": s["price"], "quantity": s["quantity"]}
                    for s in c["sizes"]
                ],
            }
            for c in serialized["colors"]
        ],
    }


def _run_add_to_cart(db: Session, current_user: User | None, args: dict) -> dict:
    if current_user is None:
        return {"error": "login_required", "message": "برای افزودن به سبد خرید باید وارد حساب کاربری بشید"}

    size = (
        db.query(ProductSize)
        .filter(
            ProductSize.id == args.get("product_size_id"),
            ProductSize.product_color_id == args.get("product_color_id"),
        )
        .first()
    )
    if size is None:
        return {"error": "رنگ یا سایز انتخاب‌شده معتبر نیست"}
    if size.quantity < 1:
        return {"error": "این سایز موجود نیست"}

    quantity = max(1, int(args.get("quantity") or 1))

    cart = db.query(Cart).filter(Cart.user_id == current_user.id).first()
    if cart is None:
        cart = Cart(user_id=current_user.id)
        db.add(cart)
        db.flush()

    item = (
        db.query(CartItem)
        .filter(
            CartItem.cart_id == cart.id,
            CartItem.product_id == args.get("product_id"),
            CartItem.product_color_id == args.get("product_color_id"),
            CartItem.product_size_id == args.get("product_size_id"),
        )
        .first()
    )
    if item:
        item.quantity += quantity
    else:
        item = CartItem(
            cart_id=cart.id,
            product_id=args.get("product_id"),
            product_color_id=args.get("product_color_id"),
            product_size_id=args.get("product_size_id"),
            quantity=quantity,
        )
        db.add(item)

    db.commit()
    return {"success": True, "message": "به سبد خرید اضافه شد"}


def _execute_tool(db: Session, current_user: User | None, name: str, args: dict) -> dict:
    if name == "search_products":
        return _run_search_products(db, args)
    if name == "get_product_details":
        return _run_get_product_details(db, args)
    if name == "add_to_cart":
        return _run_add_to_cart(db, current_user, args)
    return {"error": f"unknown tool {name}"}


def _track_tool_result(name: str, result: dict, products_by_id: dict[int, dict]) -> bool:
    """
    Records any product data a tool call turned up into products_by_id (in
    place, for the frontend's product cards) and reports whether this call
    was a successful add_to_cart (so the caller knows to refresh the cart).
    Shared between both providers since the tool results are identical
    regardless of which model produced the call.
    """
    if name == "search_products":
        for p in result.get("results", []):
            products_by_id[p["id"]] = p
    if name == "get_product_details" and "id" in result:
        card = {k: result[k] for k in (
            "id", "slug", "name", "category", "image", "min_price", "regular_price",
            "final_price", "on_sale", "discount_percent", "in_stock",
        ) if k in result}
        card["colors"] = [
            {"name": c["name"], "color_code": c["color_code"]} for c in result.get("colors", [])
        ][:6]
        products_by_id[result["id"]] = card
    return name == "add_to_cart" and bool(result.get("success"))


def _openai_tools() -> list[dict]:
    """Same TOOLS list, reshaped into OpenAI's function-calling schema for GapGPT."""
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOLS
    ]


def run_assistant(
    db: Session, current_user: User | None, messages: list[dict], product_slug: str | None = None
) -> dict:
    """
    Runs the tool-use agent loop and returns
    {"reply": str, "cart_updated": bool, "products": [...]}. `messages` is
    the full conversation so far as [{"role": "user"|"assistant", "content": str}].
    `product_slug`, when set, tells the assistant which product page the
    customer is currently viewing (it still has to call get_product_details
    itself - this is just context, never a substitute for the real lookup).
    `products` collects whatever search_products/get_product_details turned up
    during this turn, de-duplicated by id, so the frontend can render real
    product cards instead of parsing them out of the reply text.

    Dispatches to either the direct Claude API or GapGPT (an OpenAI-compatible
    proxy) based on settings.AI_PROVIDER - same tools, same DB-grounded
    results either way, just a different wire format underneath.
    """
    system_prompt = SYSTEM_PROMPT
    if product_slug:
        system_prompt += f"\n\nمشتری الان توی صفحه محصول با slug \"{product_slug}\" هست - اگه سوالش درباره همین محصوله، با get_product_details جزئیاتش رو بگیر."

    if settings.AI_PROVIDER == "gapgpt":
        runner = _run_gapgpt
    else:
        runner = _run_anthropic

    try:
        result = runner(db, current_user, messages, system_prompt)
    except AssistantUnavailable:
        result = {
            "reply": "دستیار هوشمند الان در دسترس نیست، چند لحظه دیگه دوباره امتحان کن 🙏",
            "cart_updated": False,
            "products": [],
        }
    result["quick_replies"] = _quick_replies(result)
    return result


def _quick_replies(result: dict) -> list[str]:
    """Follow-up chips shown under the assistant's reply, so the customer can
    narrow the choice with one tap instead of typing."""
    products = result.get("products") or []
    if not products:
        return []
    chips = ["ارزون‌ترین‌هاشون رو نشون بده", "پرفروش‌ترین‌ها کدومان؟"]
    if any(p.get("on_sale") for p in products):
        chips.insert(0, "فقط تخفیف‌دارها")
    else:
        chips.insert(0, "تخفیف‌دارها رو نشون بده")
    chips.append("رنگ‌های دیگه دارید؟")
    return chips[:4]


def _run_anthropic(db: Session, current_user: User | None, messages: list[dict], system_prompt: str) -> dict:
    if not settings.ANTHROPIC_API_KEY:
        return {
            "reply": "دستیار هوشمند فعلاً فعال نیست (کلید API تنظیم نشده).",
            "cart_updated": False,
            "products": [],
        }

    conversation = [{"role": m["role"], "content": m["content"]} for m in messages]
    cart_updated = False
    products_by_id: dict[int, dict] = {}

    headers = {
        "x-api-key": settings.ANTHROPIC_API_KEY,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    for _ in range(MAX_TOOL_ROUNDS):
        data = _post_with_retry(
            ANTHROPIC_URL,
            headers,
            {
                "model": settings.AI_ASSISTANT_MODEL,
                "max_tokens": settings.AI_ASSISTANT_MAX_TOKENS,
                "system": system_prompt,
                "messages": conversation,
                "tools": TOOLS,
            },
        )

        content = data.get("content", [])
        conversation.append({"role": "assistant", "content": content})

        if data.get("stop_reason") != "tool_use":
            text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
            return {
                "reply": text or "متوجه نشدم، می‌شه دوباره بپرسید؟",
                "cart_updated": cart_updated,
                "products": list(products_by_id.values()),
            }

        tool_results = []
        for block in content:
            if block.get("type") != "tool_use":
                continue
            result = _execute_tool(db, current_user, block["name"], block.get("input", {}))
            if _track_tool_result(block["name"], result, products_by_id):
                cart_updated = True

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

        conversation.append({"role": "user", "content": tool_results})

    return {
        "reply": "متاسفانه نتونستم درخواستتون رو کامل انجام بدم، لطفاً دوباره امتحان کنید.",
        "cart_updated": cart_updated,
        "products": list(products_by_id.values()),
    }


def _run_gapgpt(db: Session, current_user: User | None, messages: list[dict], system_prompt: str) -> dict:
    """
    Same agent loop as _run_anthropic, but against GapGPT's OpenAI-compatible
    /v1/chat/completions endpoint: system prompt is just the first message,
    tool calls arrive as message.tool_calls, and tool results go back as
    separate {"role": "tool", "tool_call_id": ...} messages instead of
    Anthropic's tool_result content blocks.
    """
    if not settings.GAPGPT_API_KEY:
        return {
            "reply": "دستیار هوشمند فعلاً فعال نیست (کلید GapGPT تنظیم نشده).",
            "cart_updated": False,
            "products": [],
        }

    conversation = [{"role": "system", "content": system_prompt}]
    conversation += [{"role": m["role"], "content": m["content"]} for m in messages]

    cart_updated = False
    products_by_id: dict[int, dict] = {}

    headers = {
        "Authorization": f"Bearer {settings.GAPGPT_API_KEY}",
        "Content-Type": "application/json",
    }

    for _ in range(MAX_TOOL_ROUNDS):
        data = _post_with_retry(
            GAPGPT_URL,
            headers,
            {
                "model": settings.GAPGPT_MODEL,
                "messages": conversation,
                "tools": _openai_tools(),
                "max_tokens": settings.AI_ASSISTANT_MAX_TOKENS,
            },
        )

        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise AssistantUnavailable("unexpected response shape from gapgpt") from exc
        conversation.append(message)

        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return {
                "reply": message.get("content") or "متوجه نشدم، می‌شه دوباره بپرسید؟",
                "cart_updated": cart_updated,
                "products": list(products_by_id.values()),
            }

        for call in tool_calls:
            fn = call["function"]
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except json.JSONDecodeError:
                args = {}

            result = _execute_tool(db, current_user, fn["name"], args)
            if _track_tool_result(fn["name"], result, products_by_id):
                cart_updated = True

            conversation.append({
                "role": "tool",
                "tool_call_id": call["id"],
                "content": json.dumps(result, ensure_ascii=False),
            })

    return {
        "reply": "متاسفانه نتونستم درخواستتون رو کامل انجام بدم، لطفاً دوباره امتحان کنید.",
        "cart_updated": cart_updated,
        "products": list(products_by_id.values()),
    }