from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1.auth import router as auth_router, admin_router as auth_admin_router
from app.api.v1.categories import router as categories_router, admin_router as categories_admin_router
from app.api.v1.products import router as products_router, admin_router as products_admin_router
from app.api.v1.cart import router as cart_router
from app.api.v1.coupons import router as coupons_router, admin_router as coupons_admin_router
from app.api.v1.shipping import router as shipping_router, admin_router as shipping_admin_router
from app.api.v1.orders import admin_router as orders_admin_router
from app.api.v1.transactions import admin_router as transactions_admin_router
from app.api.v1.payment import router as payment_router
from app.api.v1.profile import router as profile_router, user_router as profile_user_router
from app.api.v1.sliders import router as sliders_router, admin_router as sliders_admin_router
from app.api.v1.stories import router as stories_router, admin_router as stories_admin_router
from app.api.v1.users import admin_router as users_admin_router
from app.api.v1.contact import router as contact_router, admin_router as contact_admin_router
from app.api.v1.chat import router as chat_router
from app.api.v1.tapin import router as tapin_router, admin_router as tapin_admin_router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME, debug=settings.APP_DEBUG)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Uploaded product/category images - equivalent to Laravel's public/storage symlink
storage_dir = Path(__file__).resolve().parent.parent / "storage"
storage_dir.mkdir(exist_ok=True)
app.mount("/storage", StaticFiles(directory=str(storage_dir)), name="storage")

app.include_router(auth_router, prefix="/api/v1")
app.include_router(auth_admin_router, prefix="/api/v1")
app.include_router(categories_router, prefix="/api/v1")
app.include_router(categories_admin_router, prefix="/api/v1")
app.include_router(products_router, prefix="/api/v1")
app.include_router(products_admin_router, prefix="/api/v1")
app.include_router(cart_router, prefix="/api/v1")
app.include_router(coupons_router, prefix="/api/v1")
app.include_router(coupons_admin_router, prefix="/api/v1")
app.include_router(shipping_router, prefix="/api/v1")
app.include_router(shipping_admin_router, prefix="/api/v1")
app.include_router(orders_admin_router, prefix="/api/v1")
app.include_router(transactions_admin_router, prefix="/api/v1")
app.include_router(payment_router, prefix="/api/v1")
app.include_router(profile_router, prefix="/api/v1")
app.include_router(profile_user_router, prefix="/api/v1")
app.include_router(sliders_router, prefix="/api/v1")
app.include_router(sliders_admin_router, prefix="/api/v1")
app.include_router(stories_router, prefix="/api/v1")
app.include_router(stories_admin_router, prefix="/api/v1")
app.include_router(users_admin_router, prefix="/api/v1")
app.include_router(contact_router, prefix="/api/v1")
app.include_router(contact_admin_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(tapin_router, prefix="/api/v1")
app.include_router(tapin_admin_router, prefix="/api/v1")


@app.get("/api/v1/health")
def health():
    return {"status": "ok"}