import json

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Product, ProductColor, ProductSize, Cart, CartItem, User
from app.services.storage import image_url

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
GAPGPT_URL = "https://api.gapgpt.app/v1/chat/completions"
IMAGE_SUBDIR = "products"
MAX_TOOL_ROUNDS = 5

SYSTEM_PROMPT = """\
اسم تو پازیه، دستیار خرید هوشمند فروشگاه اسلیپر استوره. وظیفه‌ات کمک به مشتری برای پیدا کردن و خرید محصول مناسبه، مخصوصاً راهنمایی سایز.

قوانین مهم:
- هیچ‌وقت قیمت، موجودی، رنگ یا سایز رو از خودت نساز - همیشه از ابزارهای search_products یا get_product_details استفاده کن و فقط بر اساس نتیجه‌شون جواب بده.
- اگه چیزی توی نتایج جستجو پیدا نشد، صادقانه بگو که همچین محصولی نداریم؛ محصول جایگزین پیشنهاد بده اگه مرتبط بود.
- اگه مشتری خواست چیزی رو به سبد خرید اضافه کنه ولی رنگ یا سایز رو نگفته، اول بپرس.
- راهنمای سایز: سایزهای دمپایی معمولاً با سایز کفش معمولی یکسانه؛ اگه بین دو سایز مردده، سایز بزرگ‌تر رو پیشنهاد بده.
- همیشه به فارسی و خودمونی ولی محترمانه جواب بده. کوتاه و مفید باش (حداکثر چند جمله)، از توضیحات اضافی خودداری کن.
- اگه ابزار add_to_cart جواب داد که کاربر لاگین نیست، بهش بگو باید اول وارد حساب کاربریش بشه.
- هیچ‌وقت وانمود نکن که سفارش رو نهایی کردی یا پرداختی انجام شده - فقط افزودن به سبد خرید در توان توئه.
- اگه سوال کاملاً خارج از حوزه فروشگاه بود، مودبانه برگرد به موضوع خرید.
"""

TOOLS = [
    {
        "name": "search_products",
        "description": "جستجوی محصولات فروشگاه بر اساس متن آزاد، دسته‌بندی، رنگ، سایز یا سقف قیمت. همیشه قبل از معرفی هر محصولی این رو صدا بزن.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "متن جستجو، مثلا 'دمپایی خونگی' یا خالی برای همه"},
                "color": {"type": "string", "description": "نام رنگ مورد نظر، اختیاری"},
                "size": {"type": "string", "description": "سایز مورد نظر، اختیاری"},
                "max_price": {"type": "integer", "description": "سقف قیمت به تومان، اختیاری"},
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


def _run_search_products(db: Session, args: dict) -> dict:
    query = db.query(Product).filter(Product.status == 1)

    if args.get("query"):
        query = query.filter(Product.name.ilike(f"%{args['query'].strip()}%"))
    if args.get("color"):
        query = query.join(Product.colors).filter(ProductColor.name.ilike(f"%{args['color']}%")).distinct()
    if args.get("size"):
        query = (
            query.join(Product.colors)
            .join(ProductColor.sizes)
            .filter(ProductSize.size == args["size"])
            .distinct()
        )
    if args.get("max_price"):
        query = query.join(Product.colors).join(ProductColor.sizes).filter(
            ProductSize.price <= args["max_price"]
        ).distinct()

    products = query.limit(8).all()
    return {
        "results": [
            {
                "id": p.id,
                "slug": p.slug,
                "name": p.name,
                "min_price": p.min_price,
                "in_stock": p.total_quantity > 0,
                "image": image_url(p.primary_image, IMAGE_SUBDIR),
            }
            for p in products
        ]
    }


def _run_get_product_details(db: Session, args: dict) -> dict:
    product = db.query(Product).filter(Product.slug == args.get("slug", "")).first()
    if product is None:
        return {"error": "محصول با این slug پیدا نشد"}

    return {
        "id": product.id,
        "slug": product.slug,
        "name": product.name,
        "description": product.description,
        "image": image_url(product.primary_image, IMAGE_SUBDIR),
        "colors": [
            {
                "id": c.id,
                "name": c.name,
                "color_code": c.color_code,
                "sizes": [
                    {"id": s.id, "size": s.size, "price": s.price, "quantity": s.quantity}
                    for s in c.sizes
                ],
            }
            for c in product.colors
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
        products_by_id[result["id"]] = {
            "id": result["id"],
            "slug": result["slug"],
            "name": result["name"],
            "image": result["image"],
            "min_price": min((s["price"] for c in result["colors"] for s in c["sizes"]), default=0),
            "in_stock": any(s["quantity"] > 0 for c in result["colors"] for s in c["sizes"]),
        }
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
        return _run_gapgpt(db, current_user, messages, system_prompt)
    return _run_anthropic(db, current_user, messages, system_prompt)


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
        response = httpx.post(
            ANTHROPIC_URL,
            headers=headers,
            json={
                "model": settings.AI_ASSISTANT_MODEL,
                "max_tokens": settings.AI_ASSISTANT_MAX_TOKENS,
                "system": system_prompt,
                "messages": conversation,
                "tools": TOOLS,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

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
        response = httpx.post(
            GAPGPT_URL,
            headers=headers,
            json={
                "model": settings.GAPGPT_MODEL,
                "messages": conversation,
                "tools": _openai_tools(),
                "max_tokens": settings.AI_ASSISTANT_MAX_TOKENS,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()

        message = data["choices"][0]["message"]
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
