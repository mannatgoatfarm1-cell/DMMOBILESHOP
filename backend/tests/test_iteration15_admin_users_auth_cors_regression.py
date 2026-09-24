import os
import uuid
from pathlib import Path

import pytest
import requests


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
ADMIN_IDENTIFIER = "deepak143"
ADMIN_PASSWORD = "deepak143"
CUSTOMER_EMAIL = "p0check_1790113956@example.com"
CUSTOMER_PASSWORD = "TestPass123!"
PREVIEW_ORIGIN = BASE_URL
APP_LOCAL_URL = "http://localhost:8001"


# Auth/user/admin helpers for lockout, CORS, and user-management checks.
def _login_session(identifier: str, password: str) -> tuple[requests.Session, requests.Response]:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": identifier, "password": password},
        timeout=30,
    )
    return session, response


def _register_customer(prefix: str = "iter15") -> dict:
    uniq = uuid.uuid4().hex[:10]
    email = f"{prefix}_{uniq}@example.com"
    password = "TestPass123!"
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "name": f"TEST {prefix} {uniq}",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        timeout=30,
    )
    assert response.status_code == 201, response.text
    user = response.json()
    return {"session": session, "email": email, "password": password, "user": user}


@pytest.fixture
def admin_session() -> requests.Session:
    session, response = _login_session(ADMIN_IDENTIFIER, ADMIN_PASSWORD)
    assert response.status_code == 200, response.text
    return session


@pytest.fixture
def customer_session() -> requests.Session:
    session, response = _login_session(CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
    assert response.status_code == 200, response.text
    return session


class TestAuthLockoutAndCors:
    # Auth lockout policy and credentialed CORS preflight checks.

    def test_login_sets_http_only_auth_cookies(self):
        _, response = _login_session(CUSTOMER_EMAIL, CUSTOMER_PASSWORD)
        assert response.status_code == 200, response.text
        set_cookie = response.headers.get("set-cookie", "").lower()
        assert "access_token=" in set_cookie
        assert "refresh_token=" in set_cookie
        assert "httponly" in set_cookie

    def test_five_failed_attempts_then_valid_returns_429(self):
        account = _register_customer(prefix="lockout")
        identifier = account["email"]
        attacker = requests.Session()

        for _ in range(5):
            failed = attacker.post(
                f"{BASE_URL}/api/auth/login",
                json={"identifier": identifier, "password": "WrongPass123!"},
                timeout=30,
            )
            assert failed.status_code == 401, failed.text

        blocked = attacker.post(
            f"{BASE_URL}/api/auth/login",
            json={"identifier": identifier, "password": account["password"]},
            timeout=30,
        )
        assert blocked.status_code == 429, blocked.text

    def test_auth_preflight_layer_identification_public_vs_app_local(self):
        headers = {
            "Origin": PREVIEW_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        }

        public_preflight = requests.options(f"{BASE_URL}/api/auth/login", headers=headers, timeout=30)
        app_preflight = requests.options(f"{APP_LOCAL_URL}/api/auth/login", headers=headers, timeout=30)

        assert app_preflight.status_code in [200, 204], (
            f"App-local preflight failed unexpectedly: {app_preflight.status_code} {app_preflight.text}"
        )
        assert app_preflight.headers.get("access-control-allow-credentials") == "true"
        assert app_preflight.headers.get("access-control-allow-origin") == PREVIEW_ORIGIN

        assert public_preflight.status_code in [200, 204], (
            "Gateway/ingress preflight failure: "
            f"public={public_preflight.status_code} body={public_preflight.text}; "
            f"app_local={app_preflight.status_code}."
        )
        assert public_preflight.headers.get("access-control-allow-credentials") == "true"
        assert public_preflight.headers.get("access-control-allow-origin") == PREVIEW_ORIGIN


class TestAdminUsersAndAuthorization:
    # Admin users list/detail/status controls and non-admin authorization checks.

    def test_admin_users_list_includes_active_flag(self, admin_session: requests.Session):
        response = admin_session.get(f"{BASE_URL}/api/admin/users", timeout=30)
        assert response.status_code == 200, response.text
        rows = response.json()
        assert isinstance(rows, list)
        assert rows, "No users returned"
        sample = rows[0]
        assert "active" in sample
        assert isinstance(sample["active"], bool)

    def test_admin_user_detail_returns_authorized_shape_no_sensitive_fields(self, admin_session: requests.Session):
        users = admin_session.get(f"{BASE_URL}/api/admin/users", timeout=30)
        assert users.status_code == 200, users.text
        target = users.json()[0]

        detail = admin_session.get(f"{BASE_URL}/api/admin/users/{target['id']}/detail", timeout=30)
        assert detail.status_code == 200, detail.text
        payload = detail.json()

        assert set(payload.keys()) == {"user", "orders", "returns", "wallet"}
        assert isinstance(payload["user"], dict)
        assert isinstance(payload["orders"], list)
        assert isinstance(payload["returns"], list)
        assert isinstance(payload["wallet"], dict)

        assert "password_hash" not in payload["user"]
        assert "access_token" not in payload["user"]
        assert "refresh_token" not in payload["user"]

        wallet = payload["wallet"]
        assert wallet["user_id"] == payload["user"]["id"]
        assert isinstance(wallet["balance"], int)

        if payload["orders"]:
            order = payload["orders"][0]
            assert "tracking" in order
            assert isinstance(order["tracking"], dict)

    def test_admin_can_suspend_activate_disposable_customer_and_restore(self, admin_session: requests.Session):
        account = _register_customer(prefix="suspend")
        user = account["user"]
        user_id = user["id"]

        try:
            suspended = admin_session.patch(
                f"{BASE_URL}/api/admin/users/{user_id}",
                json={"active": False},
                timeout=30,
            )
            assert suspended.status_code == 200, suspended.text
            assert suspended.json()["active"] is False

            blocked = account["session"].get(f"{BASE_URL}/api/orders?page_size=5", timeout=30)
            assert blocked.status_code == 401, blocked.text

            blocked_login = requests.post(
                f"{BASE_URL}/api/auth/login",
                json={"identifier": account["email"], "password": account["password"]},
                timeout=30,
            )
            assert blocked_login.status_code == 403, blocked_login.text
        finally:
            restore = admin_session.patch(
                f"{BASE_URL}/api/admin/users/{user_id}",
                json={"active": True},
                timeout=30,
            )
            assert restore.status_code == 200, restore.text
            assert restore.json()["active"] is True

    def test_non_admin_cannot_get_other_user_detail_or_patch_activation(
        self, customer_session: requests.Session, admin_session: requests.Session
    ):
        users = admin_session.get(f"{BASE_URL}/api/admin/users", timeout=30)
        assert users.status_code == 200, users.text
        target = next((row for row in users.json() if row.get("email", "").lower() != CUSTOMER_EMAIL.lower()), None)
        assert target is not None, "No secondary target user available for non-admin check"

        detail_blocked = customer_session.get(
            f"{BASE_URL}/api/admin/users/{target['id']}/detail",
            timeout=30,
        )
        assert detail_blocked.status_code == 403, detail_blocked.text

        patch_blocked = customer_session.patch(
            f"{BASE_URL}/api/admin/users/{target['id']}",
            json={"active": False},
            timeout=30,
        )
        assert patch_blocked.status_code == 403, patch_blocked.text


class TestOrderRegressionQuickChecks:
    # Customer/admin order endpoints needed for this iteration regression.

    def test_customer_orders_detail_invoice_still_work(self, customer_session: requests.Session):
        listed = customer_session.get(f"{BASE_URL}/api/orders?page_size=100", timeout=30)
        assert listed.status_code == 200, listed.text
        rows = listed.json().get("items", [])
        assert isinstance(rows, list)
        assert rows, "No existing customer order available for regression"

        order = rows[0]
        detail = customer_session.get(f"{BASE_URL}/api/orders/{order['id']}", timeout=30)
        assert detail.status_code == 200, detail.text
        detail_body = detail.json()
        assert detail_body["id"] == order["id"]
        assert isinstance(detail_body.get("items"), list)

        invoice = customer_session.get(f"{BASE_URL}/api/orders/{order['id']}/invoice", timeout=30)
        assert invoice.status_code == 200, invoice.text
        assert invoice.headers.get("content-type", "").startswith("application/pdf")
        assert len(invoice.content) > 500

    def test_admin_order_status_update_endpoint_still_works(self, admin_session: requests.Session):
        listed = admin_session.get(f"{BASE_URL}/api/orders?page_size=50", timeout=30)
        assert listed.status_code == 200, listed.text
        rows = listed.json().get("items", [])
        assert rows, "No orders available for admin status regression"

        order = rows[0]
        order_id = order["id"]
        original_status = order["status"]
        original_tracking = (order.get("tracking") or {}).get("number", "")
        next_status = "packed" if original_status != "packed" else "confirmed"
        marker = f"I15-{uuid.uuid4().hex[:8]}"

        try:
            updated = admin_session.patch(
                f"{BASE_URL}/api/admin/orders/{order_id}/status",
                params={"status": next_status, "tracking_number": marker},
                timeout=30,
            )
            assert updated.status_code == 200, updated.text
            body = updated.json()
            assert body["status"] == next_status
            assert body.get("tracking", {}).get("number") == marker
        finally:
            restore = admin_session.patch(
                f"{BASE_URL}/api/admin/orders/{order_id}/status",
                params={"status": original_status, "tracking_number": original_tracking},
                timeout=30,
            )
            assert restore.status_code == 200, restore.text


class TestBcryptHashFormat:
    # Bcrypt storage format check for newly registered credentials.

    def test_new_user_password_hash_prefix_is_2b(self):
        pymongo = pytest.importorskip("pymongo")
        from dotenv import dotenv_values

        backend_env = dotenv_values("/app/backend/.env")
        mongo_url = backend_env.get("MONGO_URL")
        db_name = backend_env.get("DB_NAME")
        if not mongo_url or not db_name:
            pytest.skip("Mongo env values unavailable for hash format validation")

        account = _register_customer(prefix="hashfmt")
        email = account["email"]

        client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        try:
            user = client[db_name].users.find_one({"email": email})
            assert user and isinstance(user.get("password_hash"), str)
            assert user["password_hash"].startswith("$2b$")
        finally:
            client.close()