import base64
import os
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
    mongo_url = os.environ.get("MONGO_URL")
    db_name = os.environ.get("DB_NAME")
    if not mongo_url or not db_name:
        backend_env = Path("/app/backend/.env")
        if backend_env.exists():
            for line in backend_env.read_text().splitlines():
                if line.startswith("MONGO_URL=") and not mongo_url:
                    mongo_url = line.split("=", 1)[1].strip().strip('"').strip("'")
                if line.startswith("DB_NAME=") and not db_name:
                    db_name = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME unavailable")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        db = client[db_name]
        db.command("ping")
        yield db
    finally:
        client.close()


# Auth coverage: login cookies, lockout, bcrypt format, and CORS preflight
def test_auth_controls_and_playbook_basics(mongo_db):
    session = requests.Session()
    login = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert login.status_code == 200
    assert login.json()["role"] == "admin"
    assert "HttpOnly" in login.headers.get("set-cookie", "")

    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak and str(deepak["password_hash"]).startswith("$2b$")

    preflight = session.options(
        f"{BASE_URL}/api/auth/login",
        headers={
            "Origin": "https://dashboard-design-20.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert preflight.status_code in (200, 204)
    assert preflight.headers.get("access-control-allow-credentials") == "true"


# Auth brute-force lockout behavior for customer account
def test_auth_lockout_after_five_failed_attempts():
    session = requests.Session()
    email = f"test_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"
    register = session.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "name": "TEST Lockout",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        timeout=30,
    )
    assert register.status_code == 201

    session.post(f"{BASE_URL}/api/auth/logout", timeout=30)
    for _ in range(5):
        wrong = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"identifier": email, "password": "WrongPass!999"},
            timeout=30,
        )
        assert wrong.status_code == 401

    locked = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": email, "password": password},
        timeout=30,
    )
    assert locked.status_code == 429


# Product manager + upload/media flow used by admin product editor
def test_admin_product_listing_and_upload_media_is_public(admin_session):
    products = admin_session.get(f"{BASE_URL}/api/admin/products?page_size=5", timeout=30)
    assert products.status_code == 200
    assert len(products.json()["items"]) >= 1

    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO8l0J8AAAAASUVORK5CYII="
    )
    upload = admin_session.post(
        f"{BASE_URL}/api/admin/uploads",
        files={"file": ("tiny.png", png_bytes, "image/png")},
        timeout=60,
    )
    assert upload.status_code == 201, upload.text
    media = upload.json()
    assert media["url"].startswith("/api/media/")

    media_get = admin_session.get(f"{BASE_URL}{media['url']}", timeout=30)
    assert media_get.status_code == 200
    assert media_get.headers.get("content-type", "").startswith("image/")


# Resource managers coverage for renderable lists across all requested sections
def test_admin_resource_sections_load(admin_session):
    resources = [
        "banners",
        "campaigns",
        "coupons",
        "vendors",
        "brands",
        "subscriptions",
        "app-manager",
        "notifications",
        "shipping",
        "gst-tax",
        "settings",
    ]
    for resource in resources:
        response = admin_session.get(f"{BASE_URL}/api/admin/resources/{resource}?page_size=20", timeout=30)
        assert response.status_code == 200, f"{resource} failed"
        payload = response.json()
        assert isinstance(payload.get("items"), list)


# Operations managers load checks: categories/users/orders/payments/auctions/returns/support/admin-users
def test_admin_operations_sections_load(admin_session):
    endpoints = [
        "/api/admin/categories",
        "/api/admin/users",
        "/api/orders",
        "/api/admin/payments",
        "/api/admin/auctions",
        "/api/admin/returns",
        "/api/admin/support-tickets",
        "/api/admin/users?role=admin",
    ]
    for endpoint in endpoints:
        response = admin_session.get(f"{BASE_URL}{endpoint}", timeout=30)
        assert response.status_code == 200, f"{endpoint} failed"


# Wallet manager flow: credit then debit and verify ledger + balance changes
def test_wallet_credit_debit_and_ledger_updates(admin_session):
    wallets = admin_session.get(f"{BASE_URL}/api/admin/wallets", timeout=30)
    assert wallets.status_code == 200
    rows = wallets.json()
    target = next((w for w in rows if w["user_email"] == "p0check_1790113956@example.com"), None)
    assert target is not None
    starting_balance = target["balance"]

    marker = uuid.uuid4().hex[:8]
    credit = admin_session.post(
        f"{BASE_URL}/api/admin/wallets/adjust",
        json={
            "user_id": target["user_id"],
            "amount": 21,
            "kind": "credit",
            "note": f"TEST credit {marker}",
        },
        timeout=30,
    )
    assert credit.status_code == 200
    assert credit.json()["balance"] == starting_balance + 21

    debit = admin_session.post(
        f"{BASE_URL}/api/admin/wallets/adjust",
        json={
            "user_id": target["user_id"],
            "amount": 21,
            "kind": "debit",
            "note": f"TEST debit {marker}",
        },
        timeout=30,
    )
    assert debit.status_code == 200
    assert debit.json()["balance"] == starting_balance

    ledger = admin_session.get(f"{BASE_URL}/api/admin/wallets/{target['user_id']}/transactions", timeout=30)
    assert ledger.status_code == 200
    notes = [row["note"] for row in ledger.json()]
    assert any(f"TEST credit {marker}" == note for note in notes)
    assert any(f"TEST debit {marker}" == note for note in notes)


# Customer account wallet card and coupon validation
def test_customer_wallet_and_coupon_validation(customer_session):
    wallet = customer_session.get(f"{BASE_URL}/api/wallet", timeout=30)
    assert wallet.status_code == 200
    assert isinstance(wallet.json().get("balance"), int)

    coupon = customer_session.post(
        f"{BASE_URL}/api/coupons/validate",
        json={"code": "WELCOME10", "subtotal": 2500},
        timeout=30,
    )
    assert coupon.status_code == 200
    payload = coupon.json()
    assert payload["code"] == "WELCOME10"
    assert payload["discount"] > 0


# Wallet payment should block insufficient balance during order placement
def test_wallet_payment_rejects_insufficient_balance(customer_session):
    me = customer_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert me.status_code == 200
    addresses = me.json().get("addresses", [])
    if not addresses:
        add_address = customer_session.post(
            f"{BASE_URL}/api/auth/me/addresses",
            json={
                "label": "TEST_WALLET",
                "recipient_name": "Wallet Test",
                "phone": "+919999999999",
                "line1": "Wallet Street 1",
                "line2": "",
                "city": "Delhi",
                "state": "Delhi",
                "postal_code": "110001",
                "country": "India",
            },
            timeout=30,
        )
        assert add_address.status_code == 201
        address_id = add_address.json()["id"]
    else:
        address_id = addresses[0]["id"]

    products = customer_session.get(f"{BASE_URL}/api/products?sort=price_desc&page_size=1", timeout=30)
    assert products.status_code == 200
    expensive = products.json()["items"][0]

    add_cart = customer_session.post(
        f"{BASE_URL}/api/cart/items",
        json={"product_id": expensive["id"], "quantity": 1},
        timeout=30,
    )
    assert add_cart.status_code == 200

    wallet_order = customer_session.post(
        f"{BASE_URL}/api/orders",
        json={"address_id": address_id, "payment_method": "wallet"},
        timeout=30,
    )
    assert wallet_order.status_code == 409
    assert "insufficient" in wallet_order.json().get("detail", "").lower()
