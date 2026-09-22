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


@pytest.fixture
def session() -> requests.Session:
    s = requests.Session()
    return s


@pytest.fixture
def mongo_db():
    mongo_url = _backend_env_value("MONGO_URL")
    db_name = _backend_env_value("DB_NAME")
    if not mongo_url or not db_name:
        pytest.skip("MONGO_URL/DB_NAME unavailable for token/hash verification")

    client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
    try:
        db = client[db_name]
        db.command("ping")
        yield db
    finally:
        client.close()


# Auth login + cookie security + admin credential acceptance
def test_admin_username_login_and_secure_cookies(session):
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data.get("email")

    cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header


# Customer registration validation (confirm password mismatch)
def test_registration_rejects_mismatched_confirm_password(session):
    payload = {
        "name": "TEST Confirm Mismatch",
        "email": f"test_mismatch_{uuid.uuid4().hex[:8]}@example.com",
        "password": "TestPass123!",
        "confirm_password": "DifferentPass123!",
    }
    response = session.post(f"{BASE_URL}/api/auth/register", json=payload, timeout=30)
    assert response.status_code == 422
    assert "Passwords do not match" in response.json().get("detail", "")


# Customer login baseline using provided credential
def test_customer_login_with_provided_credential(session):
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "p0check_1790113956@example.com", "password": "TestPass123!"},
        timeout=30,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "customer"
    assert data["email"] == "p0check_1790113956@example.com"


# Forgot-password account-enumeration resistance
def test_forgot_password_response_is_uniform(session):
    known = session.post(
        f"{BASE_URL}/api/auth/forgot-password",
        json={"identifier": "deepak143"},
        timeout=30,
    )
    unknown = session.post(
        f"{BASE_URL}/api/auth/forgot-password",
        json={"identifier": f"ghost_{uuid.uuid4().hex[:10]}"},
        timeout=30,
    )

    assert known.status_code == 200
    assert unknown.status_code == 200
    assert known.json() == unknown.json()
    assert "If this account exists" in known.json().get("message", "")


# Forgot/reset one-time token behavior via DB-backed token capture
def test_password_reset_token_is_one_time_use(session, mongo_db):
    identifier = "deepak143"
    forgot = session.post(
        f"{BASE_URL}/api/auth/forgot-password",
        json={"identifier": identifier},
        timeout=30,
    )
    assert forgot.status_code == 200

    user = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "id": 1})
    assert user and user.get("id")

    token_doc = mongo_db.password_reset_tokens.find_one(
        {"user_id": user["id"], "used": False},
        sort=[("expires_at", -1)],
    )
    assert token_doc and token_doc.get("token")
    reset_token = token_doc["token"]

    new_password = f"ResetPass!{uuid.uuid4().hex[:8]}"
    first_reset = session.post(
        f"{BASE_URL}/api/auth/reset-password",
        json={"token": reset_token, "new_password": new_password, "confirm_password": new_password},
        timeout=30,
    )
    assert first_reset.status_code == 200
    assert first_reset.json()["role"] == "admin"

    reused = session.post(
        f"{BASE_URL}/api/auth/reset-password",
        json={"token": reset_token, "new_password": "AnotherPass123!", "confirm_password": "AnotherPass123!"},
        timeout=30,
    )
    assert reused.status_code == 400
    assert "invalid or has expired" in reused.json().get("detail", "")

    restore = session.post(
        f"{BASE_URL}/api/auth/forgot-password",
        json={"identifier": identifier},
        timeout=30,
    )
    assert restore.status_code == 200
    restore_doc = mongo_db.password_reset_tokens.find_one(
        {"user_id": user["id"], "used": False},
        sort=[("expires_at", -1)],
    )
    assert restore_doc and restore_doc.get("token")
    restore_reset = session.post(
        f"{BASE_URL}/api/auth/reset-password",
        json={"token": restore_doc["token"], "new_password": "deepak143", "confirm_password": "deepak143"},
        timeout=30,
    )
    assert restore_reset.status_code == 200


# Brute-force lockout policy after five failed attempts
def test_bruteforce_lockout_after_five_failures(session):
    email = f"test_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"

    register = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "TEST Lockout", "email": email, "password": password, "confirm_password": password},
        timeout=30,
    )
    assert register.status_code == 201

    session.post(f"{BASE_URL}/api/auth/logout", timeout=30)

    for _ in range(5):
        wrong = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"identifier": email, "password": "wrong-password"},
            timeout=30,
        )
        assert wrong.status_code == 401

    locked = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": email, "password": password},
        timeout=30,
    )
    assert locked.status_code == 429


# CORS policy for credentialed auth requests
def test_cors_allows_credentials_for_explicit_origin(session):
    frontend_origin = "https://dashboard-design-20.preview.emergentagent.com"
    response = session.options(
        f"{BASE_URL}/api/auth/login",
        headers={
            "Origin": frontend_origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == frontend_origin
    assert response.headers.get("access-control-allow-credentials") == "true"


# bcrypt hash format validation for seeded admin account
def test_seeded_admin_hash_uses_bcrypt_2b_prefix(mongo_db):
    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak and deepak.get("password_hash")
    assert str(deepak["password_hash"]).startswith("$2b$")
