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


# Auth module: login cookies + seeded admin hash quality.
def test_auth_login_sets_http_only_cookies_and_seeded_admin_hash(mongo_db):
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"

    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie

    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak and str(deepak["password_hash"]).startswith("$2b$")


# Auth security module: brute-force lockout after five failed attempts.
def test_auth_lockout_after_five_failures_then_429():
    session = requests.Session()
    email = f"test_iter8_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"

    register = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "TEST Iter8 Lock", "email": email, "password": password, "confirm_password": password},
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


# CORS module: preview preflight should allow credentialed auth requests.
def test_auth_preflight_allows_preview_origin_with_credentials():
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


# Google auth module: invalid redirect URI must be rejected explicitly.
def test_google_auth_rejects_invalid_redirect_uri(admin_session):
    response = admin_session.post(
        f"{BASE_URL}/api/auth/google",
        json={"code": "test_invalid_code_12345678", "redirect_uri": "https://evil.example.com/auth/google"},
        timeout=30,
    )
    assert response.status_code == 400
    assert "redirect" in response.json().get("detail", "").lower()


# Catalog module: admin publish must become public within 2 seconds.
def test_admin_publish_visible_on_public_products_within_two_seconds(admin_session):
    marker = uuid.uuid4().hex[:8]
    slug = f"test-live-2s-{marker}"
    payload = {
        "name": f"TEST Live Two Seconds {marker}",
        "slug": slug,
        "sub": "Iter8 SLA check",
        "description": "Temporary record for 2-second publish check",
        "category_slug": "mobiles",
        "price": 12345,
        "original_price": 12999,
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
    product = created.json()
    assert product["slug"] == slug
    product_id = product["id"]

    try:
        deadline = time.time() + 2.0
        found = False
        while time.time() < deadline:
            listing = requests.get(f"{BASE_URL}/api/products?query={payload['name']}&page_size=100", timeout=30)
            assert listing.status_code == 200
            items = listing.json().get("items", [])
            if any(item["id"] == product_id for item in items):
                found = True
                break
            time.sleep(0.25)
        assert found

        detail = requests.get(f"{BASE_URL}/api/products/{product_id}", timeout=30)
        assert detail.status_code == 200
        assert detail.json()["slug"] == slug
    finally:
        admin_session.delete(f"{BASE_URL}/api/admin/products/{product_id}", timeout=30)
