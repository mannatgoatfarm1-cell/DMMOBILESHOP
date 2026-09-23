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


# Auth module: seeded admin sign-in and session cookie security.
def test_admin_login_sets_http_only_cookies_and_returns_admin_role(mongo_db):
    response = requests.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["role"] == "admin"
    assert payload["email"] == "deepak143@mobilecart.com"

    set_cookie = response.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie

    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak and str(deepak["password_hash"]).startswith("$2b$")


# Auth security module: brute-force lockout threshold validation.
def test_lockout_after_five_failed_signins():
    session = requests.Session()
    email = f"test_iter9_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"

    register = session.post(
        f"{BASE_URL}/api/auth/register",
        json={"name": "TEST Iter9 Lock", "email": email, "password": password, "confirm_password": password},
        timeout=30,
    )
    assert register.status_code == 201, register.text

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


# Google OAuth module: valid redirect + invalid authorization code must never 500.
def test_google_exchange_invalid_code_returns_401_not_500():
    response = requests.post(
        f"{BASE_URL}/api/auth/google",
        json={
            "code": "invalid_google_code_for_regression_12345678",
            "redirect_uri": "https://dashboard-design-20.preview.emergentagent.com/auth/google",
        },
        timeout=30,
    )
    assert response.status_code == 401, response.text
    detail = response.json().get("detail", "")
    assert "google sign-in" in detail.lower()


# Google OAuth module: unsafe redirect URI must be rejected.
def test_google_exchange_rejects_unapproved_redirect_uri():
    response = requests.post(
        f"{BASE_URL}/api/auth/google",
        json={
            "code": "invalid_google_code_for_redirect_guard_12345678",
            "redirect_uri": "https://evil.example.com/auth/google",
        },
        timeout=30,
    )
    assert response.status_code == 400
    assert "redirect" in response.json().get("detail", "").lower()


# CORS module: credentialed preview-origin preflight for auth endpoint.
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
