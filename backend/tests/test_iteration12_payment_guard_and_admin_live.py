import uuid

import pytest


# Core platform health + auth/session module
def test_health_endpoint_ok(base_url: str, anon_session):
    response = anon_session.get(f"{base_url}/api/health", timeout=30)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload == {"status": "ok"}


def test_admin_login_sets_http_only_cookies_and_dashboard_renders(base_url: str):
    import requests

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

    dashboard = session.get(f"{base_url}/api/admin/dashboard", timeout=30)
    assert dashboard.status_code == 200, dashboard.text
    data = dashboard.json()
    assert isinstance(data.get("metrics"), dict)
    assert "total_products" in data["metrics"]


# Payment settings + config module
def test_public_payment_config_shape(base_url: str, anon_session):
    response = anon_session.get(f"{base_url}/api/payment-config", timeout=30)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload.get("configured"), bool)
    assert payload.get("mode") in ["test", "live"]
    methods = payload.get("methods", {})
    for method in ["upi", "card", "net_banking", "cod", "wallet"]:
        assert isinstance(methods.get(method), bool)


def test_admin_payment_settings_requires_auth(base_url: str, anon_session):
    response = anon_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert response.status_code == 401, response.text
    detail = response.json().get("detail", "")
    assert isinstance(detail, str) and detail != ""


def test_admin_can_toggle_cod_and_restore_payment_settings(base_url: str, admin_session):
    original = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert original.status_code == 200, original.text
    baseline = original.json()

    toggled_payload = {
        "razorpay_key_id": baseline.get("razorpay_key_id", ""),
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": baseline.get("mode", "test"),
        "upi_enabled": baseline.get("upi_enabled", True),
        "card_enabled": baseline.get("card_enabled", True),
        "netbanking_enabled": baseline.get("netbanking_enabled", True),
        "cod_enabled": not baseline.get("cod_enabled", True),
        "wallet_enabled": baseline.get("wallet_enabled", True),
        "partial_payment_enabled": baseline.get("partial_payment_enabled", False),
        "partial_payment_percent": baseline.get("partial_payment_percent", 100),
    }
    save = admin_session.put(
        f"{base_url}/api/admin/payment-settings", json=toggled_payload, timeout=30
    )
    assert save.status_code == 200, save.text
    assert save.json()["cod_enabled"] == toggled_payload["cod_enabled"]

    # Restore original configuration after verification
    restore_payload = {
        "razorpay_key_id": baseline.get("razorpay_key_id", ""),
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": baseline.get("mode", "test"),
        "upi_enabled": baseline.get("upi_enabled", True),
        "card_enabled": baseline.get("card_enabled", True),
        "netbanking_enabled": baseline.get("netbanking_enabled", True),
        "cod_enabled": baseline.get("cod_enabled", True),
        "wallet_enabled": baseline.get("wallet_enabled", True),
        "partial_payment_enabled": baseline.get("partial_payment_enabled", False),
        "partial_payment_percent": baseline.get("partial_payment_percent", 100),
    }
    restore = admin_session.put(
        f"{base_url}/api/admin/payment-settings", json=restore_payload, timeout=30
    )
    assert restore.status_code == 200, restore.text
    assert restore.json()["cod_enabled"] == baseline.get("cod_enabled", True)


# Checkout guard module: disabled method must be blocked by backend
def test_checkout_blocks_disabled_method_and_restores_settings(base_url: str, admin_session):
    import requests

    settings_response = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert settings_response.status_code == 200, settings_response.text
    baseline = settings_response.json()

    disable_cod_payload = {
        "razorpay_key_id": baseline.get("razorpay_key_id", ""),
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": baseline.get("mode", "test"),
        "upi_enabled": baseline.get("upi_enabled", True),
        "card_enabled": baseline.get("card_enabled", True),
        "netbanking_enabled": baseline.get("netbanking_enabled", True),
        "cod_enabled": False,
        "wallet_enabled": baseline.get("wallet_enabled", True),
        "partial_payment_enabled": baseline.get("partial_payment_enabled", False),
        "partial_payment_percent": baseline.get("partial_payment_percent", 100),
    }

    restore_payload = {
        "razorpay_key_id": baseline.get("razorpay_key_id", ""),
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": baseline.get("mode", "test"),
        "upi_enabled": baseline.get("upi_enabled", True),
        "card_enabled": baseline.get("card_enabled", True),
        "netbanking_enabled": baseline.get("netbanking_enabled", True),
        "cod_enabled": baseline.get("cod_enabled", True),
        "wallet_enabled": baseline.get("wallet_enabled", True),
        "partial_payment_enabled": baseline.get("partial_payment_enabled", False),
        "partial_payment_percent": baseline.get("partial_payment_percent", 100),
    }

    marker = uuid.uuid4().hex[:8]
    customer_email = f"test_guard_{marker}@example.com"
    password = "Passw0rd!234"
    customer = requests.Session()

    try:
        disable_response = admin_session.put(
            f"{base_url}/api/admin/payment-settings", json=disable_cod_payload, timeout=30
        )
        assert disable_response.status_code == 200, disable_response.text
        assert disable_response.json()["cod_enabled"] is False

        register = customer.post(
            f"{base_url}/api/auth/register",
            json={
                "name": f"TEST Guard {marker}",
                "email": customer_email,
                "password": password,
                "confirm_password": password,
            },
            timeout=30,
        )
        assert register.status_code == 201, register.text

        address = customer.post(
            f"{base_url}/api/auth/me/addresses",
            json={
                "label": "HOME",
                "recipient_name": "Test Guard",
                "phone": "+919999999999",
                "line1": "Test Address 1",
                "line2": "Near QA Road",
                "city": "New Delhi",
                "state": "Delhi",
                "postal_code": "110001",
                "country": "India",
            },
            timeout=30,
        )
        assert address.status_code == 201, address.text
        address_id = address.json()["id"]

        products = customer.get(f"{base_url}/api/products?page_size=1", timeout=30)
        assert products.status_code == 200, products.text
        first_product = products.json()["items"][0]

        cart = customer.post(
            f"{base_url}/api/cart/items",
            json={"product_id": first_product["id"], "quantity": 1},
            timeout=30,
        )
        assert cart.status_code == 200, cart.text

        order = customer.post(
            f"{base_url}/api/orders",
            json={"address_id": address_id, "payment_method": "cod"},
            timeout=30,
        )
        assert order.status_code == 422, order.text
        assert "payment method" in order.json().get("detail", "")
    finally:
        admin_session.put(
            f"{base_url}/api/admin/payment-settings", json=restore_payload, timeout=30
        )


# Auth hardening module: brute-force lockout + credentialed CORS preflight
def test_bruteforce_lockout_after_five_failures(base_url: str):
    import requests

    marker = uuid.uuid4().hex[:8]
    email = f"test_lock_{marker}@example.com"
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


def test_auth_preflight_allows_explicit_origin_and_credentials(base_url: str):
    import requests

    preflight = requests.options(
        f"{base_url}/api/auth/login",
        headers={
            "Origin": "https://dashboard-design-20.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert preflight.headers.get("access-control-allow-credentials") == "true"
    assert (
        preflight.headers.get("access-control-allow-origin")
        == "https://dashboard-design-20.preview.emergentagent.com"
    )
