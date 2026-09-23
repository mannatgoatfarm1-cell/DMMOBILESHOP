import os
import time
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


def _base_url() -> str:
    env_url = os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")

    frontend_env = Path("/app/frontend/.env")
    if frontend_env.exists():
        for line in frontend_env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value.rstrip("/")

    raise RuntimeError("REACT_APP_BACKEND_URL is required")


def _backend_env_value(key: str) -> str | None:
    value = os.environ.get(key)
    if value:
        return value
    backend_env = Path("/app/backend/.env")
    if backend_env.exists():
        for line in backend_env.read_text().splitlines():
            if line.startswith(f"{key}="):
                found = line.split("=", 1)[1].strip().strip('"').strip("'")
                if found:
                    return found
    return None


BASE_URL = _base_url()


@pytest.fixture
def admin_session() -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return session


@pytest.fixture
def customer_session() -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "p0check_1790113956@example.com", "password": "TestPass123!"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return session


@pytest.fixture
def mongo_db():
    mongo_url = _backend_env_value("MONGO_URL")
    db_name = _backend_env_value("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME unavailable")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        db = client[db_name]
        db.command("ping")
        yield db
    finally:
        client.close()


# Auth controls: httpOnly cookies, seeded admin, lockout, bcrypt, and CORS preflight.
def test_auth_playbook_core_controls(customer_session, mongo_db):
    me = customer_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert me.status_code == 200
    assert me.json()["email"] == "p0check_1790113956@example.com"

    fresh_login = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert fresh_login.status_code == 200
    assert fresh_login.json()["role"] == "admin"
    cookie_header = fresh_login.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header

    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak and str(deepak["password_hash"]).startswith("$2b$")


# Brute-force lockout protection should apply after five bad attempts.
def test_auth_lockout_after_five_failures():
    session = requests.Session()
    email = f"test_lock_iter7_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"

    register = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "TEST Iter7 Lockout", "email": email, "password": password, "confirm_password": password},
        timeout=30,
    )
    assert register.status_code == 201

    session.post(f"{BASE_URL}/api/auth/logout", timeout=30)
    for _ in range(5):
        bad_login = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"identifier": email, "password": "WrongPass!999"},
            timeout=30,
        )
        assert bad_login.status_code == 401

    locked = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": email, "password": password},
        timeout=30,
    )
    assert locked.status_code == 429


# CORS preflight must allow credentialed auth requests from preview origin.
def test_auth_preflight_allows_preview_origin():
    response = requests.options(
        f"{BASE_URL}/api/auth/login",
        headers={
            "Origin": "https://dashboard-design-20.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == "https://dashboard-design-20.preview.emergentagent.com"
    assert response.headers.get("access-control-allow-credentials") == "true"


# Admin sections backing APIs for Products, Orders, Wallet, Banners, Coupons, and Settings.
def test_admin_core_sections_api_load(admin_session):
    endpoints = [
        "/api/admin/products?page_size=20",
        "/api/orders?page_size=20",
        "/api/admin/wallets",
        "/api/admin/resources/banners?page_size=20",
        "/api/admin/resources/coupons?page_size=20",
        "/api/admin/resources/settings?page_size=20",
    ]
    for endpoint in endpoints:
        response = admin_session.get(f"{BASE_URL}{endpoint}", timeout=30)
        assert response.status_code == 200, f"{endpoint}: {response.status_code}"


# Live publish flow should surface new active product on public API and allow cleanup.
def test_admin_product_publish_visible_on_public_api_and_cleanup(admin_session):
    marker = uuid.uuid4().hex[:8]
    slug = f"test-live-sync-{marker}"
    payload = {
        "name": f"TEST Live Sync {marker}",
        "slug": slug,
        "sub": "Iter7 live sync test",
        "description": "Temporary product for live sync verification",
        "category_slug": "mobiles",
        "price": 12345,
        "original_price": 15999,
        "stock": 5,
        "images": [
            "https://static.prod-images.emergentagent.com/jobs/4d8ba7d6-4cc2-48fd-a329-88470c3b0d75/images/29f5c8a586dbdda9921a2bd753139bccf4cd74c5f0004bb94e7b3148cb72b303.jpeg"
        ],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
    }

    created = admin_session.post(f"{BASE_URL}/api/admin/products", json=payload, timeout=30)
    assert created.status_code == 201, created.text
    created_data = created.json()
    assert created_data["slug"] == slug
    product_id = created_data["id"]

    try:
        found = False
        query_text = f"TEST Live Sync {marker}"
        for _ in range(5):
            public_list = requests.get(f"{BASE_URL}/api/products?query={query_text}&page_size=50", timeout=30)
            assert public_list.status_code == 200
            items = public_list.json().get("items", [])
            if any(item["id"] == product_id and item["slug"] == slug for item in items):
                found = True
                break
            time.sleep(4)
        assert found

        public_detail = requests.get(f"{BASE_URL}/api/products/{product_id}", timeout=30)
        assert public_detail.status_code == 200
        assert public_detail.json()["slug"] == slug
    finally:
        admin_session.delete(f"{BASE_URL}/api/admin/products/{product_id}", timeout=30)

    after_delete = requests.get(f"{BASE_URL}/api/products/{product_id}", timeout=30)
    assert after_delete.status_code == 404


# Favicon and PWA files should be wired and publicly retrievable with MobileCart manifest values.
def test_favicon_and_manifest_assets_served_and_mobilecart_metadata_present():
    for path in ["/favicon.ico", "/favicon-16x16.png", "/favicon-32x32.png", "/apple-touch-icon.png", "/manifest.json"]:
        response = requests.get(f"{BASE_URL}{path}", timeout=30)
        assert response.status_code == 200, f"{path}: {response.status_code}"

    manifest = requests.get(f"{BASE_URL}/manifest.json", timeout=30)
    assert manifest.status_code == 200
    payload = manifest.json()
    assert payload.get("short_name") == "MobileCart"
    assert "MobileCart" in payload.get("name", "")
    icons = payload.get("icons", [])
    sizes = {icon.get("sizes") for icon in icons}
    assert "192x192" in sizes
    assert "512x512" in sizes
