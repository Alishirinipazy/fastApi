# FastAPI rewrite of the Laravel shop API

## Progress so far

- **Phase 1**: all database models + auth (customer OTP login, admin
  email/password login).
- **Phase 2** (this round): categories (with parent/child + single image
  upload), products (with images/colors/sizes, listing/filter/search/
  pagination, admin CRUD), and cart (new module - see note below).

Still not built: orders/checkout, coupons, shipping methods, the payment
gateway, contact-us, sliders, stories. Say which one's next.

## Project layout

```
app/
  core/
    config.py      # settings (env vars) - replaces Laravel's .env + config/*.php
    security.py     # password hashing, OTP generation, bearer-token hashing
  db/
    session.py      # SQLAlchemy engine/session/Base - replaces DB facade
  models/            # SQLAlchemy models - one file per domain, mirrors app/Models + migrations
  schemas/           # Pydantic request/response schemas - replaces FormRequest validation
  api/
    deps.py          # get_current_user / get_current_admin - replaces Sanctum middleware
    v1/auth.py        # AuthController rewritten as two routers (user + admin)
  services/
    sms.py             # Ghasedak OTP send - replaces SmsChannel + OTPSms notification
    slug.py            # Persian-aware slugify - replaces amirvahedix/laravel-persian-slugify
    storage.py         # local file upload/serve - replaces storeAs(..., 'public') + the storage symlink
  utils/
    response.py       # success_response/error_response - replaces ApiResponser trait
    jalali.py          # Jalali date formatting - replaces the verta() helper
    pagination.py      # replaces Laravel's ->paginate() links/meta envelope
  api/v1/
    auth.py
    categories.py      # CategoryController rewritten (list/CRUD, image upload, parent/child)
    products.py        # ProductController rewritten (listing, filter, search, CRUD, colors/sizes)
    cart.py            # NEW - see note below, no Laravel equivalent
  main.py              # FastAPI app + router wiring - replaces routes/api.php + bootstrap
alembic/               # migrations, generated from the SQLAlchemy models
```

## How the pieces map to the Laravel app

| Laravel                                   | FastAPI equivalent here                              |
|--------------------------------------------|-------------------------------------------------------|
| Eloquent models + migrations               | `app/models/*.py` (SQLAlchemy 2.0 `Mapped` style)      |
| `Validator::make(...)`/FormRequest         | Pydantic schemas in `app/schemas/`                     |
| `ApiResponser` trait                       | `app/utils/response.py`                                |
| Sanctum `personal_access_tokens` + abilities| `AccessToken` model + `abilities` JSON column + `app/api/deps.py` |
| `auth:sanctum` + `ability:admin` middleware| `Depends(get_current_user)` / `Depends(get_current_admin)` |
| `SmsChannel` / `OTPSms` notification       | `app/services/sms.py`                                  |
| `verta($date)->format(...)`                | `app/utils/jalali.py`                                  |
| `routes/api.php`                           | `app/main.py` (`include_router`)                       |

## Auth flow (unchanged behavior, new transport)

1. `POST /api/v1/auth/login` `{cellphone}` → creates/updates the user, generates
   a 6-digit OTP, sends it via Ghasedak, returns a `login_token`.
2. `POST /api/v1/auth/check-otp` `{otp, login_token}` → on match, issues a
   bearer token (ability `["user"]`) and the serialized user.
3. `POST /api/v1/auth/resend-otp` `{login_token}` → new OTP + new `login_token`.
4. `GET /api/v1/auth/me`, `POST /api/v1/auth/logout` → require
   `Authorization: Bearer <token>`.
5. Admin: `POST /api/v1/admin-panel/auth/login` `{email, password}` (only if
   `is_admin`), `GET /api/v1/admin-panel/auth/me`, `POST
   /api/v1/admin-panel/auth/logout`.

**One deliberate change:** Sanctum's `personal_access_tokens` table is
reimplemented here as `access_tokens`, storing an HMAC-SHA256 hash of the
token instead of the plaintext-hashed value Sanctum uses — same idea (never
store the raw token), different hash, so a fresh migration is needed for
this table; it can't reuse Sanctum's existing rows.

**Also worth knowing:** the Ghasedak call in `app/services/sms.py` is a
best-effort translation of the PHP SDK's `->Verify(...)` call using `httpx`
directly, since there's no official Ghasedak Python SDK. Verify the
endpoint/payload against Ghasedak's current REST docs before depending on it.

## Categories

`Category.parent_id` drives the parent/child tree; `Category.image` is a
single uploaded file, saved under `storage/images/categories/` and served at
`/storage/images/categories/<file>`.

**One deliberate change:** Laravel stored `parent_id` as a plain unsigned
bigint defaulting to `0` with no FK constraint (`0` = no parent). Here it's a
real nullable self-referencing foreign key (`NULL` = top-level) instead, so
the DB enforces that a `parent_id` actually points at an existing category,
and deleting a parent sets its children's `parent_id` to `NULL` automatically
instead of leaving a stale `0` (or a stale non-existent id) behind.

- `GET /api/v1/categories` — public, flat list (matches the Laravel route)
- `GET/POST /api/v1/admin-panel/categories`, `GET/POST
  /api/v1/admin-panel/categories/{id}` (create/update take
  `multipart/form-data`: `name`, `description`, `parent_id`, `image`),
  `DELETE /api/v1/admin-panel/categories/{id}`
- `GET /api/v1/admin-panel/categories/{id}/children` — direct children
- `GET /api/v1/admin-panel/categories/{id}/parent` — parent category
- `GET /api/v1/admin-panel/categories/{id}/products`
- `GET /api/v1/admin-panel/categories-list` — flat list for admin dropdowns

`GET /api/v1/filter-options` was declared in `routes/api.php` pointing at
`CategoryController::filterOptions`, but that method never actually existed
in the source project - built fresh here instead, scoped to what
`/menu`'s filters need: category list with product counts, overall price
range, and the distinct colors/sizes that exist across products. `/menu`
itself now also accepts `price_min`, `price_max`, `color`, `size` query
params, and `sort_by=bestseller` is implemented for real (ranks by units
sold across paid orders) now that the orders module exists.

## Products

Mirrors `ProductController` + `ProductColorController` +
`ProductSizeController` combined into one router. `total_quantity` and
`min_price` are computed from `colors.sizes` exactly like the Laravel
model's accessors.

- `GET /api/v1/products` — paginated (6/page), `GET
  /api/v1/products/products-tabs`, `GET /api/v1/random-products?count=N`,
  `GET /api/v1/menu?category=&sort_by=&search=&page=`, `GET
  /api/v1/products/{slug}`
- `POST /api/v1/admin-panel/products` (multipart: `name`, `category_id`,
  `description`, `status`, `primary_image` file, `images` file list,
  optional `colors_json` + `colors_images`), `POST
  /api/v1/admin-panel/products/{id}` (update), `DELETE .../{id}`

**One necessary change:** nested color/size file uploads. Laravel/PHP can
receive `colors[0][image]` as a file inside a multipart body naturally;
FastAPI's multipart parsing doesn't have an equivalent for deeply nested
file arrays. So creating a product with colors sends two parallel form
fields instead: `colors_json` (a JSON string with `name`/`color_code`/
`sizes` per color) and `colors_images` (a file list, same order as
`colors_json`). Same data, different wire format.

`sort_by=bestseller` isn't implemented yet — it ranks products by paid
order counts, which needs the orders module built first.

## Cart

**There was no cart table or `CartController` in the Laravel app** — the
frontend (`stores/cart.js`) kept the cart client-side and only called the
API at checkout to create an `Order` directly. This module is new,
added so the cart persists server-side per logged-in user. If a
stateless/client-only cart is what's actually wanted, say so and this can
be dropped in favor of a simple "validate + price a cart payload" endpoint
that matches the original architecture more closely instead.

- `GET /api/v1/cart` — current user's cart with computed subtotals
- `POST /api/v1/cart/items` `{product_id, product_color_id?,
  product_size_id?, quantity}` — adds or merges into an existing line
- `PATCH /api/v1/cart/items/{id}` `{quantity}`
- `DELETE /api/v1/cart/items/{id}`, `DELETE /api/v1/cart` (clear)

All cart routes require `Authorization: Bearer <user token>`.

## Running it

```bash
pip install -r requirements.txt --break-system-packages
cp .env.example .env   # fill in DATABASE_URL, TOKEN_SECRET, GHASEDAK_API_KEY

# creates every table (users, categories, products, orders, carts, ...)
alembic upgrade head

uvicorn app.main:app --reload
```

The migration in `alembic/versions/a1b2c3d4e5f6_initial_schema.py` was
hand-written from the models (no live DB here to run `--autogenerate`
against) - it's a straight table-by-table translation, but run `alembic
check` or diff it against a fresh autogenerate once you have a real DB
connection, just to be safe.

Swagger UI at `http://localhost:8000/docs` once it's running.

## Deploying with Docker (e.g. Runflare)

A `Dockerfile` + `docker-entrypoint.sh` are included. The entrypoint waits
for the database to accept connections (useful when it's a separately
provisioned service that might still be starting up), runs
`alembic upgrade head`, then starts uvicorn on `$PORT` (defaults to 8000) -
so a fresh deploy migrates itself, no manual step needed after the first
`docker run`/platform deploy.

```bash
docker build -t slipper-api .
docker run -p 8000:8000 --env-file .env slipper-api
```

Runflare specifically: it's a Docker/Kubernetes-based PaaS where each
project holds separate "services" (this backend, the storefront, the admin
panel) plus a "database" service you provision alongside them - deploy via
their CLI (`pip install runflare`, then `runflare deploy` from this
directory) or by pointing a service at this Dockerfile, whichever their
dashboard offers for your project. Their docs weren't reachable to confirm
the exact env-var name Runflare injects for the container port - if `$PORT`
isn't it, override the port Runflare expects to via its dashboard rather
than editing the Dockerfile, everything here already reads `$PORT`.

**Set these in Runflare's service environment variables panel** (or
`--env-file .env` locally) - none of this is baked into the image:

- `DATABASE_URL` - point at the database service Runflare provisions
  (host/port/credentials come from its dashboard, not this repo)
- `TOKEN_SECRET`, `GHASEDAK_API_KEY`, `ANTHROPIC_API_KEY` or
  `GAPGPT_API_KEY`, `ZIBAL_MERCHANT`, `PAYMENT_CALLBACK_URL` - see
  `.env.example` for the full list
- `PAYMENT_CALLBACK_URL` needs to point at the **deployed storefront's**
  `/payment/verify` page, not `localhost:3000`, once both are live

`storage/` (uploaded images) is a plain local folder inside the container -
it does **not** persist across redeploys/restarts on most container
platforms unless a persistent volume is mounted at that path. Check
Runflare's volume/disk options for the service if uploaded images need to
survive a redeploy.

## AI shopping assistant (new - not from the Laravel app)

`POST /api/v1/chat` — a tool-using Claude API agent that can search the real
product catalog, pull full product details, and add items to the logged-in
customer's cart, grounded entirely in actual DB data (it's instructed to
never invent prices, stock, or colors).

- **Stateless**: the client sends the whole conversation each call
  (`{"messages": [{"role": "user"|"assistant", "content": "..."}]}`), same
  pattern as any direct LLM API integration - no server-side chat history.
- **Works for guests and logged-in users**: `Authorization: Bearer <token>`
  is optional. Without it, search/browse works fine but `add_to_cart` tells
  the customer to log in first instead of silently failing.
- **Tools**: `search_products`, `get_product_details`, `add_to_cart` - see
  `app/services/ai_assistant.py`. The response also includes a de-duplicated
  `products` array (whatever the tools turned up that turn) so the frontend
  can render real product cards instead of parsing them out of prose.
- **Two providers, same tools/behavior** - set `AI_PROVIDER` in `.env`:
  - `anthropic` (default): calls the Claude API directly. Set
    `ANTHROPIC_API_KEY` (get one at https://console.anthropic.com).
    `AI_ASSISTANT_MODEL` defaults to `claude-sonnet-5`; drop to a Haiku
    model if cost matters more than handling ambiguous requests well.
  - `gapgpt`: routes through https://api.gapgpt.app instead (an
    OpenAI-compatible proxy). Set `GAPGPT_API_KEY` and optionally
    `GAPGPT_MODEL` (defaults to `gpt-4o-mini`). Same tools, same DB-grounded
    answers - `_run_gapgpt()` just speaks OpenAI's function-calling format
    (`tool_calls` / `role: "tool"` messages) instead of Anthropic's
    (`tool_use` / `tool_result` content blocks) under the hood.

**Wired into the real customer-facing storefront** (`storefront/`, the
Nuxt app connected separately) as `components/ChatBot.vue` - the "پازی"
persona, product cards, and cart-refresh-on-add all live there now. The
standalone `widget/ai-assistant-demo.html` in this repo is only useful if
a different or additional frontend ever needs the same feature - a
plain HTML/CSS/JS drop-in with no build step.

## Coupons, shipping, orders, payment, profile (this round's additions)

- **Coupons** (`/coupons` admin CRUD, `/check-coupon` for the logged-in
  customer) — straight port of `CouponController`.
- **Shipping methods** (`/shipping-methods` public list of active methods,
  `/admin-panel/shipping-methods` full CRUD + `/toggle`) — port of
  `ShippingMethodController`. One note: the Laravel validator declared
  `delivery_days` as a string, but the migration/column is an integer —
  this rewrite validates it as an integer (matching the actual column),
  since that looks like a bug in the original validator rather than intent.
- **Orders** (`/admin-panel/orders` list/detail, `PATCH .../status` with the
  same allowed-transition state machine as `Order::allowedTransitions()`) —
  port of `OrderController`'s admin-facing methods.
- **Payment** (`POST /payment/send`, `POST /payment/verify`) — originally
  ported from `PaymentController` using pay.ir, **since switched to Zibal**
  (`app/services/zibal.py`). `/payment/send` calls Zibal's `/v1/request`,
  creates the order in `order_status=0` (pending), and returns the gateway
  URL to redirect to. Zibal redirects back to `PAYMENT_CALLBACK_URL` with
  `?trackId=&success=&status=` in the query string - the frontend page at
  that URL reads those and posts them to `/payment/verify`, which calls
  Zibal's `/v1/verify`, and on success marks the order paid, decrements
  stock, and clears the cart. Verify is idempotent (checked via
  `transaction.status`, not just Zibal's own "already verified" result code)
  since the callback page can legitimately get hit more than once. Zibal's
  integer `trackId` is stored as text in the same `token` column pay.ir's
  string token used to live in, so no migration was needed for the switch.
  **One deliberate change kept from the pay.ir version:** the Laravel app
  took the cart as a raw array in the request body; this still reads from
  the user's server-side cart (`app/models/cart.py`) instead, since resending
  the whole cart on every checkout call is one more place client and server
  can disagree.
- **Profile** (`/profile/info`, `/profile/addresses/*`, `/profile/orders`,
  `/profile/transactions`, plus `/user/addresses`) — port of
  `ProfileController` or the relevant slice of `UserController`.
- **Transactions** (`/admin-panel/transactions`, `/admin-panel/transactions/chart`)
  — port of `TransactionController`, including the 12-Jalali-month
  zero-filled chart bucketing.

## Sliders and stories

Both follow the same shape: public list (`/sliders`, `/stories` - active
items only, stories additionally filtered by `expires_at`), admin CRUD,
`PATCH .../{id}/toggle`, and `POST .../reorder` `{ids: [...]}` which
rewrites the `sort` column in the given order. Straight ports of
`SliderController` / `StoryController`. Images are saved to their own
`storage/images/sliders/` and `storage/images/stories/` subdirectories
(the Laravel app reused `images/products` for both — split out here since
there's no reason to share a folder with actual product images).

## Admin users and contact-us

- **Users** (`/admin-panel/users` full CRUD, paginated 5/page) — port of
  `UserController`, plus `is_admin` support added on request: create/update
  now accept an `is_admin` boolean (Laravel's version had no way to set
  this at all). Guarded so an admin can't demote or delete their own
  account through this endpoint.
- **Contact-us** (`POST /contact-us`, public) — port of `ContactUsController`.
  Laravel only had `store()`; an admin inbox
  (`GET /admin-panel/contact-us` list, `GET .../{id}`, `DELETE .../{id}`)
  was added on request so submissions are actually readable somewhere -
  new functionality, not a port.

## Iran provinces/cities seeder

`provinces` and `cities` start out empty after `alembic upgrade head` - the
profile address form needs them populated. Two equivalent ways to do it,
same 31 provinces / 353 cities either way (major cities per province, not
literally every town/village - enough for a real address form):

```bash
# Option A: Python, idempotent (safe to re-run, skips what's already there)
python -m scripts.seed_iran_locations

# Option B: plain SQL (only run once - not idempotent, will duplicate on a second run)
mysql -u root -p your_db_name < scripts/seed_iran_locations.sql
```

## Not done yet (next slices)

Everything from `routes/api.php` has a home now, plus the two additions
above. Nothing outstanding from the source project at this point - further
work would be new functionality rather than porting.
