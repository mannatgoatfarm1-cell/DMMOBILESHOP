from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

import asyncio
from io import BytesIO
import logging
import os
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Annotated, Any, Literal
from urllib.parse import urlencode

import bcrypt
import jwt
import razorpay
import requests
from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, FastAPI, File, Form, HTTPException, Query, Request, Response, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field, field_validator
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware


MONGO_URL = os.environ["MONGO_URL"]
DB_NAME = os.environ["DB_NAME"]
JWT_SECRET = os.environ["JWT_SECRET"]
FRONTEND_URL = os.environ["FRONTEND_URL"]
ADMIN_EMAIL = os.environ["ADMIN_EMAIL"].lower()
ADMIN_PASSWORD = os.environ["ADMIN_PASSWORD"]
STORAGE_BASE = os.environ["INTEGRATION_PROXY_URL"].rstrip("/")
EMERGENT_STORAGE_KEY = os.environ["EMERGENT_LLM_KEY"]
GOOGLE_CLIENT_ID = os.environ["GOOGLE_CLIENT_ID"]
GOOGLE_CLIENT_SECRET = os.environ["GOOGLE_CLIENT_SECRET"]
GOOGLE_ALLOWED_ORIGINS = {origin.strip().rstrip("/") for origin in os.environ["GOOGLE_ALLOWED_ORIGINS"].split(",") if origin.strip()}
STORAGE_URL = f"{STORAGE_BASE}/objstore/api/v1/storage"
JWT_ALGORITHM = "HS256"
UPLOAD_DIR = ROOT_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
storage_key: str | None = None

client = AsyncIOMotorClient(MONGO_URL, serverSelectionTimeoutMS=5000)
db = client[DB_NAME]
app = FastAPI(title="MobileCart API", version="1.0.0")
api = APIRouter(prefix="/api")
app.mount("/api/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")
oauth = OAuth()
oauth.register(
    name="google",
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
    client_kwargs={"scope": "openid email profile"},
)


class ApiError(BaseModel):
    detail: str


class AddressInput(BaseModel):
    label: str = Field(min_length=1, max_length=32)
    recipient_name: str = Field(min_length=2, max_length=100)
    phone: str = Field(pattern=r"^[0-9+ -]{8,20}$")
    line1: str = Field(min_length=3, max_length=160)
    line2: str = Field(default="", max_length=160)
    city: str = Field(min_length=2, max_length=64)
    state: str = Field(min_length=2, max_length=64)
    postal_code: str = Field(min_length=4, max_length=12)
    country: str = Field(default="India", max_length=64)


class Address(AddressInput):
    id: str


class UserPublic(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: Literal["customer", "admin"]
    active: bool = True
    phone: str | None = None
    addresses: list[Address] = []
    created_at: str


class RegisterInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class LoginInput(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=128)


class ForgotPasswordInput(BaseModel):
    identifier: str = Field(min_length=1, max_length=255)


class ResetPasswordInput(BaseModel):
    token: str = Field(min_length=20, max_length=255)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_password: str = Field(min_length=8, max_length=128)


class GoogleAuthInput(BaseModel):
    code: str = Field(min_length=8, max_length=4096)
    redirect_uri: str = Field(min_length=12, max_length=500)


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    phone: str | None = Field(default=None, max_length=20)


class CategoryInput(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    slug: str = Field(pattern=r"^[a-z0-9-]{2,80}$")
    image: str | None = None
    active: bool = True


class Category(CategoryInput):
    id: str


class Variant(BaseModel):
    sku: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=1, max_length=80)
    attributes: dict[str, str] = {}
    price: int = Field(ge=0)
    stock: int = Field(ge=0)


class ProductInput(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    slug: str = Field(pattern=r"^[a-z0-9-]{2,180}$")
    sub: str = Field(default="", max_length=200)
    description: str = Field(default="", max_length=5000)
    category_slug: str = Field(min_length=2, max_length=80)
    price: int = Field(ge=0)
    original_price: int = Field(ge=0)
    stock: int = Field(ge=0)
    images: list[str] = Field(min_length=1, max_length=12)
    tag: str = Field(default="DEAL", max_length=32)
    variants: list[Variant] = Field(default_factory=list, max_length=100)
    active: bool = True
    featured: bool = False
    qc_grade: Literal["new", "excellent", "good", "fair"] = "new"
    qc_status: dict[str, Literal["pass", "fail", "unknown"]] = Field(default_factory=dict)
    imei_number: str = Field(default="", max_length=40)
    barcode: str = Field(default="", max_length=80)
    warranty_days: int = Field(default=0, ge=0, le=1095)

    @field_validator("images")
    @classmethod
    def validate_images(cls, images: list[str]) -> list[str]:
        if any(not image.startswith(("https://", "http://", "/api/uploads/", "/api/media/")) for image in images):
            raise ValueError("Images must be secure URLs or uploaded image paths")
        return images


class Product(ProductInput):
    id: str
    created_at: str
    updated_at: str
    off: str


class ProductList(BaseModel):
    items: list[Product]
    page: int
    page_size: int
    total: int
    pages: int


class CartItemInput(BaseModel):
    product_id: str
    variant_sku: str | None = None
    quantity: int = Field(ge=1, le=20)


class CartItem(BaseModel):
    product_id: str
    variant_sku: str | None = None
    quantity: int
    product: Product


class CartResponse(BaseModel):
    items: list[CartItem]
    subtotal: int
    item_count: int


class OrderCreate(BaseModel):
    address_id: str
    payment_method: Literal["upi", "card", "net_banking", "wallet", "cod", "bank_transfer"] = "upi"
    coupon_code: str | None = Field(default=None, max_length=40)


class Order(BaseModel):
    id: str
    order_number: str
    user_id: str
    items: list[dict[str, Any]]
    delivery_address: Address
    subtotal: int
    platform_fee: int
    discount: int = 0
    total: int
    status: str
    tracking: dict[str, Any]
    payment: dict[str, Any]
    created_at: str
    updated_at: str


class OrderList(BaseModel):
    items: list[Order]
    total: int


class AuctionInput(BaseModel):
    product_id: str
    starting_price: int = Field(ge=0)
    bid_increment: int = Field(gt=0)
    starts_at: str
    ends_at: str


class Auction(BaseModel):
    id: str
    product_id: str
    product: Product | None = None
    starting_price: int
    current_bid: int
    bid_increment: int
    bid_count: int
    status: str
    starts_at: str
    ends_at: str
    winner_user_id: str | None = None


class BidInput(BaseModel):
    amount: int = Field(gt=0)


class Bid(BaseModel):
    id: str
    auction_id: str
    user_id: str
    bidder_name: str
    amount: int
    created_at: str


class Dashboard(BaseModel):
    metrics: dict[str, int]
    recent_orders: list[Order]
    order_statuses: dict[str, int]
    activities: list[dict[str, str]]
    top_categories: list[dict[str, Any]] = []
    revenue_series: list[dict[str, Any]] = []


class ManagedRecordInput(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    status: str = Field(default="active", pattern=r"^[a-z_ -]{2,32}$")
    description: str = Field(default="", max_length=2000)
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("data")
    @classmethod
    def validate_data(cls, data: dict[str, Any]) -> dict[str, Any]:
        if len(data) > 24 or any(not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", key) for key in data):
            raise ValueError("Data fields are invalid")
        return data


class ManagedRecord(ManagedRecordInput):
    id: str
    resource: str
    created_at: str
    updated_at: str


class ManagedRecordList(BaseModel):
    items: list[ManagedRecord]
    total: int
    page: int
    page_size: int


class StorefrontHero(BaseModel):
    eyebrow: str = Field(default="DMMobile Shop · 2080 → 2080", max_length=100)
    title: str = Field(default="Premium Tech", max_length=100)
    highlight: str = Field(default="Bigger. Brighter. Smarter.", max_length=120)
    description: str = Field(default="Smarter Deals | Bigger Savings | Future Ready", max_length=220)
    image_url: str = Field(default="", max_length=500)


class StorefrontSection(BaseModel):
    id: str = Field(min_length=2, max_length=48, pattern=r"^[a-z0-9-]+$")
    label: str = Field(default="", max_length=100)
    title: str = Field(default="", max_length=100)
    eyebrow: str = Field(default="", max_length=100)
    active: bool = True


class StorefrontConfig(BaseModel):
    hero: StorefrontHero = Field(default_factory=StorefrontHero)
    sections: list[StorefrontSection] = Field(default_factory=list)


STOREFRONT_SECTION_DEFAULTS = [
    {"id": "flash-deals", "label": "Flash Deals", "title": "Flash Deals", "eyebrow": "LIMITED TIME", "active": True},
    {"id": "mobile-parts-deals", "label": "Mobile Parts Deals", "title": "Mobile Parts Deals", "eyebrow": "REPAIR ESSENTIALS", "active": True},
    {"id": "today-deals", "label": "Today's Deals", "title": "Today's Deals", "eyebrow": "ENDS TONIGHT", "active": True},
    {"id": "deal-of-the-day", "label": "Deal of the Day", "title": "Deal of the Day", "eyebrow": "FEATURED PICK", "active": True},
    {"id": "new-stock", "label": "New Stock", "title": "New Stock", "eyebrow": "JUST LANDED", "active": True},
    {"id": "stock-clearance", "label": "Stock Clearance Sale", "title": "Stock Clearance Sale", "eyebrow": "LAST CHANCE", "active": True},
    {"id": "trust-strip", "label": "Trust Strip", "title": "", "eyebrow": "", "active": True},
    {"id": "hot-categories", "label": "Hot Selling Categories", "title": "Hot Selling Categories", "eyebrow": "", "active": True},
    {"id": "marketplace-services", "label": "Marketplace Services", "title": "", "eyebrow": "", "active": True},
    {"id": "category-navigation", "label": "Category Navigation", "title": "", "eyebrow": "", "active": True},
    {"id": "promo-banners", "label": "Promo Banners", "title": "", "eyebrow": "", "active": True},
    {"id": "product-insights", "label": "Trending, Reviews & Why Choose", "title": "", "eyebrow": "", "active": True},
    {"id": "auction-teaser", "label": "Auction Teaser", "title": "", "eyebrow": "", "active": True},
    {"id": "blog", "label": "Blog", "title": "", "eyebrow": "", "active": True},
    {"id": "customer-community", "label": "Community & Newsletter", "title": "", "eyebrow": "", "active": True},
]


def storefront_payload(document: dict[str, Any] | None) -> StorefrontConfig:
    saved = document or {}
    hero = {**StorefrontHero().model_dump(), **(saved.get("hero") or {})}
    saved_sections = {item.get("id"): item for item in saved.get("sections", []) if item.get("id")}
    sections = [{**default, **{key: value for key, value in saved_sections.get(default["id"], {}).items() if key in default}} for default in STOREFRONT_SECTION_DEFAULTS]
    return StorefrontConfig(hero=StorefrontHero(**hero), sections=[StorefrontSection(**section) for section in sections])


class UserManagementUpdate(BaseModel):
    active: bool


class AdminUserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class PaymentUpdate(BaseModel):
    status: Literal["pending", "review_pending", "captured", "failed", "refunded", "cash_on_delivery"]
    transaction_id: str | None = Field(default=None, max_length=120)


class PaymentSettingsInput(BaseModel):
    razorpay_key_id: str = Field(default="", max_length=120)
    razorpay_key_secret: str = Field(default="", max_length=200)
    razorpay_webhook_secret: str = Field(default="", max_length=200)
    mode: Literal["test", "live"] = "test"
    upi_enabled: bool = True
    upi_id: str = Field(default="", max_length=160)
    card_enabled: bool = True
    netbanking_enabled: bool = True
    cod_enabled: bool = True
    wallet_enabled: bool = True
    bank_transfer_enabled: bool = True
    bank_account_name: str = Field(default="", max_length=120)
    bank_account_number: str = Field(default="", max_length=40)
    bank_ifsc_code: str = Field(default="", max_length=20)
    partial_payment_enabled: bool = False
    partial_payment_percent: int = Field(default=100, ge=10, le=100)

    @field_validator("upi_id")
    @classmethod
    def validate_upi_id(cls, upi_id: str) -> str:
        value = upi_id.strip().lower()
        if value and not re.fullmatch(r"[a-z0-9._-]{2,128}@[a-z0-9._-]{2,64}", value):
            raise ValueError("UPI ID format is invalid")
        return value

    @field_validator("bank_ifsc_code")
    @classmethod
    def validate_ifsc(cls, ifsc: str) -> str:
        value = ifsc.strip().upper()
        if value and not re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", value):
            raise ValueError("IFSC code format is invalid")
        return value


MASKED_PAYMENT_SECRETS = frozenset({"***", "********", "••••••••", "Saved securely — enter only to replace"})


def retained_payment_secret(submitted: str, existing: str) -> str:
    """Keep the stored secret when an admin form submits an empty or masked value."""
    value = submitted.strip()
    return existing if not value or value in MASKED_PAYMENT_SECRETS else value


class RazorpayOrderInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)


class RazorpayVerifyInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    razorpay_order_id: str = Field(min_length=4, max_length=120)
    razorpay_payment_id: str = Field(min_length=4, max_length=120)
    razorpay_signature: str = Field(min_length=8, max_length=256)


class RazorpayFailureInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    reason: str = Field(default="payment_cancelled", max_length=120)


class ManualPaymentReviewInput(BaseModel):
    action: Literal["capture", "reject"]
    note: str = Field(default="", max_length=240)


class ReturnClaimInput(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    reason: Literal["defective", "wrong_item", "damaged", "warranty_claim", "other"]
    detail: str = Field(min_length=8, max_length=1000)
    photo_file_ids: list[str] = Field(min_length=2, max_length=2)
    video_file_id: str = Field(min_length=1, max_length=80)


class ReturnDecisionInput(BaseModel):
    decision: Literal["approve", "disapprove"]
    reason: str = Field(min_length=4, max_length=500)


class ChatMessageInput(BaseModel):
    message: str = Field(min_length=1, max_length=1000)


class ChatMessage(BaseModel):
    id: str
    thread_id: str
    sender_role: Literal["customer", "admin"]
    sender_name: str
    message: str
    created_at: str


class CouponCheckInput(BaseModel):
    code: str = Field(min_length=2, max_length=40)
    subtotal: int = Field(ge=0)


class WalletAdjustmentInput(BaseModel):
    user_id: str
    amount: int = Field(gt=0, le=1_000_000)
    kind: Literal["credit", "debit"]
    note: str = Field(min_length=2, max_length=240)


class WalletSummary(BaseModel):
    user_id: str
    user_name: str
    user_email: EmailStr
    balance: int
    updated_at: str


class AdminUserDetail(BaseModel):
    user: UserPublic
    orders: list[Order]
    returns: list[ManagedRecord]
    wallet: WalletSummary


class WalletTransaction(BaseModel):
    id: str
    user_id: str
    kind: Literal["credit", "debit"]
    amount: int
    balance_after: int
    note: str
    created_at: str


class MediaFile(BaseModel):
    id: str
    url: str
    original_filename: str
    content_type: str
    size: int
    created_at: str


MANAGED_RESOURCES = {
    "vendors", "brands", "campaigns", "coupons", "subscriptions", "app-manager", "announcements",
    "banners", "notifications", "wallet-withdrawals", "shipping", "gst-tax", "settings",
}
PUBLIC_RESOURCES = {"brands", "campaigns", "coupons", "banners", "shipping", "announcements"}


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(document: dict[str, Any] | None) -> dict[str, Any] | None:
    if document is None:
        return None
    document.pop("_id", None)
    document.pop("password_hash", None)
    return document


def public_user(document: dict[str, Any]) -> UserPublic:
    payload = clean(document.copy())
    return UserPublic(**payload)


def product_payload(document: dict[str, Any]) -> Product:
    payload = clean(document.copy())
    price = payload["price"]
    original_price = payload["original_price"]
    payload["off"] = f"{round((1 - price / original_price) * 100)}% OFF" if original_price else "DEAL"
    return Product(**payload)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))


def init_storage(force: bool = False) -> str:
    global storage_key
    if storage_key and not force:
        return storage_key
    response = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_STORAGE_KEY}, timeout=30)
    response.raise_for_status()
    storage_key = response.json()["storage_key"]
    return storage_key


def put_object(path: str, data: bytes, content_type: str) -> dict[str, Any]:
    key = init_storage()
    response = requests.put(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key, "Content-Type": content_type}, data=data, timeout=120)
    response.raise_for_status()
    return response.json()


def get_object(path: str) -> tuple[bytes, str]:
    key = init_storage()
    response = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    response.raise_for_status()
    return response.content, response.headers.get("Content-Type", "application/octet-stream")


def token_for(user: dict[str, Any], token_type: str, duration: timedelta) -> str:
    return jwt.encode(
        {"sub": user["id"], "email": user["email"], "role": user["role"], "type": token_type, "exp": datetime.now(timezone.utc) + duration},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def set_session(response: Response, user: dict[str, Any]) -> None:
    response.set_cookie("access_token", token_for(user, "access", timedelta(minutes=15)), httponly=True, secure=True, samesite="none", max_age=900, path="/")
    response.set_cookie("refresh_token", token_for(user, "refresh", timedelta(days=7)), httponly=True, secure=True, samesite="none", max_age=604800, path="/")


async def current_user(request: Request) -> dict[str, Any]:
    token = request.cookies.get("access_token")
    header = request.headers.get("authorization", "")
    if not token and header.startswith("Bearer "):
        token = header[7:]
    if not token:
        raise HTTPException(401, "Authentication required")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise ValueError("Wrong token type")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Invalid or expired session")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user or not user.get("active", True) or user.get("role") != payload.get("role"):
        raise HTTPException(401, "Session is no longer valid")
    return user


async def admin_user(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(403, "Admin access required")
    return user


async def super_admin_user(user: Annotated[dict[str, Any], Depends(admin_user)]) -> dict[str, Any]:
    if user.get("admin_level") != "super":
        raise HTTPException(403, "Super admin access required")
    return user


async def require_customer(user: Annotated[dict[str, Any], Depends(current_user)]) -> dict[str, Any]:
    return user


async def seed_data() -> None:
    legacy_admins = await db.users.find({"email": {"$regex": r"@dealkr\.local$"}}, {"_id": 0, "id": 1}).to_list(20)
    for legacy in legacy_admins:
        await db.users.update_one({"id": legacy["id"]}, {"$set": {"email": f"legacy-{legacy['id'][:8]}@dealkr.example.com", "active": False, "updated_at": now()}})
    admin = await db.users.find_one({"email": ADMIN_EMAIL})
    if not admin:
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": ADMIN_EMAIL, "name": "MobileCart Admin", "role": "admin", "admin_level": "super", "active": True, "phone": None, "addresses": [], "password_hash": hash_password(ADMIN_PASSWORD), "created_at": now()})
    elif not verify_password(ADMIN_PASSWORD, admin["password_hash"]):
        await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"password_hash": hash_password(ADMIN_PASSWORD)}})
    await db.users.update_one({"email": ADMIN_EMAIL}, {"$set": {"admin_level": "super", "active": True}})
    deepak = await db.users.find_one({"username": "deepak143"})
    if not deepak:
        await db.users.insert_one({"id": str(uuid.uuid4()), "email": "deepak143@mobilecart.com", "username": "deepak143", "name": "Deepak", "role": "admin", "admin_level": "super", "active": True, "phone": None, "addresses": [], "password_hash": hash_password("deepak143"), "created_at": now()})
    else:
        await db.users.update_one({"username": "deepak143"}, {"$set": {"password_hash": hash_password("deepak143"), "role": "admin", "admin_level": "super", "active": True}})
    catalog = [
        ("iphone", "iPhone 15 Pro Max", "256GB · Natural Titanium", "mobiles", 109900, 134900, "AI PICK", "https://static.prod-images.emergentagent.com/jobs/4d8ba7d6-4cc2-48fd-a329-88470c3b0d75/images/29f5c8a586dbdda9921a2bd753139bccf4cd74c5f0004bb94e7b3148cb72b303.jpeg"),
        ("samsung", "Samsung S23 Ultra", "256GB · Phantom Black", "mobiles", 64999, 89999, "BESTSELLER", "https://images.unsplash.com/photo-1678911820864-e2c567c655d7?auto=format&fit=crop&w=800&q=85"),
        ("macbook", "MacBook Air M2", "13-inch · 8GB RAM", "laptops", 89900, 114900, "TOP RATED", "https://static.prod-images.emergentagent.com/jobs/4d8ba7d6-4cc2-48fd-a329-88470c3b0d75/images/75c5dc30a6aeec454c376afa972e9fe1b132b2ab74a220483c2294f0d13ce72a.jpeg"),
        ("nothing-phone-2", "Nothing Phone (2)", "256GB · White", "mobiles", 32999, 39999, "NEW", "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=800&q=85"),
        ("boat-airdopes-141", "boAt Airdopes 141", "TWS Wireless · Black", "audio", 1299, 2999, "DEAL", "https://images.unsplash.com/photo-1606220945770-b5b6c2c55bf1?auto=format&fit=crop&w=800&q=85"),
        ("pixel-7", "Google Pixel 7", "128GB · Snow", "mobiles", 28999, 49999, "VALUE", "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=800&q=85"),
        ("apple-watch-9", "Apple Watch Series 9", "45mm · Midnight", "smartwatch", 37900, 45900, "BESTSELLER", "https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=800&q=85"),
        ("dualsense", "Sony DualSense Controller", "PS5 · Midnight Black", "gaming", 5490, 6990, "HOT DEAL", "https://images.unsplash.com/photo-1633499737221-5e3406d4d952?auto=format&fit=crop&w=800&q=85"),
        ("sony-camera", "Sony Alpha Mirrorless", "24MP · Body + Lens", "cameras", 71999, 89999, "TOP RATED", "https://images.unsplash.com/photo-1486492440844-ebc195542a40?auto=format&fit=crop&w=800&q=85"),
        ("oneplus-12r", "OnePlus 12R", "256GB · Iron Gray", "mobiles", 39999, 45999, "NEW", "https://images.unsplash.com/photo-1598327105666-5b89351aff97?auto=format&fit=crop&w=800&q=85"),
        ("redmi-note-13", "Redmi Note 13 Pro", "256GB · Aurora Purple", "mobiles", 24999, 29999, "VALUE", "https://images.unsplash.com/photo-1678911820864-e2c567c655d7?auto=format&fit=crop&w=800&q=85"),
        ("dell-xps-13", "Dell XPS 13", "16GB · 512GB SSD", "laptops", 99900, 119900, "TOP RATED", "https://images.unsplash.com/photo-1650661926447-9efb2610f64c?auto=format&fit=crop&w=800&q=85"),
        ("sony-wh1000", "Sony WH-1000XM5", "Wireless · Silver", "audio", 26990, 34990, "BESTSELLER", "https://images.unsplash.com/photo-1590658268037-6bf12165a8df?auto=format&fit=crop&w=800&q=85"),
    ]
    for name in ["mobiles", "laptops", "tablets", "smartwatch", "accessories", "audio", "gaming", "cameras", "home-living"]:
        title = "Smart Watches" if name == "smartwatch" else name.replace("-", " & ").title()
        await db.categories.update_one({"slug": name}, {"$setOnInsert": {"id": str(uuid.uuid4()), "name": title, "slug": name, "image": None, "active": True}}, upsert=True)
    for slug, name, sub, category, price, original_price, tag, image in catalog:
        await db.products.update_one({"slug": slug}, {"$setOnInsert": {"id": slug, "name": name, "slug": slug, "sub": sub, "description": f"{name} available with MobileCart Assured quality.", "category_slug": category, "price": price, "original_price": original_price, "stock": 25, "images": [image], "tag": tag, "variants": [], "active": True, "featured": True, "created_at": now(), "updated_at": now()}}, upsert=True)
    phone = await db.products.find_one({"slug": "iphone"}, {"_id": 0})
    if phone:
        await db.auctions.update_one({"product_id": phone["id"], "status": "live"}, {"$setOnInsert": {"id": "auction-iphone-14", "product_id": phone["id"], "starting_price": 50000, "current_bid": 68900, "bid_increment": 500, "bid_count": 12, "status": "live", "starts_at": (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat(), "ends_at": (datetime.now(timezone.utc) + timedelta(days=2)).isoformat(), "winner_user_id": None}}, upsert=True)
    section_seeds = {
        "vendors": [("CellPoint Store", "approved", "Verified marketplace vendor", {"email": "vendor@cellpoint.example.com", "commission": "12%"})],
        "brands": [("Apple", "active", "Official brand collection", {"slug": "apple"})],
        "campaigns": [("Mobile Festival", "published", "Seasonal device offers", {"starts_at": now(), "ends_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()})],
        "coupons": [("WELCOME10", "active", "10% welcome discount", {"code": "WELCOME10", "discount": "10%", "minimum_order": 999})],
        "subscriptions": [("MobileCart Gold", "active", "Premium membership: free delivery, priority support, early access", {"monthly_price": 99})],
        "app-manager": [("Homepage Feed", "active", "Customer home modules configuration", {"version": "1.0"})],
        "banners": [("Premium Refurbished", "published", "Quality-checked refurbished devices", {"link": "/category"})],
        "notifications": [("Welcome to MobileCart", "published", "New deals and order updates are ready.", {"audience": "customers"})],
        "wallet-withdrawals": [("Vendor settlement policy", "active", "Weekly settlement configuration", {"minimum_withdrawal": 500})],
        "shipping": [("Standard Delivery", "active", "Free delivery across eligible pin codes", {"fee": 0, "estimated_days": "3-5"})],
        "gst-tax": [("GST Standard", "active", "Default tax rule for electronics", {"rate": 18})],
        "settings": [("Store Settings", "active", "Global marketplace controls", {"currency": "INR", "support_email": "support@mobilecart.example.com"})],
    }
    for resource, records in section_seeds.items():
        collection = db[f"admin_{resource.replace('-', '_')}"]
        for title, status, description, data in records:
            timestamp = now()
            await collection.update_one({"title": title}, {"$setOnInsert": {"id": str(uuid.uuid4()), "resource": resource, "title": title, "status": status, "description": description, "data": data, "created_at": timestamp, "updated_at": timestamp}}, upsert=True)


@app.on_event("startup")
async def initialise() -> None:
    await db.command("ping")
    await db.users.create_index("email", unique=True)
    await db.products.create_index("slug", unique=True)
    await db.users.create_index("username", unique=True, sparse=True)
    await db.users.create_index("google_id", unique=True, sparse=True)
    await db.categories.create_index("slug", unique=True)
    await db.products.create_index([("name", "text"), ("description", "text"), ("sub", "text")])
    await db.products.create_index([("active", 1), ("category_slug", 1), ("price", 1)])
    await db.carts.create_index("user_id", unique=True)
    await db.wishlists.create_index("user_id", unique=True)
    await db.orders.create_index([("user_id", 1), ("created_at", -1)])
    await db.auctions.create_index([("status", 1), ("ends_at", 1)])
    await db.bids.create_index([("auction_id", 1), ("created_at", -1)])
    await db.login_attempts.create_index("identifier", unique=True)
    await db.password_reset_tokens.create_index("expires_at", expireAfterSeconds=0)
    await db.wallets.create_index("user_id", unique=True)
    await db.wallet_transactions.create_index([("user_id", 1), ("created_at", -1)])
    await db.media_files.create_index("storage_path", unique=True)
    await db.returns.create_index([("user_id", 1), ("created_at", -1)])
    await db.support_tickets.create_index([("user_id", 1), ("created_at", -1)])
    for resource in MANAGED_RESOURCES:
        await db[f"admin_{resource.replace('-', '_')}"] .create_index([("status", 1), ("updated_at", -1)])
    await seed_data()
    try:
        await asyncio.to_thread(init_storage)
        logger.info("Object storage initialized")
    except requests.RequestException as error:
        logger.error("Object storage initialization failed: %s", error)


@app.on_event("shutdown")
async def shutdown() -> None:
    client.close()


@app.exception_handler(HTTPException)
async def http_error(_: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc.detail)})


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    message = "; ".join(error["msg"] for error in exc.errors())
    return JSONResponse(status_code=422, content={"detail": message})


@api.get("/health")
async def health() -> dict[str, str]:
    await db.command("ping")
    return {"status": "ok"}


@api.post("/auth/register", response_model=UserPublic, status_code=201)
async def register(input: RegisterInput, response: Response) -> UserPublic:
    if input.password != input.confirm_password:
        raise HTTPException(422, "Passwords do not match")
    email = str(input.email).lower()
    if await db.users.find_one({"email": email}, {"_id": 0, "id": 1}):
        raise HTTPException(409, "An account with this email already exists")
    user = {"id": str(uuid.uuid4()), "email": email, "name": input.name.strip(), "role": "customer", "phone": None, "addresses": [], "password_hash": hash_password(input.password), "created_at": now()}
    await db.users.insert_one(user.copy())
    set_session(response, user)
    return public_user(user)


@api.post("/auth/login", response_model=UserPublic)
async def login(input: LoginInput, request: Request, response: Response) -> UserPublic:
    identifier = input.identifier.strip().lower()
    user = await db.users.find_one({"$or": [{"email": identifier}, {"username": identifier}]}, {"_id": 0})
    attempt = await db.login_attempts.find_one({"identifier": identifier}, {"_id": 0})
    if attempt and attempt.get("locked_until", "") > now():
        raise HTTPException(429, "Too many sign-in attempts. Please try again in 15 minutes")
    if user and verify_password(input.password, user["password_hash"]):
        if not user.get("active", True):
            raise HTTPException(403, "This account is inactive")
        await db.login_attempts.delete_one({"identifier": identifier})
        set_session(response, user)
        return public_user(user)
    failures = (attempt or {}).get("failures", 0) + 1
    update: dict[str, Any] = {"failures": failures, "updated_at": now()}
    if failures >= 5:
        update["locked_until"] = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()
    await db.login_attempts.update_one({"identifier": identifier}, {"$set": update}, upsert=True)
    raise HTTPException(401, "Incorrect email or password")


@api.post("/auth/google", response_model=UserPublic)
async def login_with_google(input: GoogleAuthInput, request: Request, response: Response) -> UserPublic:
    redirect_uri = input.redirect_uri.rstrip("/")
    if redirect_uri.rsplit("/auth/google", 1)[0] not in GOOGLE_ALLOWED_ORIGINS or not redirect_uri.endswith("/auth/google"):
        raise HTTPException(400, "Google sign-in redirect is not allowed")
    try:
        token = await oauth.google.fetch_access_token(code=input.code, redirect_uri=redirect_uri)
        if token.get("id_token"):
            user_info = await oauth.google.parse_id_token(request, token)
        else:
            user_info_response = await oauth.google.get("userinfo", token=token)
            user_info = user_info_response.json()
    except Exception as error:
        logger.warning("Google sign-in exchange failed: %s", error)
        raise HTTPException(401, "Google sign-in could not be completed") from error
    if not user_info or not user_info.get("email") or not user_info.get("email_verified"):
        raise HTTPException(401, "A verified Google email is required")
    email = str(user_info["email"]).lower()
    google_id = str(user_info["sub"])
    user = await db.users.find_one({"$or": [{"google_id": google_id}, {"email": email}]}, {"_id": 0})
    if not user:
        user = {"id": str(uuid.uuid4()), "email": email, "google_id": google_id, "name": str(user_info.get("name") or email.split("@")[0]), "role": "customer", "active": True, "phone": None, "addresses": [], "password_hash": hash_password(secrets.token_urlsafe(32)), "created_at": now()}
        await db.users.insert_one(user.copy())
    else:
        if not user.get("active", True):
            raise HTTPException(403, "This account is inactive")
        if user.get("google_id") and user["google_id"] != google_id:
            raise HTTPException(401, "This Google account does not match the linked MobileCart account")
        if not user.get("google_id"):
            await db.users.update_one({"id": user["id"]}, {"$set": {"google_id": google_id, "updated_at": now()}})
            user["google_id"] = google_id
    set_session(response, user)
    return public_user(user)


@api.post("/auth/refresh", response_model=UserPublic)
async def refresh(request: Request, response: Response) -> UserPublic:
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "Refresh session required")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "refresh":
            raise ValueError("Wrong token")
    except (jwt.InvalidTokenError, ValueError):
        raise HTTPException(401, "Invalid or expired refresh session")
    user = await db.users.find_one({"id": payload["sub"]}, {"_id": 0})
    if not user or not user.get("active", True) or user.get("role") != payload.get("role"):
        raise HTTPException(401, "Session is no longer valid")
    set_session(response, user)
    return public_user(user)


@api.post("/auth/logout", status_code=204)
async def logout() -> Response:
    response = Response(status_code=204)
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return response


@api.post("/auth/forgot-password")
async def forgot_password(input: ForgotPasswordInput) -> dict[str, Any]:
    identifier = input.identifier.strip().lower()
    user = await db.users.find_one({"$or": [{"email": identifier}, {"username": identifier}]}, {"_id": 0, "id": 1})
    if user:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
        await db.password_reset_tokens.insert_one({"token": token, "user_id": user["id"], "used": False, "expires_at": expires_at})
        print(f"MobileCart password reset link: {FRONTEND_URL}/login?reset_token={token}")
    return {"message": "If this account exists, password reset instructions have been created."}


@api.post("/auth/reset-password", response_model=UserPublic)
async def reset_password(input: ResetPasswordInput) -> UserPublic:
    if input.new_password != input.confirm_password:
        raise HTTPException(422, "Passwords do not match")
    reset = await db.password_reset_tokens.find_one({"token": input.token, "used": False, "expires_at": {"$gt": datetime.now(timezone.utc)}}, {"_id": 0})
    if not reset:
        raise HTTPException(400, "This password reset link is invalid or has expired")
    user = await db.users.find_one({"id": reset["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(404, "Account not found")
    await db.users.update_one({"id": user["id"]}, {"$set": {"password_hash": hash_password(input.new_password), "updated_at": now()}})
    await db.password_reset_tokens.update_one({"token": input.token}, {"$set": {"used": True, "used_at": now()}})
    identifiers = [user["email"].lower()]
    if user.get("username"):
        identifiers.append(user["username"].lower())
    await db.login_attempts.delete_many({"identifier": {"$in": identifiers}})
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return public_user(updated)


@api.get("/auth/me", response_model=UserPublic)
async def me(user: Annotated[dict[str, Any], Depends(current_user)]) -> UserPublic:
    return public_user(user)


@api.patch("/auth/me", response_model=UserPublic)
async def update_profile(input: ProfileUpdate, user: Annotated[dict[str, Any], Depends(current_user)]) -> UserPublic:
    await db.users.update_one({"id": user["id"]}, {"$set": {"name": input.name.strip(), "phone": input.phone, "updated_at": now()}})
    updated = await db.users.find_one({"id": user["id"]}, {"_id": 0})
    return public_user(updated)


@api.post("/auth/me/addresses", response_model=Address, status_code=201)
async def add_address(input: AddressInput, user: Annotated[dict[str, Any], Depends(current_user)]) -> Address:
    address = {"id": str(uuid.uuid4()), **input.model_dump()}
    await db.users.update_one({"id": user["id"]}, {"$push": {"addresses": address}})
    return Address(**address)


@api.delete("/auth/me/addresses/{address_id}", status_code=204)
async def remove_address(address_id: str, user: Annotated[dict[str, Any], Depends(current_user)]) -> Response:
    result = await db.users.update_one({"id": user["id"]}, {"$pull": {"addresses": {"id": address_id}}})
    if result.modified_count == 0:
        raise HTTPException(404, "Address not found")
    return Response(status_code=204)


@api.get("/categories", response_model=list[Category])
async def list_categories() -> list[Category]:
    rows = await db.categories.find({"active": True}, {"_id": 0}).sort("name", 1).to_list(100)
    return [Category(**row) for row in rows]


@api.get("/products", response_model=ProductList)
async def list_products(response: Response, query: str | None = None, category: str | None = None, min_price: int | None = Query(default=None, ge=0), max_price: int | None = Query(default=None, ge=0), page: int = Query(default=1, ge=1), page_size: int = Query(default=24, ge=1, le=100), sort: Literal["newest", "price_asc", "price_desc"] = "newest") -> ProductList:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    filter_query: dict[str, Any] = {"active": True}
    if category:
        filter_query["category_slug"] = category
    if query:
        regex = re.escape(query.strip())
        filter_query["$or"] = [{"name": {"$regex": regex, "$options": "i"}}, {"sub": {"$regex": regex, "$options": "i"}}, {"description": {"$regex": regex, "$options": "i"}}]
    if min_price is not None or max_price is not None:
        filter_query["price"] = {**({"$gte": min_price} if min_price is not None else {}), **({"$lte": max_price} if max_price is not None else {})}
    sort_value = {"newest": ("created_at", -1), "price_asc": ("price", 1), "price_desc": ("price", -1)}[sort]
    total = await db.products.count_documents(filter_query)
    rows = await db.products.find(filter_query, {"_id": 0}).sort(*sort_value).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return ProductList(items=[product_payload(row) for row in rows], page=page, page_size=page_size, total=total, pages=max(1, (total + page_size - 1) // page_size))


@api.get("/products/{product_id_or_slug}", response_model=Product)
async def get_product(product_id_or_slug: str, response: Response) -> Product:
    response.headers["Cache-Control"] = "no-store, max-age=0"
    row = await db.products.find_one({"$and": [{"active": True}, {"$or": [{"id": product_id_or_slug}, {"slug": product_id_or_slug}]}]}, {"_id": 0})
    if not row:
        raise HTTPException(404, "Product not found")
    return product_payload(row)


async def cart_response(user_id: str) -> CartResponse:
    cart = await db.carts.find_one({"user_id": user_id}, {"_id": 0}) or {"items": []}
    items: list[CartItem] = []
    for item in cart.get("items", []):
        product = await db.products.find_one({"id": item["product_id"], "active": True}, {"_id": 0})
        if product:
            items.append(CartItem(product_id=item["product_id"], variant_sku=item.get("variant_sku"), quantity=item["quantity"], product=product_payload(product)))
    return CartResponse(items=items, subtotal=sum(item.product.price * item.quantity for item in items), item_count=sum(item.quantity for item in items))


@api.get("/cart", response_model=CartResponse)
async def get_cart(user: Annotated[dict[str, Any], Depends(require_customer)]) -> CartResponse:
    return await cart_response(user["id"])


@api.post("/cart/items", response_model=CartResponse)
async def add_cart_item(input: CartItemInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> CartResponse:
    product = await db.products.find_one({"id": input.product_id, "active": True}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    available = product["stock"]
    if input.variant_sku:
        variant = next((variant for variant in product["variants"] if variant["sku"] == input.variant_sku), None)
        if not variant:
            raise HTTPException(404, "Product variant not found")
        available = variant["stock"]
    if input.quantity > available:
        raise HTTPException(409, "Requested quantity is not available")
    cart = await db.carts.find_one({"user_id": user["id"]}, {"_id": 0})
    item = {"product_id": input.product_id, "variant_sku": input.variant_sku, "quantity": input.quantity}
    if not cart:
        await db.carts.insert_one({"user_id": user["id"], "items": [item], "updated_at": now()})
    else:
        existing_index = next((index for index, row in enumerate(cart["items"]) if row["product_id"] == input.product_id and row.get("variant_sku") == input.variant_sku), None)
        if existing_index is None:
            await db.carts.update_one({"user_id": user["id"]}, {"$push": {"items": item}, "$set": {"updated_at": now()}})
        else:
            new_quantity = cart["items"][existing_index]["quantity"] + input.quantity
            if new_quantity > available:
                raise HTTPException(409, "Requested quantity is not available")
            await db.carts.update_one({"user_id": user["id"], "items.product_id": input.product_id}, {"$set": {f"items.{existing_index}.quantity": new_quantity, "updated_at": now()}})
    return await cart_response(user["id"])


@api.patch("/cart/items/{product_id}", response_model=CartResponse)
async def set_cart_quantity(product_id: str, input: CartItemInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> CartResponse:
    if product_id != input.product_id:
        raise HTTPException(400, "Product identifier mismatch")
    product = await db.products.find_one({"id": product_id, "active": True}, {"_id": 0})
    if not product:
        raise HTTPException(404, "Product not found")
    available = product["stock"]
    if input.variant_sku:
        variant = next((row for row in product["variants"] if row["sku"] == input.variant_sku), None)
        if not variant:
            raise HTTPException(404, "Product variant not found")
        available = variant["stock"]
    if input.quantity < 1 or input.quantity > available:
        raise HTTPException(409, "Requested quantity is not available")
    result = await db.carts.update_one({"user_id": user["id"], "items.product_id": product_id}, {"$set": {"items.$.quantity": input.quantity, "updated_at": now()}})
    if result.modified_count == 0:
        raise HTTPException(404, "Cart item not found")
    return await cart_response(user["id"])


@api.delete("/cart/items/{product_id}", status_code=204)
async def remove_cart_item(product_id: str, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Response:
    await db.carts.update_one({"user_id": user["id"]}, {"$pull": {"items": {"product_id": product_id}}, "$set": {"updated_at": now()}})
    return Response(status_code=204)


@api.get("/wishlist", response_model=list[Product])
async def get_wishlist(user: Annotated[dict[str, Any], Depends(require_customer)]) -> list[Product]:
    wishlist = await db.wishlists.find_one({"user_id": user["id"]}, {"_id": 0}) or {"product_ids": []}
    rows = await db.products.find({"id": {"$in": wishlist["product_ids"]}, "active": True}, {"_id": 0}).to_list(100)
    return [product_payload(row) for row in rows]


@api.put("/wishlist/{product_id}", status_code=204)
async def add_wishlist(product_id: str, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Response:
    if not await db.products.find_one({"id": product_id, "active": True}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Product not found")
    await db.wishlists.update_one({"user_id": user["id"]}, {"$setOnInsert": {"user_id": user["id"]}, "$addToSet": {"product_ids": product_id}}, upsert=True)
    return Response(status_code=204)


@api.delete("/wishlist/{product_id}", status_code=204)
async def remove_wishlist(product_id: str, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Response:
    await db.wishlists.update_one({"user_id": user["id"]}, {"$pull": {"product_ids": product_id}})
    return Response(status_code=204)


async def coupon_discount(code: str | None, subtotal: int) -> tuple[int, str | None]:
    if not code:
        return 0, None
    coupon = await db.admin_coupons.find_one({"status": {"$in": ["active", "published"]}, "data.code": code.strip().upper()}, {"_id": 0})
    if not coupon:
        raise HTTPException(404, "Coupon is not active or does not exist")
    data = coupon.get("data", {})
    minimum = int(data.get("minimum_order", 0))
    if subtotal < minimum:
        raise HTTPException(422, f"Coupon requires a minimum order of ₹{minimum}")
    raw_discount = str(data.get("discount", "0")).strip()
    discount = round(subtotal * float(raw_discount[:-1]) / 100) if raw_discount.endswith("%") else int(float(raw_discount))
    return min(max(discount, 0), subtotal), str(data.get("code", code)).upper()


@api.post("/coupons/validate")
async def validate_coupon(input: CouponCheckInput) -> dict[str, Any]:
    discount, code = await coupon_discount(input.code, input.subtotal)
    return {"code": code, "discount": discount, "subtotal_after_discount": input.subtotal - discount}


@api.post("/orders", response_model=Order, status_code=201)
async def create_order(input: OrderCreate, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Order:
    cart = await cart_response(user["id"])
    if not cart.items:
        raise HTTPException(400, "Your cart is empty")
    payment_settings = await get_payment_settings()
    method_enabled = {
        "upi": payment_settings.get("upi_enabled", True),
        "card": payment_settings.get("card_enabled", True),
        "net_banking": payment_settings.get("netbanking_enabled", True),
        "wallet": payment_settings.get("wallet_enabled", True),
        "cod": payment_settings.get("cod_enabled", True),
        "bank_transfer": payment_settings.get("bank_transfer_enabled", True),
    }
    if not method_enabled.get(input.payment_method, False):
        raise HTTPException(422, "यह payment method अभी उपलब्ध नहीं है")
    address = next((row for row in user.get("addresses", []) if row["id"] == input.address_id), None)
    if not address:
        raise HTTPException(404, "Delivery address not found")
    discount, coupon_code = await coupon_discount(input.coupon_code, cart.subtotal)
    total = max(0, cart.subtotal - discount + 99)
    created = now()
    payment_status = "pending" if input.payment_method != "cod" else "cash_on_delivery"
    if input.payment_method == "wallet":
        debit = await db.wallets.update_one({"user_id": user["id"], "balance": {"$gte": total}}, {"$inc": {"balance": -total}, "$set": {"updated_at": created}})
        if debit.modified_count == 0:
            raise HTTPException(409, "Your MobileCart Wallet balance is insufficient")
        wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0})
        await db.wallet_transactions.insert_one({"id": str(uuid.uuid4()), "user_id": user["id"], "kind": "debit", "amount": total, "balance_after": wallet["balance"], "note": f"Order payment {coupon_code or ''}".strip(), "created_at": created})
        payment_status = "captured"
    order_items: list[dict[str, Any]] = []
    for cart_item in cart.items:
        result = await db.products.update_one({"id": cart_item.product_id, "stock": {"$gte": cart_item.quantity}}, {"$inc": {"stock": -cart_item.quantity}, "$set": {"updated_at": now()}})
        if result.modified_count == 0:
            raise HTTPException(409, f"{cart_item.product.name} is no longer in stock")
        order_items.append({"product_id": cart_item.product_id, "name": cart_item.product.name, "image": cart_item.product.images[0], "price": cart_item.product.price, "quantity": cart_item.quantity, "variant_sku": cart_item.variant_sku, "imei_number": cart_item.product.imei_number, "barcode": cart_item.product.barcode, "warranty_days": cart_item.product.warranty_days})
    manual = input.payment_method == "bank_transfer"
    if manual and not payment_settings.get("upi_id"):
        raise HTTPException(422, "Admin को पहले Personal UPI ID configure करनी होगी")
    order_number = f"DM-{secrets.randbelow(900000) + 100000}"
    order = {"id": str(uuid.uuid4()), "order_number": order_number, "user_id": user["id"], "items": order_items, "delivery_address": address, "subtotal": cart.subtotal, "discount": discount, "coupon_code": coupon_code, "platform_fee": 99, "total": total, "status": "payment_pending" if not manual else "payment_proof_required", "tracking": {"status": "Order placed", "events": [{"status": "Order placed", "at": created}]}, "payment": {"provider": "manual_upi" if manual else ("mobilecart_wallet" if input.payment_method == "wallet" else "razorpay"), "method": input.payment_method, "status": payment_status, "provider_order_id": None, "transaction_id": None, "manual_request_ref": f"UPI-{order_number}", "payment_reference": None} if manual else {"provider": "mobilecart_wallet" if input.payment_method == "wallet" else "razorpay", "method": input.payment_method, "status": payment_status, "provider_order_id": None, "transaction_id": None}, "created_at": created, "updated_at": created}
    if input.payment_method in {"cod", "wallet"}:
        order["status"] = "confirmed"
    await db.orders.insert_one(order.copy())
    await db.carts.update_one({"user_id": user["id"]}, {"$set": {"items": [], "updated_at": now()}})
    return Order(**order)


@api.get("/orders", response_model=OrderList)
async def list_orders(user: Annotated[dict[str, Any], Depends(require_customer)], page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100)) -> OrderList:
    filter_query = {} if user["role"] == "admin" else {"user_id": user["id"]}
    total = await db.orders.count_documents(filter_query)
    rows = await db.orders.find(filter_query, {"_id": 0}).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return OrderList(items=[Order(**row) for row in rows], total=total)


@api.get("/orders/{order_id}", response_model=Order)
async def get_order(order_id: str, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Order:
    filter_query: dict[str, Any] = {"id": order_id}
    if user["role"] != "admin":
        filter_query["user_id"] = user["id"]
    order = await db.orders.find_one(filter_query, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    return Order(**order)


@api.get("/orders/{order_id}/invoice")
async def download_order_invoice(order_id: str, user: Annotated[dict[str, Any], Depends(require_customer)]) -> StreamingResponse:
    filter_query: dict[str, Any] = {"id": order_id}
    if user["role"] != "admin":
        filter_query["user_id"] = user["id"]
    order = await db.orders.find_one(filter_query, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    pdf.setFillColorRGB(0.08, 0.11, 0.2)
    pdf.rect(0, height - 110, width, 110, fill=1, stroke=0)
    pdf.setFillColorRGB(1, 1, 1)
    pdf.setFont("Helvetica-Bold", 24)
    pdf.drawString(48, height - 62, "DMobileMart")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, height - 82, "Tax Invoice / Order Bill")
    pdf.setFillColorRGB(0.1, 0.14, 0.24)
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(48, height - 145, f"Invoice for {order['order_number']}")
    pdf.setFont("Helvetica", 10)
    pdf.drawString(48, height - 164, f"Order date: {str(order['created_at'])[:10]}     Status: {order['status'].replace('_', ' ').title()}")
    address = order.get("delivery_address", {})
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(48, height - 198, "Deliver to")
    pdf.setFont("Helvetica", 10)
    for index, line in enumerate([address.get("recipient_name", ""), address.get("line1", ""), f"{address.get('city', '')} - {address.get('postal_code', '')}"]):
        pdf.drawString(48, height - 216 - index * 15, str(line))
    y = height - 285
    pdf.setFont("Helvetica-Bold", 10)
    pdf.drawString(48, y, "Item")
    pdf.drawRightString(440, y, "Qty")
    pdf.drawRightString(540, y, "Amount")
    pdf.line(48, y - 8, 548, y - 8)
    pdf.setFont("Helvetica", 10)
    for item in order.get("items", []):
        y -= 24
        if y < 100:
            pdf.showPage(); y = height - 60
        pdf.drawString(48, y, str(item.get("name", "Product"))[:58])
        pdf.drawRightString(440, y, str(item.get("quantity", 1)))
        pdf.drawRightString(540, y, f"Rs. {int(item.get('price', 0)) * int(item.get('quantity', 1)):,}")
        identifiers = " · ".join(part for part in [f"IMEI: {item.get('imei_number')}" if item.get("imei_number") else "", f"Barcode: {item.get('barcode')}" if item.get("barcode") else ""] if part)
        if identifiers:
            y -= 12
            pdf.setFont("Helvetica", 8)
            pdf.drawString(58, y, identifiers[:90])
            pdf.setFont("Helvetica", 10)
    y -= 28
    pdf.line(330, y, 548, y)
    for label, value in [("Subtotal", order.get("subtotal", 0)), ("Discount", -order.get("discount", 0)), ("Platform fee", order.get("platform_fee", 0)), ("Total paid", order.get("total", 0))]:
        y -= 19
        pdf.setFont("Helvetica-Bold" if label == "Total paid" else "Helvetica", 10)
        pdf.drawString(360, y, label)
        pdf.drawRightString(540, y, f"Rs. {int(value):,}")
    pdf.setFont("Helvetica", 8)
    pdf.drawString(48, 42, "Thank you for shopping with DMobileMart. This is a computer-generated invoice.")
    pdf.save()
    output.seek(0)
    return StreamingResponse(output, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="MobileCart-{order["order_number"]}-invoice.pdf"'})


@api.get("/wallet")
async def customer_wallet(user: Annotated[dict[str, Any], Depends(require_customer)]) -> dict[str, Any]:
    wallet = await db.wallets.find_one({"user_id": user["id"]}, {"_id": 0}) or {"user_id": user["id"], "balance": 0, "updated_at": user["created_at"]}
    transactions = await db.wallet_transactions.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).limit(30).to_list(30)
    return {"balance": wallet["balance"], "updated_at": wallet["updated_at"], "transactions": [WalletTransaction(**row) for row in transactions]}


async def auction_payload(row: dict[str, Any]) -> Auction:
    payload = clean(row.copy())
    product = await db.products.find_one({"id": payload["product_id"]}, {"_id": 0})
    payload["product"] = product_payload(product) if product else None
    return Auction(**payload)


async def reconcile_expired_auctions() -> None:
    timestamp = now()
    expired = await db.auctions.find({"status": "live", "ends_at": {"$lte": timestamp}}, {"_id": 0, "id": 1}).to_list(100)
    for auction in expired:
        winner = await db.bids.find_one({"auction_id": auction["id"]}, {"_id": 0, "user_id": 1}, sort=[("amount", -1), ("created_at", 1)])
        await db.auctions.update_one({"id": auction["id"], "status": "live", "ends_at": {"$lte": timestamp}}, {"$set": {"status": "closed", "winner_user_id": winner["user_id"] if winner else None}})


@api.get("/auctions", response_model=list[Auction])
async def list_auctions(status: str = "live") -> list[Auction]:
    await reconcile_expired_auctions()
    rows = await db.auctions.find({"status": status}, {"_id": 0}).sort("ends_at", 1).to_list(100)
    return [await auction_payload(row) for row in rows]


@api.get("/auctions/{auction_id}", response_model=Auction)
async def get_auction(auction_id: str) -> Auction:
    await reconcile_expired_auctions()
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Auction not found")
    return await auction_payload(auction)


@api.post("/auctions/{auction_id}/bids", response_model=Bid, status_code=201)
async def place_bid(auction_id: str, input: BidInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Bid:
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction or auction["status"] != "live" or auction["ends_at"] <= now():
        raise HTTPException(409, "This auction is no longer live")
    minimum = auction["current_bid"] + auction["bid_increment"]
    if input.amount < minimum:
        raise HTTPException(409, f"Your bid must be at least ₹{minimum}")
    result = await db.auctions.update_one({"id": auction_id, "status": "live", "current_bid": {"$lt": input.amount}, "ends_at": {"$gt": now()}}, {"$set": {"current_bid": input.amount, "leading_user_id": user["id"]}, "$inc": {"bid_count": 1}})
    if result.modified_count == 0:
        raise HTTPException(409, "A higher bid was placed. Refresh and try again")
    bid = {"id": str(uuid.uuid4()), "auction_id": auction_id, "user_id": user["id"], "bidder_name": user["name"], "amount": input.amount, "created_at": now()}
    await db.bids.insert_one(bid.copy())
    return Bid(**bid)


@api.get("/auctions/{auction_id}/bids", response_model=list[Bid])
async def bid_history(auction_id: str) -> list[Bid]:
    rows = await db.bids.find({"auction_id": auction_id}, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return [Bid(**row) for row in rows]


@api.get("/admin/dashboard", response_model=Dashboard)
async def dashboard(_: Annotated[dict[str, Any], Depends(admin_user)]) -> Dashboard:
    orders = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).limit(5).to_list(5)
    order_statuses: dict[str, int] = {}
    async for row in db.orders.find({}, {"_id": 0, "status": 1}):
        order_statuses[row["status"]] = order_statuses.get(row["status"], 0) + 1
    paid_orders = await db.orders.find({"payment.status": {"$in": ["captured", "cash_on_delivery"]}}, {"_id": 0, "total": 1, "created_at": 1}).to_list(10000)
    revenue = sum(row["total"] for row in paid_orders)
    # Revenue for the last 7 days, oldest first, for the dashboard chart.
    today = datetime.now(timezone.utc).date()
    series_map = {(today - timedelta(days=offset)).isoformat(): 0 for offset in range(6, -1, -1)}
    for row in paid_orders:
        day = str(row.get("created_at", ""))[:10]
        if day in series_map:
            series_map[day] += row["total"]
    revenue_series = [{"label": datetime.fromisoformat(day).strftime("%d %b"), "value": value} for day, value in series_map.items()]
    # Top categories by published product count.
    category_counts: dict[str, int] = {}
    async for row in db.products.find({"active": True}, {"_id": 0, "category_slug": 1}):
        category_counts[row["category_slug"]] = category_counts.get(row["category_slug"], 0) + 1
    category_names = {row["slug"]: row["name"] for row in await db.categories.find({}, {"_id": 0, "slug": 1, "name": 1}).to_list(200)}
    top_categories = sorted(({"name": category_names.get(slug, slug.title()), "count": count} for slug, count in category_counts.items()), key=lambda entry: entry["count"], reverse=True)[:6]
    return Dashboard(metrics={"total_revenue": revenue, "total_orders": await db.orders.count_documents({}), "total_users": await db.users.count_documents({"role": "customer"}), "total_products": await db.products.count_documents({"active": True}), "total_auctions": await db.auctions.count_documents({}), "total_vendors": await db.admin_vendors.count_documents({})}, recent_orders=[Order(**row) for row in orders], order_statuses=order_statuses, activities=[{"title": "Live catalog connected", "detail": "Products, orders and auctions are using the secure API", "time": "Just now"}], top_categories=top_categories, revenue_series=revenue_series)


@api.get("/admin/products", response_model=ProductList)
async def admin_products(_: Annotated[dict[str, Any], Depends(admin_user)], page: int = 1, page_size: int = 50) -> ProductList:
    total = await db.products.count_documents({})
    rows = await db.products.find({}, {"_id": 0}).sort([("created_at", -1), ("id", 1)]).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return ProductList(items=[product_payload(row) for row in rows], page=page, page_size=page_size, total=total, pages=max(1, (total + page_size - 1) // page_size))


@api.post("/admin/products", response_model=Product, status_code=201)
async def create_product(input: ProductInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Product:
    if await db.products.find_one({"slug": input.slug}, {"_id": 0, "id": 1}):
        raise HTTPException(409, "A product with this slug already exists")
    if not await db.categories.find_one({"slug": input.category_slug, "active": True}, {"_id": 0, "id": 1}):
        raise HTTPException(422, "Category does not exist or is inactive")
    timestamp = now()
    product = {"id": str(uuid.uuid4()), **input.model_dump(), "created_at": timestamp, "updated_at": timestamp}
    await db.products.insert_one(product.copy())
    if product["active"]:
        announcement = {"id": str(uuid.uuid4()), "resource": "announcements", "title": f"New arrival: {product['name']}", "description": f"अब MobileCart पर ₹{product['price']:,} में उपलब्ध", "status": "published", "data": {"product_id": product["id"], "image_url": product["images"][0] if product["images"] else ""}, "created_at": timestamp, "updated_at": timestamp}
        await db.admin_announcements.insert_one(announcement.copy())
    return product_payload(product)


@api.patch("/admin/products/{product_id}", response_model=Product)
async def update_product(product_id: str, input: ProductInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Product:
    existing = await db.products.find_one({"id": product_id}, {"_id": 0})
    if not existing:
        raise HTTPException(404, "Product not found")
    duplicate = await db.products.find_one({"slug": input.slug, "id": {"$ne": product_id}}, {"_id": 0, "id": 1})
    if duplicate:
        raise HTTPException(409, "A product with this slug already exists")
    await db.products.update_one({"id": product_id}, {"$set": {**input.model_dump(), "updated_at": now()}})
    updated = await db.products.find_one({"id": product_id}, {"_id": 0})
    return product_payload(updated)


@api.delete("/admin/products/{product_id}", status_code=204)
async def delete_product(product_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    result = await db.products.update_one({"id": product_id}, {"$set": {"active": False, "updated_at": now()}})
    if result.modified_count == 0:
        raise HTTPException(404, "Product not found")
    return Response(status_code=204)


@api.post("/admin/categories", response_model=Category, status_code=201)
async def create_category(input: CategoryInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Category:
    if await db.categories.find_one({"slug": input.slug}, {"_id": 0, "id": 1}):
        raise HTTPException(409, "Category already exists")
    category = {"id": str(uuid.uuid4()), **input.model_dump()}
    await db.categories.insert_one(category.copy())
    return Category(**category)


@api.patch("/admin/orders/{order_id}/status", response_model=Order)
async def update_order_status(order_id: str, status: str = Query(pattern=r"^(confirmed|packed|shipped|delivered|cancelled)$"), tracking_number: str | None = None, _: Annotated[dict[str, Any], Depends(admin_user)] = None) -> Order:
    event = {"status": status.replace("_", " ").title(), "at": now()}
    update: dict[str, Any] = {"status": status, "updated_at": now(), "tracking.status": event["status"]}
    if tracking_number is not None:
        update["tracking.number"] = tracking_number
    result = await db.orders.update_one({"id": order_id}, {"$set": update, "$push": {"tracking.events": event}})
    if result.modified_count == 0:
        raise HTTPException(404, "Order not found")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return Order(**order)


@api.post("/admin/auctions", response_model=Auction, status_code=201)
async def create_auction(input: AuctionInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Auction:
    product = await db.products.find_one({"id": input.product_id}, {"_id": 0, "id": 1, "active": 1, "stock": 1})
    if not product:
        raise HTTPException(404, "Product not found")
    if not product.get("active") or int(product.get("stock", 0)) < 1:
        raise HTTPException(422, "Auction product must be active and in stock")
    if input.ends_at <= input.starts_at:
        raise HTTPException(422, "Auction end must be after start")
    auction = {"id": str(uuid.uuid4()), **input.model_dump(), "current_bid": input.starting_price, "bid_count": 0, "status": "upcoming" if input.starts_at > now() else "live", "winner_user_id": None}
    await db.auctions.insert_one(auction.copy())
    return await auction_payload(auction)


@api.post("/admin/auctions/{auction_id}/close", response_model=Auction)
async def close_auction(auction_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Auction:
    auction = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    if not auction:
        raise HTTPException(404, "Auction not found")
    winner = await db.bids.find_one({"auction_id": auction_id}, {"_id": 0}, sort=[("amount", -1), ("created_at", 1)])
    await db.auctions.update_one({"id": auction_id}, {"$set": {"status": "closed", "winner_user_id": winner["user_id"] if winner else None}})
    closed = await db.auctions.find_one({"id": auction_id}, {"_id": 0})
    return await auction_payload(closed)


@api.post("/admin/uploads", response_model=MediaFile, status_code=201)
async def upload_image(file: UploadFile = File(...), admin: Annotated[dict[str, Any], Depends(admin_user)] = None) -> MediaFile:
    allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if file.content_type not in allowed:
        raise HTTPException(415, "Only JPEG, PNG and WebP images are allowed")
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Image must be 5 MB or smaller")
    file_id = str(uuid.uuid4())
    path = f"mobilecart/uploads/{admin['id']}/{uuid.uuid4().hex}{allowed[file.content_type]}"
    try:
        stored = await asyncio.to_thread(put_object, path, content, file.content_type)
    except requests.RequestException as error:
        logger.exception("Media upload failed")
        raise HTTPException(502, "Image storage is temporarily unavailable") from error
    record = {"id": file_id, "storage_path": stored["path"], "original_filename": file.filename or "product-image", "content_type": file.content_type, "size": stored["size"], "is_deleted": False, "created_at": now()}
    await db.media_files.insert_one(record.copy())
    return MediaFile(id=file_id, url=f"/api/media/{file_id}", original_filename=record["original_filename"], content_type=record["content_type"], size=record["size"], created_at=record["created_at"])


@api.get("/media/{file_id}")
async def download_media(file_id: str) -> Response:
    record = await db.media_files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Image not found")
    if str(record.get("kind", "")).startswith("return_") or record.get("kind") == "payment_proof":
        raise HTTPException(403, "This private evidence is available to the assigned reviewer only")
    try:
        content, content_type = await asyncio.to_thread(get_object, record["storage_path"])
    except requests.RequestException as error:
        logger.exception("Media download failed")
        raise HTTPException(502, "Image is temporarily unavailable") from error
    return Response(content=content, media_type=record.get("content_type", content_type))


@api.get("/admin/media/{file_id}/content")
async def admin_download_private_media(file_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    record = await db.media_files.find_one({"id": file_id, "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Evidence not found")
    content, content_type = await asyncio.to_thread(get_object, record["storage_path"])
    return Response(content=content, media_type=record.get("content_type", content_type))


@api.get("/admin/media/{file_id}")
async def admin_download_media_compat(file_id: str, admin: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    return await admin_download_private_media(file_id, admin)


@api.delete("/admin/media/{file_id}", status_code=204)
async def remove_media(file_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    result = await db.media_files.update_one({"id": file_id, "is_deleted": False}, {"$set": {"is_deleted": True, "deleted_at": now()}})
    if result.modified_count == 0:
        raise HTTPException(404, "Image not found")
    return Response(status_code=204)


@api.get("/admin/wallets", response_model=list[WalletSummary])
async def admin_wallets(_: Annotated[dict[str, Any], Depends(admin_user)]) -> list[WalletSummary]:
    users = await db.users.find({"role": "customer"}, {"_id": 0, "id": 1, "name": 1, "email": 1, "created_at": 1}).sort("created_at", -1).to_list(500)
    rows: list[WalletSummary] = []
    for customer in users:
        wallet = await db.wallets.find_one({"user_id": customer["id"]}, {"_id": 0, "balance": 1, "updated_at": 1})
        rows.append(WalletSummary(user_id=customer["id"], user_name=customer["name"], user_email=customer["email"], balance=(wallet or {}).get("balance", 0), updated_at=(wallet or {}).get("updated_at", customer["created_at"])))
    return rows


@api.get("/admin/wallets/{user_id}/transactions", response_model=list[WalletTransaction])
async def admin_wallet_transactions(user_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> list[WalletTransaction]:
    rows = await db.wallet_transactions.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(100).to_list(100)
    return [WalletTransaction(**row) for row in rows]


@api.post("/admin/wallets/adjust", response_model=WalletSummary)
async def adjust_wallet(input: WalletAdjustmentInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> WalletSummary:
    customer = await db.users.find_one({"id": input.user_id, "role": "customer"}, {"_id": 0, "id": 1, "name": 1, "email": 1, "created_at": 1})
    if not customer:
        raise HTTPException(404, "Customer not found")
    timestamp = now()
    if input.kind == "credit":
        await db.wallets.update_one({"user_id": input.user_id}, {"$setOnInsert": {"user_id": input.user_id, "created_at": timestamp}, "$inc": {"balance": input.amount}, "$set": {"updated_at": timestamp}}, upsert=True)
    else:
        result = await db.wallets.update_one({"user_id": input.user_id, "balance": {"$gte": input.amount}}, {"$inc": {"balance": -input.amount}, "$set": {"updated_at": timestamp}})
        if result.modified_count == 0:
            raise HTTPException(409, "Customer wallet has insufficient balance")
    wallet = await db.wallets.find_one({"user_id": input.user_id}, {"_id": 0})
    transaction = {"id": str(uuid.uuid4()), "user_id": input.user_id, "kind": input.kind, "amount": input.amount, "balance_after": wallet["balance"], "note": input.note.strip(), "created_at": timestamp}
    await db.wallet_transactions.insert_one(transaction.copy())
    return WalletSummary(user_id=customer["id"], user_name=customer["name"], user_email=customer["email"], balance=wallet["balance"], updated_at=wallet["updated_at"])


def managed_collection(resource: str):
    if resource not in MANAGED_RESOURCES:
        raise HTTPException(404, "Admin section not found")
    return db[f"admin_{resource.replace('-', '_')}"]


def managed_payload(row: dict[str, Any]) -> ManagedRecord:
    return ManagedRecord(**clean(row.copy()))


@api.get("/admin/resources/{resource}", response_model=ManagedRecordList)
async def list_managed_records(resource: str, _: Annotated[dict[str, Any], Depends(admin_user)], page: int = Query(default=1, ge=1), page_size: int = Query(default=20, ge=1, le=100), query: str | None = None, status: str | None = None) -> ManagedRecordList:
    collection = managed_collection(resource)
    filter_query: dict[str, Any] = {}
    if status:
        filter_query["status"] = status
    if query:
        filter_query["$or"] = [{"title": {"$regex": re.escape(query), "$options": "i"}}, {"description": {"$regex": re.escape(query), "$options": "i"}}]
    total = await collection.count_documents(filter_query)
    rows = await collection.find(filter_query, {"_id": 0}).sort("updated_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return ManagedRecordList(items=[managed_payload(row) for row in rows], total=total, page=page, page_size=page_size)


@api.post("/admin/resources/{resource}", response_model=ManagedRecord, status_code=201)
async def create_managed_record(resource: str, input: ManagedRecordInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> ManagedRecord:
    collection = managed_collection(resource)
    timestamp = now()
    record = {"id": str(uuid.uuid4()), "resource": resource, **input.model_dump(), "created_at": timestamp, "updated_at": timestamp}
    await collection.insert_one(record.copy())
    return ManagedRecord(**record)


@api.patch("/admin/resources/{resource}/{record_id}", response_model=ManagedRecord)
async def update_managed_record(resource: str, record_id: str, input: ManagedRecordInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> ManagedRecord:
    collection = managed_collection(resource)
    result = await collection.update_one({"id": record_id}, {"$set": {**input.model_dump(), "updated_at": now()}})
    if result.modified_count == 0:
        if not await collection.find_one({"id": record_id}, {"_id": 0, "id": 1}):
            raise HTTPException(404, "Record not found")
    record = await collection.find_one({"id": record_id}, {"_id": 0})
    return managed_payload(record)


@api.delete("/admin/resources/{resource}/{record_id}", status_code=204)
async def delete_managed_record(resource: str, record_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    collection = managed_collection(resource)
    result = await collection.delete_one({"id": record_id})
    if result.deleted_count == 0:
        raise HTTPException(404, "Record not found")
    return Response(status_code=204)


@api.get("/content/{resource}", response_model=list[ManagedRecord])
async def public_content(resource: str) -> list[ManagedRecord]:
    if resource not in PUBLIC_RESOURCES:
        raise HTTPException(404, "Customer content section not found")
    collection = managed_collection(resource)
    rows = await collection.find({"status": {"$in": ["active", "published"]}}, {"_id": 0}).sort("updated_at", -1).to_list(100)
    return [managed_payload(row) for row in rows]


@api.get("/storefront", response_model=StorefrontConfig)
async def get_storefront() -> StorefrontConfig:
    document = await db.storefront_settings.find_one({"key": "homepage"}, {"_id": 0})
    return storefront_payload(document)


@api.get("/admin/storefront", response_model=StorefrontConfig)
async def get_admin_storefront(_: Annotated[dict[str, Any], Depends(admin_user)]) -> StorefrontConfig:
    document = await db.storefront_settings.find_one({"key": "homepage"}, {"_id": 0})
    return storefront_payload(document)


@api.put("/admin/storefront", response_model=StorefrontConfig)
async def update_storefront(input: StorefrontConfig, _: Annotated[dict[str, Any], Depends(admin_user)]) -> StorefrontConfig:
    normalized = storefront_payload(input.model_dump()).model_dump()
    update = {"key": "homepage", **normalized, "updated_at": now()}
    await db.storefront_settings.update_one({"key": "homepage"}, {"$set": update.copy()}, upsert=True)
    return StorefrontConfig(**normalized)


@api.get("/admin/categories", response_model=list[Category])
async def admin_categories(_: Annotated[dict[str, Any], Depends(admin_user)]) -> list[Category]:
    rows = await db.categories.find({}, {"_id": 0}).sort("name", 1).to_list(200)
    return [Category(**row) for row in rows]


@api.patch("/admin/categories/{category_id}", response_model=Category)
async def update_category(category_id: str, input: CategoryInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Category:
    duplicate = await db.categories.find_one({"slug": input.slug, "id": {"$ne": category_id}}, {"_id": 0, "id": 1})
    if duplicate:
        raise HTTPException(409, "Category already exists")
    result = await db.categories.update_one({"id": category_id}, {"$set": input.model_dump()})
    if result.modified_count == 0 and not await db.categories.find_one({"id": category_id}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Category not found")
    category = await db.categories.find_one({"id": category_id}, {"_id": 0})
    return Category(**category)


@api.delete("/admin/categories/{category_id}", status_code=204)
async def delete_category(category_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    result = await db.categories.update_one({"id": category_id}, {"$set": {"active": False}})
    if result.modified_count == 0:
        raise HTTPException(404, "Category not found")
    return Response(status_code=204)


@api.get("/admin/users", response_model=list[UserPublic])
async def list_users(_: Annotated[dict[str, Any], Depends(admin_user)], role: Literal["customer", "admin"] | None = None) -> list[UserPublic]:
    filter_query: dict[str, Any] = {"role": role} if role else {}
    rows = await db.users.find(filter_query, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [public_user(row) for row in rows]


@api.patch("/admin/users/{user_id}", response_model=UserPublic)
async def set_user_active(user_id: str, input: UserManagementUpdate, admin: Annotated[dict[str, Any], Depends(admin_user)]) -> UserPublic:
    if user_id == admin["id"] and not input.active:
        raise HTTPException(400, "You cannot deactivate your own account")
    result = await db.users.update_one({"id": user_id}, {"$set": {"active": input.active, "updated_at": now()}})
    if result.modified_count == 0 and not await db.users.find_one({"id": user_id}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "User not found")
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    return public_user(user)


@api.get("/admin/users/{user_id}/detail", response_model=AdminUserDetail)
async def admin_user_detail(user_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> AdminUserDetail:
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(404, "User not found")
    orders = await db.orders.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    returns = await db.returns.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(100)
    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0}) or {"user_id": user_id, "balance": 0, "updated_at": user.get("created_at", now())}
    return AdminUserDetail(user=public_user(user), orders=[Order(**row) for row in orders], returns=[managed_payload(row) for row in returns], wallet=WalletSummary(user_id=user["id"], user_name=user["name"], user_email=user["email"], balance=wallet["balance"], updated_at=wallet["updated_at"]))


@api.post("/admin/users", response_model=UserPublic, status_code=201)
async def create_admin_user(input: AdminUserCreate, _: Annotated[dict[str, Any], Depends(super_admin_user)]) -> UserPublic:
    email = str(input.email).lower()
    if await db.users.find_one({"email": email}, {"_id": 0, "id": 1}):
        raise HTTPException(409, "An account with this email already exists")
    user = {"id": str(uuid.uuid4()), "email": email, "name": input.name.strip(), "role": "admin", "admin_level": "standard", "active": True, "phone": None, "addresses": [], "password_hash": hash_password(input.password), "created_at": now()}
    await db.users.insert_one(user.copy())
    return public_user(user)


@api.get("/admin/payments", response_model=OrderList)
async def admin_payments(_: Annotated[dict[str, Any], Depends(admin_user)], page: int = Query(default=1, ge=1), page_size: int = Query(default=50, ge=1, le=100)) -> OrderList:
    total = await db.orders.count_documents({})
    rows = await db.orders.find({}, {"_id": 0}).sort("created_at", -1).skip((page - 1) * page_size).limit(page_size).to_list(page_size)
    return OrderList(items=[Order(**row) for row in rows], total=total)


@api.get("/admin/auctions", response_model=list[Auction])
async def admin_auctions(_: Annotated[dict[str, Any], Depends(admin_user)]) -> list[Auction]:
    rows = await db.auctions.find({}, {"_id": 0}).sort("ends_at", 1).to_list(500)
    return [await auction_payload(row) for row in rows]


@api.patch("/admin/payments/{order_id}", response_model=Order)
async def update_payment(order_id: str, input: PaymentUpdate, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Order:
    update: dict[str, Any] = {"payment.status": input.status, "updated_at": now()}
    if input.transaction_id:
        update["payment.transaction_id"] = input.transaction_id
    result = await db.orders.update_one({"id": order_id}, {"$set": update})
    if result.modified_count == 0 and not await db.orders.find_one({"id": order_id}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Order not found")
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return Order(**order)


@api.get("/admin/reports", response_model=Dashboard)
async def reports(user: Annotated[dict[str, Any], Depends(admin_user)]) -> Dashboard:
    return await dashboard(user)


@api.post("/returns", response_model=ManagedRecord, status_code=201)
async def create_return(input: ManagedRecordInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> ManagedRecord:
    order_id = str(input.data.get("order_id", ""))
    if not order_id or not await db.orders.find_one({"id": order_id, "user_id": user["id"]}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Your order was not found")
    timestamp = now()
    record = {"id": str(uuid.uuid4()), "resource": "returns", "user_id": user["id"], **input.model_dump(), "status": "requested", "created_at": timestamp, "updated_at": timestamp}
    await db.returns.insert_one(record.copy())
    return managed_payload(record)


@api.get("/returns", response_model=list[ManagedRecord])
async def customer_returns(user: Annotated[dict[str, Any], Depends(require_customer)]) -> list[ManagedRecord]:
    rows = await db.returns.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [managed_payload(row) for row in rows]


@api.get("/admin/returns", response_model=list[ManagedRecord])
async def admin_returns(_: Annotated[dict[str, Any], Depends(admin_user)]) -> list[ManagedRecord]:
    rows = await db.returns.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [managed_payload(row) for row in rows]


@api.patch("/admin/returns/{return_id}", response_model=ManagedRecord)
async def update_return(return_id: str, input: ManagedRecordInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> ManagedRecord:
    result = await db.returns.update_one({"id": return_id}, {"$set": {**input.model_dump(), "updated_at": now()}})
    if result.modified_count == 0 and not await db.returns.find_one({"id": return_id}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Return request not found")
    record = await db.returns.find_one({"id": return_id}, {"_id": 0})
    return managed_payload(record)


@api.post("/support/tickets", response_model=ManagedRecord, status_code=201)
async def create_ticket(input: ManagedRecordInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> ManagedRecord:
    timestamp = now()
    record = {"id": str(uuid.uuid4()), "resource": "support", "user_id": user["id"], **input.model_dump(), "status": "open", "created_at": timestamp, "updated_at": timestamp}
    await db.support_tickets.insert_one(record.copy())
    return managed_payload(record)


@api.get("/support/tickets", response_model=list[ManagedRecord])
async def customer_tickets(user: Annotated[dict[str, Any], Depends(require_customer)]) -> list[ManagedRecord]:
    rows = await db.support_tickets.find({"user_id": user["id"]}, {"_id": 0}).sort("created_at", -1).to_list(100)
    return [managed_payload(row) for row in rows]


@api.get("/admin/support-tickets", response_model=list[ManagedRecord])
async def admin_tickets(_: Annotated[dict[str, Any], Depends(admin_user)]) -> list[ManagedRecord]:
    rows = await db.support_tickets.find({}, {"_id": 0}).sort("created_at", -1).to_list(500)
    return [managed_payload(row) for row in rows]


@api.patch("/admin/support-tickets/{ticket_id}", response_model=ManagedRecord)
async def update_ticket(ticket_id: str, input: ManagedRecordInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> ManagedRecord:
    result = await db.support_tickets.update_one({"id": ticket_id}, {"$set": {**input.model_dump(), "updated_at": now()}})
    if result.modified_count == 0 and not await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0, "id": 1}):
        raise HTTPException(404, "Support ticket not found")
    record = await db.support_tickets.find_one({"id": ticket_id}, {"_id": 0})
    return managed_payload(record)


async def get_payment_settings() -> dict[str, Any]:
    doc = await db.app_settings.find_one({"id": "payment"}, {"_id": 0})
    if not doc:
        return {"id": "payment", **PaymentSettingsInput().model_dump()}
    merged = {**PaymentSettingsInput().model_dump(), **doc}
    return merged


def public_payment_config(settings: dict[str, Any]) -> dict[str, Any]:
    return {
        "key_id": settings.get("razorpay_key_id", "") if settings.get("razorpay_key_secret") else "",
        "mode": settings.get("mode", "test"),
        "configured": bool(settings.get("razorpay_key_id") and settings.get("razorpay_key_secret")),
        "methods": {
            "upi": settings.get("upi_enabled", True),
            "card": settings.get("card_enabled", True),
            "net_banking": settings.get("netbanking_enabled", True),
            "cod": settings.get("cod_enabled", True),
            "wallet": settings.get("wallet_enabled", True),
            "bank_transfer": settings.get("bank_transfer_enabled", True),
        },
        "upi_id_configured": bool(settings.get("upi_id")),
        "manual_transfer": {"account_name": settings.get("bank_account_name", ""), "account_number": settings.get("bank_account_number", ""), "ifsc_code": settings.get("bank_ifsc_code", ""), "upi_id": settings.get("upi_id", "")},
        "partial_payment_enabled": settings.get("partial_payment_enabled", False),
        "partial_payment_percent": settings.get("partial_payment_percent", 100),
    }


@api.get("/payment-config")
async def payment_config() -> dict[str, Any]:
    return public_payment_config(await get_payment_settings())


@api.get("/admin/payment-settings")
async def admin_get_payment_settings(_: Annotated[dict[str, Any], Depends(admin_user)]) -> dict[str, Any]:
    settings = await get_payment_settings()
    return {
        "razorpay_key_id": settings.get("razorpay_key_id", ""),
        "razorpay_key_secret_set": bool(settings.get("razorpay_key_secret")),
        "razorpay_webhook_secret_set": bool(settings.get("razorpay_webhook_secret")),
        "mode": settings.get("mode", "test"),
        "upi_enabled": settings.get("upi_enabled", True),
        "upi_id": settings.get("upi_id", ""),
        "card_enabled": settings.get("card_enabled", True),
        "netbanking_enabled": settings.get("netbanking_enabled", True),
        "cod_enabled": settings.get("cod_enabled", True),
        "wallet_enabled": settings.get("wallet_enabled", True),
        "bank_transfer_enabled": settings.get("bank_transfer_enabled", True),
        "bank_account_name": settings.get("bank_account_name", ""),
        "bank_account_number": settings.get("bank_account_number", ""),
        "bank_ifsc_code": settings.get("bank_ifsc_code", ""),
        "partial_payment_enabled": settings.get("partial_payment_enabled", False),
        "partial_payment_percent": settings.get("partial_payment_percent", 100),
    }


@api.put("/admin/payment-settings")
async def admin_save_payment_settings(input: PaymentSettingsInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> dict[str, Any]:
    existing = await get_payment_settings()
    payload = input.model_dump()
    payload["razorpay_key_secret"] = retained_payment_secret(payload["razorpay_key_secret"], existing.get("razorpay_key_secret", ""))
    payload["razorpay_webhook_secret"] = retained_payment_secret(payload["razorpay_webhook_secret"], existing.get("razorpay_webhook_secret", ""))
    payload["updated_at"] = now()
    await db.app_settings.update_one({"id": "payment"}, {"$set": {"id": "payment", **payload}}, upsert=True)
    saved = await get_payment_settings()
    return {
        "razorpay_key_id": saved.get("razorpay_key_id", ""),
        "razorpay_key_secret_set": bool(saved.get("razorpay_key_secret")),
        "razorpay_webhook_secret_set": bool(saved.get("razorpay_webhook_secret")),
        "mode": saved.get("mode", "test"),
        "upi_enabled": saved.get("upi_enabled", True),
        "upi_id": saved.get("upi_id", ""),
        "card_enabled": saved.get("card_enabled", True),
        "netbanking_enabled": saved.get("netbanking_enabled", True),
        "cod_enabled": saved.get("cod_enabled", True),
        "wallet_enabled": saved.get("wallet_enabled", True),
        "bank_transfer_enabled": saved.get("bank_transfer_enabled", True),
        "bank_account_name": saved.get("bank_account_name", ""),
        "bank_account_number": saved.get("bank_account_number", ""),
        "bank_ifsc_code": saved.get("bank_ifsc_code", ""),
        "partial_payment_enabled": saved.get("partial_payment_enabled", False),
        "partial_payment_percent": saved.get("partial_payment_percent", 100),
    }


@api.post("/payments/razorpay/order")
async def create_razorpay_order(input: RazorpayOrderInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> dict[str, Any]:
    order = await db.orders.find_one({"id": input.order_id, "user_id": user["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("payment", {}).get("status") != "pending" or order.get("status") != "payment_pending":
        raise HTTPException(409, "This order cannot be paid again")
    settings = await get_payment_settings()
    if not (settings.get("razorpay_key_id") and settings.get("razorpay_key_secret")):
        raise HTTPException(400, "Razorpay अभी configure नहीं हुआ है। Admin panel में keys डालें")
    payable = order["total"]
    if settings.get("partial_payment_enabled"):
        payable = max(1, round(order["total"] * settings.get("partial_payment_percent", 100) / 100))
    try:
        client = razorpay.Client(auth=(settings["razorpay_key_id"], settings["razorpay_key_secret"]))
        rz_order = await asyncio.to_thread(client.order.create, {"amount": payable * 100, "currency": "INR", "receipt": order["order_number"][:40], "payment_capture": 1})
    except Exception as error:
        logger.warning("Razorpay order creation failed: %s", error)
        raise HTTPException(502, "Razorpay credentials reject हो गए। Admin → Razorpay & Payments में same Test/Live mode की matching Key ID और Key Secret फिर से save करें।") from error
    await db.orders.update_one({"id": order["id"]}, {"$set": {"payment.provider_order_id": rz_order["id"], "payment.amount_due": payable, "updated_at": now()}})
    return {"razorpay_order_id": rz_order["id"], "key_id": settings["razorpay_key_id"], "amount": payable * 100, "currency": "INR", "order_number": order["order_number"], "name": user.get("name", ""), "email": user.get("email", "")}


@api.post("/payments/razorpay/verify", response_model=Order)
async def verify_razorpay_payment(input: RazorpayVerifyInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Order:
    order = await db.orders.find_one({"id": input.order_id, "user_id": user["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("payment", {}).get("provider_order_id") != input.razorpay_order_id:
        raise HTTPException(400, "Payment order mismatch")
    settings = await get_payment_settings()
    if not (settings.get("razorpay_key_id") and settings.get("razorpay_key_secret")):
        raise HTTPException(400, "Razorpay अभी configure नहीं हुआ है")
    client = razorpay.Client(auth=(settings["razorpay_key_id"], settings["razorpay_key_secret"]))
    try:
        client.utility.verify_payment_signature({"razorpay_order_id": input.razorpay_order_id, "razorpay_payment_id": input.razorpay_payment_id, "razorpay_signature": input.razorpay_signature})
    except Exception as error:
        logger.warning("Razorpay signature verification failed: %s", error)
        await db.orders.update_one({"id": order["id"]}, {"$set": {"payment.status": "failed", "updated_at": now()}})
        raise HTTPException(400, "Payment verification विफल रहा") from error
    await db.orders.update_one({"id": order["id"]}, {"$set": {"payment.status": "captured", "payment.transaction_id": input.razorpay_payment_id, "status": "confirmed", "updated_at": now()}})
    updated = await db.orders.find_one({"id": order["id"]}, {"_id": 0})
    return Order(**updated)


@api.post("/payments/razorpay/fail", response_model=Order)
async def fail_razorpay_payment(input: RazorpayFailureInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> Order:
    order = await db.orders.find_one({"id": input.order_id, "user_id": user["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    if order.get("payment", {}).get("status") != "pending":
        return Order(**order)
    timestamp = now()
    event = {"status": "Payment failed", "at": timestamp, "reason": input.reason[:120]}
    result = await db.orders.update_one(
        {"id": order["id"], "user_id": user["id"], "payment.status": "pending"},
        {"$set": {"payment.status": "failed", "payment.failure_reason": input.reason[:120], "status": "payment_failed", "updated_at": timestamp}, "$push": {"tracking.events": event}},
    )
    if result.modified_count:
        for item in order.get("items", []):
            await db.products.update_one({"id": item["product_id"]}, {"$inc": {"stock": int(item["quantity"])}, "$set": {"updated_at": timestamp}})
    updated = await db.orders.find_one({"id": order["id"]}, {"_id": 0})
    return Order(**updated)


@api.post("/payments/manual-proof", response_model=Order)
async def upload_manual_payment_proof(order_id: str = Query(min_length=1, max_length=80), payment_reference: str = Form(min_length=6, max_length=80), file: UploadFile = File(...), user: Annotated[dict[str, Any], Depends(require_customer)] = None) -> Order:
    allowed = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
    if file.content_type not in allowed:
        raise HTTPException(415, "Only JPEG, PNG and WebP payment screenshots are allowed")
    content = await file.read()
    if not content or len(content) > 5 * 1024 * 1024:
        raise HTTPException(413, "Payment screenshot must be 5 MB or smaller")
    order = await db.orders.find_one({"id": order_id, "user_id": user["id"]}, {"_id": 0})
    if not order or order.get("payment", {}).get("method") != "bank_transfer":
        raise HTTPException(404, "Manual payment order not found")
    if order.get("status") != "payment_proof_required":
        raise HTTPException(409, "Payment proof was already submitted")
    reference = payment_reference.strip().upper()
    if not re.fullmatch(r"[A-Z0-9._:/-]+", reference):
        raise HTTPException(422, "UPI reference number format is invalid")
    path = f"dmobilemart/payment-proofs/{user['id']}/{uuid.uuid4().hex}{allowed[file.content_type]}"
    try:
        stored = await asyncio.to_thread(put_object, path, content, file.content_type)
    except requests.RequestException as error:
        logger.exception("Payment proof upload failed")
        raise HTTPException(502, "Payment proof storage is temporarily unavailable") from error
    file_id = str(uuid.uuid4())
    record = {"id": file_id, "storage_path": stored["path"], "original_filename": file.filename or "payment-proof", "content_type": file.content_type, "size": stored["size"], "owner_id": user["id"], "order_id": order_id, "kind": "payment_proof", "is_deleted": False, "created_at": now()}
    await db.media_files.insert_one(record.copy())
    timestamp = now()
    await db.orders.update_one({"id": order_id, "user_id": user["id"]}, {"$set": {"status": "payment_review", "payment.status": "review_pending", "payment.proof_file_id": file_id, "payment.payment_reference": reference, "payment.transaction_id": reference, "updated_at": timestamp}, "$push": {"tracking.events": {"status": "UPI reference and payment proof submitted", "at": timestamp}}})
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return Order(**updated)


@api.get("/payments/manual-upi/{order_id}")
async def manual_upi_instructions(order_id: str, user: Annotated[dict[str, Any], Depends(require_customer)]) -> dict[str, Any]:
    order = await db.orders.find_one({"id": order_id, "user_id": user["id"], "payment.method": "bank_transfer"}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Personal UPI payment order not found")
    if order.get("status") != "payment_proof_required":
        raise HTTPException(409, "This UPI payment is already submitted for review")
    settings = await get_payment_settings()
    upi_id = settings.get("upi_id", "").strip()
    if not upi_id:
        raise HTTPException(422, "Personal UPI ID is not configured")
    merchant_name = settings.get("bank_account_name", "").strip() or "DMobileMart"
    params = {"pa": upi_id, "pn": merchant_name, "tr": order["payment"].get("manual_request_ref", f"UPI-{order['order_number']}"), "tn": f"DMobileMart order {order['order_number']}", "am": f"{order['total']:.2f}", "cu": "INR"}
    return {"order_id": order["id"], "order_number": order["order_number"], "amount": order["total"], "merchant_name": merchant_name, "merchant_upi_id": upi_id, "payment_request_ref": params["tr"], "upi_uri": f"upi://pay?{urlencode(params)}"}


@api.post("/returns/evidence")
async def upload_return_evidence(kind: Literal["photo", "video"], file: UploadFile = File(...), user: Annotated[dict[str, Any], Depends(require_customer)] = None) -> dict[str, Any]:
    allowed = {"photo": {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}, "video": {"video/mp4": ".mp4", "video/webm": ".webm", "video/quicktime": ".mov"}}
    if file.content_type not in allowed[kind]:
        raise HTTPException(415, "Unsupported return evidence format")
    content = await file.read()
    limit = 5 * 1024 * 1024 if kind == "photo" else 50 * 1024 * 1024
    if not content or len(content) > limit:
        raise HTTPException(413, "Photo must be under 5MB and video must be under 50MB")
    suffix = allowed[kind][file.content_type]
    path = f"dmobilemart/returns/{user['id']}/{uuid.uuid4().hex}{suffix}"
    stored = await asyncio.to_thread(put_object, path, content, file.content_type)
    file_id = str(uuid.uuid4())
    await db.media_files.insert_one({"id": file_id, "storage_path": stored["path"], "original_filename": file.filename or f"return-{kind}", "content_type": file.content_type, "size": stored["size"], "owner_id": user["id"], "kind": f"return_{kind}", "is_deleted": False, "created_at": now()})
    return {"id": file_id, "kind": kind, "filename": file.filename, "size": stored["size"]}


@api.post("/returns/claim", response_model=ManagedRecord)
async def create_return_claim(input: ReturnClaimInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> ManagedRecord:
    order = await db.orders.find_one({"id": input.order_id, "user_id": user["id"]}, {"_id": 0})
    if not order:
        raise HTTPException(404, "Order not found")
    eligible_items = [item for item in order.get("items", []) if int(item.get("warranty_days", 0)) > 0]
    if not eligible_items:
        raise HTTPException(409, "No warranty is available for this order")
    evidence = await db.media_files.find({"id": {"$in": [*input.photo_file_ids, input.video_file_id]}, "owner_id": user["id"], "is_deleted": False}, {"_id": 0, "id": 1, "kind": 1}).to_list(3)
    if len(evidence) != 3 or sum(row["kind"] == "return_photo" for row in evidence) != 2 or not any(row["kind"] == "return_video" for row in evidence):
        raise HTTPException(422, "Upload front photo, back photo and one-minute device video first")
    record = {"id": str(uuid.uuid4()), "resource": "returns", "title": f"Warranty return: {order['order_number']}", "description": input.detail, "status": "pending_admin_review", "data": {"order_id": order["id"], "reason": input.reason, "photo_file_ids": input.photo_file_ids, "video_file_id": input.video_file_id, "eligible_items": [item["name"] for item in eligible_items], "admin_reason": ""}, "user_id": user["id"], "created_at": now(), "updated_at": now()}
    await db.returns.insert_one(record.copy())
    return managed_payload(record)


@api.post("/admin/returns/{return_id}/decision", response_model=ManagedRecord)
async def decide_return_claim(return_id: str, input: ReturnDecisionInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> ManagedRecord:
    status = "approved" if input.decision == "approve" else "disapproved"
    updated = await db.returns.find_one_and_update({"id": return_id, "status": "pending_admin_review"}, {"$set": {"status": status, "data.admin_reason": input.reason, "updated_at": now()}}, return_document=True, projection={"_id": 0})
    if not updated:
        raise HTTPException(409, "Return is not awaiting review")
    return managed_payload(updated)


async def customer_chat_thread(user: dict[str, Any]) -> dict[str, Any]:
    thread = await db.chat_threads.find_one({"user_id": user["id"]}, {"_id": 0})
    if thread:
        return thread
    thread = {"id": str(uuid.uuid4()), "user_id": user["id"], "user_name": user["name"], "user_email": user["email"], "status": "open", "updated_at": now(), "created_at": now()}
    await db.chat_threads.insert_one(thread.copy())
    return thread


@api.get("/chat/thread")
async def get_customer_chat(user: Annotated[dict[str, Any], Depends(require_customer)]) -> dict[str, Any]:
    thread = await customer_chat_thread(user)
    messages = await db.chat_messages.find({"thread_id": thread["id"]}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return {"thread": thread, "messages": [ChatMessage(**message) for message in messages]}


@api.post("/chat/messages", response_model=ChatMessage)
async def send_customer_chat(input: ChatMessageInput, user: Annotated[dict[str, Any], Depends(require_customer)]) -> ChatMessage:
    thread = await customer_chat_thread(user)
    message = {"id": str(uuid.uuid4()), "thread_id": thread["id"], "sender_role": "customer", "sender_name": user["name"], "message": input.message.strip(), "read_by_admin": False, "created_at": now()}
    await db.chat_messages.insert_one(message.copy())
    await db.chat_threads.update_one({"id": thread["id"]}, {"$set": {"updated_at": message["created_at"], "status": "open"}})
    return ChatMessage(**message)


@api.get("/admin/chats")
async def list_admin_chats(_: Annotated[dict[str, Any], Depends(admin_user)]) -> list[dict[str, Any]]:
    threads = await db.chat_threads.find({}, {"_id": 0}).sort("updated_at", -1).to_list(200)
    for thread in threads:
        thread["unread_customer"] = await db.chat_messages.count_documents({"thread_id": thread["id"], "sender_role": "customer", "read_by_admin": {"$ne": True}})
    return threads


@api.get("/admin/chats/{thread_id}")
async def get_admin_chat(thread_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> dict[str, Any]:
    thread = await db.chat_threads.find_one({"id": thread_id}, {"_id": 0})
    if not thread:
        raise HTTPException(404, "Chat thread not found")
    await db.chat_messages.update_many({"thread_id": thread_id, "sender_role": "customer", "read_by_admin": {"$ne": True}}, {"$set": {"read_by_admin": True}})
    messages = await db.chat_messages.find({"thread_id": thread_id}, {"_id": 0}).sort("created_at", 1).to_list(200)
    return {"thread": thread, "messages": [ChatMessage(**message) for message in messages]}


@api.post("/admin/chats/{thread_id}/messages", response_model=ChatMessage)
async def send_admin_chat(thread_id: str, input: ChatMessageInput, admin: Annotated[dict[str, Any], Depends(admin_user)]) -> ChatMessage:
    thread = await db.chat_threads.find_one({"id": thread_id}, {"_id": 0})
    if not thread:
        raise HTTPException(404, "Chat thread not found")
    message = {"id": str(uuid.uuid4()), "thread_id": thread_id, "sender_role": "admin", "sender_name": admin["name"], "message": input.message.strip(), "created_at": now()}
    await db.chat_messages.insert_one(message.copy())
    await db.chat_threads.update_one({"id": thread_id}, {"$set": {"updated_at": message["created_at"]}})
    return ChatMessage(**message)


@api.get("/admin/orders/{order_id}/payment-proof")
async def admin_payment_proof(order_id: str, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Response:
    record = await db.media_files.find_one({"order_id": order_id, "kind": "payment_proof", "is_deleted": False}, {"_id": 0})
    if not record:
        raise HTTPException(404, "Payment screenshot not found")
    try:
        content, content_type = await asyncio.to_thread(get_object, record["storage_path"])
    except requests.RequestException as error:
        raise HTTPException(502, "Payment screenshot is temporarily unavailable") from error
    return Response(content=content, media_type=record.get("content_type", content_type))


@api.post("/admin/orders/{order_id}/payment-review", response_model=Order)
async def review_manual_payment(order_id: str, input: ManualPaymentReviewInput, _: Annotated[dict[str, Any], Depends(admin_user)]) -> Order:
    order = await db.orders.find_one({"id": order_id}, {"_id": 0})
    if not order or order.get("payment", {}).get("method") != "bank_transfer":
        raise HTTPException(404, "Manual payment order not found")
    if order.get("payment", {}).get("status") != "review_pending":
        raise HTTPException(409, "This payment is not awaiting review")
    timestamp = now()
    if input.action == "capture":
        update = {"$set": {"status": "confirmed", "payment.status": "captured", "payment.transaction_id": f"MANUAL-{order['order_number']}", "payment.review_note": input.note.strip(), "updated_at": timestamp}, "$push": {"tracking.events": {"status": "Payment captured by admin", "at": timestamp}}}
    else:
        update = {"$set": {"status": "payment_failed", "payment.status": "failed", "payment.review_note": input.note.strip(), "updated_at": timestamp}, "$push": {"tracking.events": {"status": "Payment rejected by admin", "at": timestamp, "reason": input.note.strip()}}}
    result = await db.orders.update_one({"id": order_id, "payment.status": "review_pending"}, update)
    if not result.modified_count:
        raise HTTPException(409, "Payment review was already completed")
    if input.action == "reject":
        for item in order.get("items", []):
            await db.products.update_one({"id": item["product_id"]}, {"$inc": {"stock": int(item["quantity"])}, "$set": {"updated_at": timestamp}})
    updated = await db.orders.find_one({"id": order_id}, {"_id": 0})
    return Order(**updated)


app.include_router(api)
app.add_middleware(SessionMiddleware, secret_key=JWT_SECRET, same_site="lax", https_only=True)
app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted({FRONTEND_URL.rstrip("/"), *GOOGLE_ALLOWED_ORIGINS}),
    allow_origin_regex=r"^https://[a-z0-9-]+\.preview\.emergentagent\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["Content-Type", "Authorization"],
)