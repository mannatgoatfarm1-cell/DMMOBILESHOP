import os
import uuid
from pathlib import Path

import pytest
import requests


# Auth hardening module: cookies/CORS/lockout assertions
def test_admin_login_sets_httponly_cookies(base_url: str):
    session = requests.Session()
    login = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert login.status_code == 200, login.text
    set_cookie = login.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie


def test_auth_preflight_allows_origin_with_credentials(base_url: str):
    preflight = requests.options(
        f"{base_url}/api/auth/login",
        headers={
            "Origin": "https://dashboard-design-20.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert preflight.status_code in [200, 204], preflight.text
    assert preflight.headers.get("access-control-allow-credentials") == "true"
    assert preflight.headers.get("access-control-allow-origin") == "https://dashboard-design-20.preview.emergentagent.com"


def test_bruteforce_lockout_after_five_failures(base_url: str):
    marker = uuid.uuid4().hex[:8]
    email = f"test_lock_iter13_{marker}@example.com"
    password = "Passw0rd!234"
    session = requests.Session()

    register = session.post(
        f"{base_url}/api/auth/register",
        json={
            "name": f"TEST Lock {marker}",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        timeout=30,
    )
    assert register.status_code == 201, register.text
    session.post(f"{base_url}/api/auth/logout", timeout=30)

    for _ in range(5):
        wrong = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": email, "password": "WrongPass!999"},
            timeout=30,
        )
        assert wrong.status_code == 401, wrong.text

    locked = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": email, "password": "WrongPass!999"},
        timeout=30,
    )
    assert locked.status_code == 429, locked.text


def test_seeded_admin_hash_uses_bcrypt_prefix_2b():
    pytest.importorskip("pymongo")
    from pymongo import MongoClient

    backend_env = Path("/app/backend/.env")
    values = {}
    for line in backend_env.read_text().splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')

    mongo_url = values.get("MONGO_URL")
    db_name = values.get("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME missing in backend/.env")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        admin = client[db_name].users.find_one({"username": "deepak143"})
        assert admin is not None
        password_hash = admin.get("password_hash", "")
        assert isinstance(password_hash, str)
        assert password_hash.startswith("$2b$")
    finally:
        client.close()


# QC product persistence module: admin create/update and customer read verification
def test_product_qc_create_update_and_customer_visibility(base_url: str, admin_session):
    marker = uuid.uuid4().hex[:8]
    slug = f"test-qc-iter13-{marker}"
    payload = {
        "name": f"TEST QC Iter13 {marker}",
        "slug": slug,
        "sub": "Disposable QC test",
        "description": "Temporary QC persistence test",
        "category_slug": "mobiles",
        "price": 12000,
        "original_price": 15000,
        "stock": 4,
        "images": ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=400&q=60"],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
        "qc_grade": "good",
        "qc_status": {
            "Screen": "pass",
            "Battery": "fail",
            "Buttons": "unknown",
        },
    }
    created_id = None

    try:
        created = admin_session.post(f"{base_url}/api/admin/products", json=payload, timeout=30)
        assert created.status_code == 201, created.text
        created_data = created.json()
        created_id = created_data["id"]
        assert created_data["qc_grade"] == "good"
        assert created_data["qc_status"]["Screen"] == "pass"
        assert created_data["qc_status"]["Battery"] == "fail"

        customer_get = admin_session.get(f"{base_url}/api/products/{slug}?_live={uuid.uuid4().hex}", timeout=30)
        assert customer_get.status_code == 200, customer_get.text
        customer_data = customer_get.json()
        assert customer_data["slug"] == slug
        assert customer_data["qc_grade"] == "good"
        assert customer_data["qc_status"]["Battery"] == "fail"

        update_payload = {
            **payload,
            "qc_grade": "excellent",
            "qc_status": {"Screen": "pass", "Battery": "pass", "Buttons": "pass"},
        }
        updated = admin_session.patch(
            f"{base_url}/api/admin/products/{created_id}", json=update_payload, timeout=30
        )
        assert updated.status_code == 200, updated.text
        updated_data = updated.json()
        assert updated_data["qc_grade"] == "excellent"
        assert updated_data["qc_status"]["Battery"] == "pass"

        customer_get_after = admin_session.get(
            f"{base_url}/api/products/{slug}?_live={uuid.uuid4().hex}", timeout=30
        )
        assert customer_get_after.status_code == 200, customer_get_after.text
        customer_data_after = customer_get_after.json()
        assert customer_data_after["qc_grade"] == "excellent"
        assert customer_data_after["qc_status"]["Buttons"] == "pass"
    finally:
        if created_id:
            admin_session.delete(f"{base_url}/api/admin/products/{created_id}", timeout=30)


# Payment settings module: persistence/validation/no-secret-leak assertions
def test_payment_settings_upi_validation_persistence_and_restore(base_url: str, admin_session):
    current = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert current.status_code == 200, current.text
    baseline = current.json()

    original_upi = baseline.get("upi_id", "")
    disposable_upi = f"iter13{uuid.uuid4().hex[:6]}@okicici"

    valid_payload = {
        "razorpay_key_id": baseline.get("razorpay_key_id", ""),
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": baseline.get("mode", "test"),
        "upi_enabled": baseline.get("upi_enabled", True),
        "upi_id": disposable_upi,
        "card_enabled": baseline.get("card_enabled", True),
        "netbanking_enabled": baseline.get("netbanking_enabled", True),
        "cod_enabled": baseline.get("cod_enabled", True),
        "wallet_enabled": baseline.get("wallet_enabled", True),
        "partial_payment_enabled": baseline.get("partial_payment_enabled", False),
        "partial_payment_percent": baseline.get("partial_payment_percent", 100),
    }
    restore_payload = {**valid_payload, "upi_id": original_upi}

    try:
        saved_valid = admin_session.put(
            f"{base_url}/api/admin/payment-settings", json=valid_payload, timeout=30
        )
        assert saved_valid.status_code == 200, saved_valid.text
        valid_data = saved_valid.json()
        assert valid_data["upi_id"] == disposable_upi
        assert "razorpay_key_secret" not in valid_data
        assert "razorpay_webhook_secret" not in valid_data
        assert isinstance(valid_data.get("razorpay_key_secret_set"), bool)
        assert isinstance(valid_data.get("razorpay_webhook_secret_set"), bool)

        get_after_valid = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
        assert get_after_valid.status_code == 200, get_after_valid.text
        assert get_after_valid.json().get("upi_id") == disposable_upi

        invalid_payload = {**valid_payload, "upi_id": "invalid upi"}
        invalid = admin_session.put(
            f"{base_url}/api/admin/payment-settings", json=invalid_payload, timeout=30
        )
        assert invalid.status_code == 422, invalid.text

        get_after_invalid = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
        assert get_after_invalid.status_code == 200, get_after_invalid.text
        assert get_after_invalid.json().get("upi_id") == disposable_upi

        public_cfg = admin_session.get(f"{base_url}/api/payment-config", timeout=30)
        assert public_cfg.status_code == 200, public_cfg.text
        public_data = public_cfg.json()
        assert "razorpay_key_secret" not in public_data
        assert "razorpay_webhook_secret" not in public_data
        assert "upi_id" not in public_data
        assert isinstance(public_data.get("configured"), bool)
    finally:
        restore = admin_session.put(
            f"{base_url}/api/admin/payment-settings", json=restore_payload, timeout=30
        )
        assert restore.status_code == 200, restore.text
        restored = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
        assert restored.status_code == 200, restored.text
        assert restored.json().get("upi_id", "") == original_upi


def test_seed_admin_update_logic_present_in_source():
    source = Path("/app/backend/server.py").read_text()
    assert 'await db.users.update_one({"username": "deepak143"}, {"$set": {"password_hash": hash_password("deepak143")' in source
