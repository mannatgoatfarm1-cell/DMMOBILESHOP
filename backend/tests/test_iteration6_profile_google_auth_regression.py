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
def session() -> requests.Session:
    return requests.Session()


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


# Login/session coverage for provided customer credential
def test_customer_login_sets_secure_httponly_cookie_and_me_stable(session):
    login = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "p0check_1790113956@example.com", "password": "TestPass123!"},
        timeout=30,
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["email"] == "p0check_1790113956@example.com"
    cookie_header = login.headers.get("set-cookie", "")
    assert "HttpOnly" in cookie_header
    assert "Secure" in cookie_header

    me_1 = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert me_1.status_code == 200
    me_2 = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert me_2.status_code == 200
    assert me_1.json()["id"] == me_2.json()["id"]
    assert me_2.json()["email"] == "p0check_1790113956@example.com"


# Seeded admin credential baseline for post-auth changes
def test_admin_login_still_works(session):
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200
    assert response.json()["role"] == "admin"


# Google exchange hardening for invalid authorization code
def test_google_invalid_code_rejected_with_401(session):
    response = session.post(
        f"{BASE_URL}/api/auth/google",
        json={
            "code": "invalid_google_code_12345",
            "redirect_uri": "https://dashboard-design-20.preview.emergentagent.com/auth/google",
        },
        timeout=30,
    )
    assert response.status_code == 401
    assert "could not be completed" in response.json().get("detail", "").lower()


# CORS credential support required for browser auth preflight
def test_auth_preflight_allows_preview_origin_with_credentials(session):
    origin = "https://dashboard-design-20.preview.emergentagent.com"
    response = session.options(
        f"{BASE_URL}/api/auth/login",
        headers={
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code in (200, 204)
    assert response.headers.get("access-control-allow-origin") == origin
    assert response.headers.get("access-control-allow-credentials") == "true"


# Brute-force lockout protection after five failed attempts
def test_lockout_triggers_after_five_failed_attempts(session):
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


# Password hash format check for seeded admin account
def test_seeded_admin_hash_has_bcrypt_2b_prefix(mongo_db):
    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak and deepak.get("password_hash")
    assert str(deepak["password_hash"]).startswith("$2b$")
