import os
import uuid
from pathlib import Path

import pytest
import requests
from pymongo import MongoClient


def _backend_env_value(key: str) -> str | None:
    value = os.environ.get(key)
    if value:
        return value
    backend_env = Path("/app/backend/.env")
    if backend_env.exists():
        for line in backend_env.read_text().splitlines():
            if line.startswith(f"{key}="):
                parsed = line.split("=", 1)[1].strip().strip('"').strip("'")
                if parsed:
                    return parsed
    return None


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


# Auth module: customer seeded credential login reliability + secure cookies.
def test_customer_login_reliably_succeeds_multiple_times(base_url: str):
    for _ in range(3):
        session = requests.Session()
        response = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "p0check_1790113956@example.com", "password": "TestPass123!"},
            timeout=30,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["email"] == "p0check_1790113956@example.com"
        assert data["role"] == "customer"

        set_cookie = response.headers.get("set-cookie", "")
        assert "access_token=" in set_cookie
        assert "refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie

        me_response = session.get(f"{base_url}/api/auth/me", timeout=30)
        assert me_response.status_code == 200, me_response.text
        me_data = me_response.json()
        assert me_data["email"] == "p0check_1790113956@example.com"


# Auth/admin module: seeded admin login works and can reach admin dashboard API.
def test_admin_login_and_dashboard_access(base_url: str):
    session = requests.Session()
    login = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert login.status_code == 200, login.text
    payload = login.json()
    assert payload["role"] == "admin"
    assert payload["email"] == "deepak143@mobilecart.com"

    dashboard = session.get(f"{base_url}/api/admin/dashboard", timeout=30)
    assert dashboard.status_code == 200, dashboard.text
    metrics = dashboard.json().get("metrics", {})
    assert isinstance(metrics, dict)
    assert "total_users" in metrics


# Auth security module: lockout persists for wrong password, valid password bypasses stale lockout.
def test_lockout_then_correct_password_succeeds_and_clears_attempts(base_url: str, mongo_db):
    session = requests.Session()
    email = f"test_iter10_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"

    register = session.post(
        f"{base_url}/api/auth/register",
        json={"name": "TEST Iter10 Lock", "email": email, "password": password, "confirm_password": password},
        timeout=30,
    )
    assert register.status_code == 201, register.text

    # Ensure clean auth state before lockout checks.
    session.post(f"{base_url}/api/auth/logout", timeout=30)

    for _ in range(5):
        bad = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": email, "password": "WrongPass!999"},
            timeout=30,
        )
        assert bad.status_code == 401, bad.text

    wrong_while_locked = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": email, "password": "WrongPass!999"},
        timeout=30,
    )
    assert wrong_while_locked.status_code == 429, wrong_while_locked.text
    assert "too many sign-in attempts" in wrong_while_locked.json().get("detail", "").lower()

    good_while_locked = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": email, "password": password},
        timeout=30,
    )
    assert good_while_locked.status_code == 200, good_while_locked.text
    assert good_while_locked.json()["email"] == email

    attempt_record = mongo_db.login_attempts.find_one({"identifier": email})
    assert attempt_record is None

    wrong_after_success = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": email, "password": "WrongPass!999"},
        timeout=30,
    )
    assert wrong_after_success.status_code == 401, wrong_after_success.text

    # Cleanup test user and residual attempt if present.
    mongo_db.users.delete_one({"email": email})
    mongo_db.login_attempts.delete_one({"identifier": email})


# CORS module: explicit preview origin should be echoed for credentialed auth requests.
def test_auth_preflight_origin_header_is_explicit(base_url: str):
    response = requests.options(
        f"{base_url}/api/auth/login",
        headers={
            "Origin": "https://dashboard-design-20.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.headers.get("access-control-allow-origin") == "https://dashboard-design-20.preview.emergentagent.com"
    assert response.headers.get("access-control-allow-credentials") == "true"
