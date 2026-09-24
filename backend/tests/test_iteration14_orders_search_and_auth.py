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


# Auth + customer/admin session modules for order and invoice regression coverage
@pytest.fixture
def admin_session() -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": ADMIN_IDENTIFIER, "password": ADMIN_PASSWORD},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return session


@pytest.fixture
def customer_session() -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{BASE_URL}/api/auth/login",
        json={"identifier": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return session


def _ensure_customer_address(session: requests.Session) -> str:
    me = session.get(f"{BASE_URL}/api/auth/me", timeout=30)
    assert me.status_code == 200, me.text
    payload = me.json()
    addresses = payload.get("addresses", [])
    if addresses:
        return addresses[0]["id"]

    address_payload = {
        "label": "HOME",
        "recipient_name": "TEST Customer",
        "phone": "+919900001234",
        "line1": "Test Lane 12",
        "line2": "",
        "city": "New Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
    }
    created = session.post(f"{BASE_URL}/api/auth/me/addresses", json=address_payload, timeout=30)
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _get_available_order_method(session: requests.Session) -> str:
    response = session.get(f"{BASE_URL}/api/payment-config", timeout=30)
    assert response.status_code == 200, response.text
    methods = (response.json() or {}).get("methods", {})
    for candidate in ["cod", "upi", "card", "net_banking"]:
        if methods.get(candidate, True):
            return candidate
    pytest.skip("No supported non-wallet payment method enabled for order creation")


def _ensure_customer_order(session: requests.Session) -> dict:
    listed = session.get(f"{BASE_URL}/api/orders?page_size=100", timeout=30)
    assert listed.status_code == 200, listed.text
    rows = listed.json().get("items", [])
    if rows:
        return rows[0]

    products = session.get(f"{BASE_URL}/api/products?page_size=50", timeout=30)
    assert products.status_code == 200, products.text
    items = products.json().get("items", [])
    assert items, "No product found for order seed"
    selected_product_id = None
    last_error = ""
    for product in items:
        if int(product.get("stock", 0)) < 1:
            continue
        candidate_id = product["id"]
        add_cart = session.post(
            f"{BASE_URL}/api/cart/items",
            json={"product_id": candidate_id, "quantity": 1},
            timeout=30,
        )
        if add_cart.status_code == 200:
            selected_product_id = candidate_id
            break
        last_error = add_cart.text
    assert selected_product_id, f"Unable to add any in-stock product to cart: {last_error}"

    address_id = _ensure_customer_address(session)
    method = _get_available_order_method(session)
    created = session.post(
        f"{BASE_URL}/api/orders",
        json={"address_id": address_id, "payment_method": method},
        timeout=30,
    )
    assert created.status_code == 201, created.text
    return created.json()


def _register_and_login_temp_customer() -> requests.Session:
    session = requests.Session()
    uniq = uuid.uuid4().hex[:10]
    email = f"test_ord_owner_{uniq}@example.com"
    password = "TestPass123!"
    response = session.post(
        f"{BASE_URL}/api/auth/register",
        json={
            "name": f"TEST Owner {uniq}",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        timeout=30,
    )
    assert response.status_code == 201, response.text
    return session


class TestSearchOrderInvoiceAndAdminFlow:
    # Storefront search + orders/invoice/admin fulfilment regression suite

    def test_storefront_search_exact_result_stable(self):
        first = requests.get(f"{BASE_URL}/api/products?query=IPHONE%20XR&page_size=50", timeout=30)
        assert first.status_code == 200, first.text
        first_items = first.json()["items"]

        import time
        time.sleep(3.2)

        second = requests.get(f"{BASE_URL}/api/products?query=IPHONE%20XR&page_size=50", timeout=30)
        assert second.status_code == 200, second.text
        second_items = second.json()["items"]

        first_names = [item.get("name", "") for item in first_items]
        second_names = [item.get("name", "") for item in second_items]

        assert all("iphone xr" in name.lower() for name in first_names), first_names
        assert first_names == second_names

    def test_customer_orders_list_and_detail(self, customer_session: requests.Session):
        order = _ensure_customer_order(customer_session)

        listed = customer_session.get(f"{BASE_URL}/api/orders?page_size=100", timeout=30)
        assert listed.status_code == 200, listed.text
        payload = listed.json()
        assert isinstance(payload.get("items"), list)
        assert any(row["id"] == order["id"] for row in payload["items"])

        detail = customer_session.get(f"{BASE_URL}/api/orders/{order['id']}", timeout=30)
        assert detail.status_code == 200, detail.text
        body = detail.json()
        assert body["user_id"] == order["user_id"]
        assert isinstance(body.get("items"), list) and len(body["items"]) >= 1
        assert isinstance(body.get("tracking", {}).get("events", []), list)
        assert body.get("delivery_address", {}).get("recipient_name")
        assert body.get("payment", {}).get("status")

    def test_invoice_owner_and_admin_access_and_non_owner_blocked(
        self, customer_session: requests.Session, admin_session: requests.Session
    ):
        order = _ensure_customer_order(customer_session)

        owner_invoice = customer_session.get(f"{BASE_URL}/api/orders/{order['id']}/invoice", timeout=30)
        assert owner_invoice.status_code == 200, owner_invoice.text
        assert owner_invoice.headers.get("content-type", "").startswith("application/pdf")
        assert "Content-Disposition" in owner_invoice.headers
        assert len(owner_invoice.content) > 500

        admin_invoice = admin_session.get(f"{BASE_URL}/api/orders/{order['id']}/invoice", timeout=30)
        assert admin_invoice.status_code == 200, admin_invoice.text
        assert admin_invoice.headers.get("content-type", "").startswith("application/pdf")
        assert len(admin_invoice.content) > 500

        unrelated_customer = _register_and_login_temp_customer()
        blocked = unrelated_customer.get(f"{BASE_URL}/api/orders/{order['id']}/invoice", timeout=30)
        assert blocked.status_code == 404, blocked.text

    def test_admin_can_update_status_and_timeline_and_restore(self, admin_session: requests.Session):
        all_orders = admin_session.get(f"{BASE_URL}/api/orders?page_size=100", timeout=30)
        assert all_orders.status_code == 200, all_orders.text
        rows = all_orders.json().get("items", [])
        assert rows, "No existing order available for admin fulfilment test"
        order = rows[0]
        order_id = order["id"]
        original_status = order["status"]
        original_tracking = (order.get("tracking") or {}).get("number", "")

        valid_states = ["confirmed", "packed", "shipped", "delivered", "cancelled"]
        next_status = next((state for state in valid_states if state != original_status), "packed")
        marker = f"TST-{uuid.uuid4().hex[:8]}"

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
            events = body.get("tracking", {}).get("events", [])
            assert any(event.get("status", "").lower() == next_status.replace("_", " ") for event in events)
        finally:
            admin_session.patch(
                f"{BASE_URL}/api/admin/orders/{order_id}/status",
                params={"status": original_status, "tracking_number": original_tracking},
                timeout=30,
            )

    def test_order_status_api_rejects_invalid_status(self, admin_session: requests.Session):
        all_orders = admin_session.get(f"{BASE_URL}/api/orders?page_size=100", timeout=30)
        assert all_orders.status_code == 200, all_orders.text
        order_id = all_orders.json()["items"][0]["id"]

        invalid = admin_session.patch(
            f"{BASE_URL}/api/admin/orders/{order_id}/status",
            params={"status": "invalid_state"},
            timeout=30,
        )
        assert invalid.status_code == 422, invalid.text

    def test_order_status_api_blocks_non_admin(self, customer_session: requests.Session):
        own_order = _ensure_customer_order(customer_session)
        blocked = customer_session.patch(
            f"{BASE_URL}/api/admin/orders/{own_order['id']}/status",
            params={"status": "packed"},
            timeout=30,
        )
        assert blocked.status_code == 403, blocked.text

    def test_orders_api_and_auth_me_regression(self, customer_session: requests.Session):
        me = customer_session.get(f"{BASE_URL}/api/auth/me", timeout=30)
        assert me.status_code == 200, me.text
        me_payload = me.json()
        assert me_payload["email"].lower() == CUSTOMER_EMAIL.lower()
        assert me_payload["role"] == "customer"

        listed = customer_session.get(f"{BASE_URL}/api/orders?page_size=20", timeout=30)
        assert listed.status_code == 200, listed.text
        data = listed.json()
        assert isinstance(data.get("items"), list)
        assert isinstance(data.get("total"), int)


class TestAuthPlaybookChecks:
    # Auth playbook checks for cookie/CORS/lockout behavior and bcrypt format

    def test_login_sets_http_only_cookies(self):
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/api/auth/login",
            json={"identifier": CUSTOMER_EMAIL, "password": CUSTOMER_PASSWORD},
            timeout=30,
        )
        assert response.status_code == 200, response.text
        set_cookie_headers = response.headers.get("set-cookie", "").lower()
        assert "access_token=" in set_cookie_headers
        assert "refresh_token=" in set_cookie_headers
        assert "httponly" in set_cookie_headers

    def test_auth_preflight_allows_credentials_for_explicit_origin(self):
        origin = BASE_URL
        response = requests.options(
            f"{BASE_URL}/api/auth/login",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=30,
        )
        assert response.status_code in [200, 204], response.text
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert response.headers.get("access-control-allow-origin") == origin

    def test_bruteforce_lockout_after_five_failures(self):
        session = _register_and_login_temp_customer()

        # Start from signed-out session to avoid stale success cookies affecting lockout assertions.
        logout = session.post(f"{BASE_URL}/api/auth/logout", timeout=30)
        assert logout.status_code in [200, 204], logout.text

        identifier = f"lock_{uuid.uuid4().hex[:8]}@example.com"
        setup = requests.Session().post(
            f"{BASE_URL}/api/auth/register",
            json={
                "name": "TEST Lockout",
                "email": identifier,
                "password": CUSTOMER_PASSWORD,
                "confirm_password": CUSTOMER_PASSWORD,
            },
            timeout=30,
        )
        assert setup.status_code == 201, setup.text

        attacker = requests.Session()
        for _ in range(5):
            failed = attacker.post(
                f"{BASE_URL}/api/auth/login",
                json={"identifier": identifier, "password": "WrongPass123!"},
                timeout=30,
            )
            assert failed.status_code == 401, failed.text

        locked = attacker.post(
            f"{BASE_URL}/api/auth/login",
            json={"identifier": identifier, "password": CUSTOMER_PASSWORD},
            timeout=30,
        )
        assert locked.status_code == 429, locked.text

    def test_bcrypt_hash_prefix_is_2b_for_new_user(self):
        pymongo = pytest.importorskip("pymongo")
        from dotenv import dotenv_values

        backend_env = dotenv_values("/app/backend/.env")
        mongo_url = backend_env.get("MONGO_URL")
        db_name = backend_env.get("DB_NAME")
        if not mongo_url or not db_name:
            pytest.skip("Mongo env values unavailable for hash check")

        email = f"hash_{uuid.uuid4().hex[:10]}@example.com"
        password = "Passw0rd!234"
        register = requests.post(
            f"{BASE_URL}/api/auth/register",
            json={"name": "TEST Hash", "email": email, "password": password, "confirm_password": password},
            timeout=30,
        )
        assert register.status_code == 201, register.text

        client = pymongo.MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
        try:
            user = client[db_name].users.find_one({"email": email})
            assert user and isinstance(user.get("password_hash"), str)
            assert user["password_hash"].startswith("$2b$")
        finally:
            client.close()
