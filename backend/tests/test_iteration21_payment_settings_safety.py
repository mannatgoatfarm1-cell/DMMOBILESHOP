import pytest


# Auth/session safety module
def test_admin_login_works_and_sets_http_only_session_cookies(base_url: str, anon_session):
    response = anon_session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload.get("role") == "admin"
    assert payload.get("email") == "deepak143@mobilecart.com"

    set_cookie = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie


# Password hashing guard module
def test_bcrypt_hashes_use_2b_prefix():
    from server import hash_password

    hashed = hash_password("TestPass123!")
    assert hashed.startswith("$2b$")


# Payment settings secrecy module
def test_admin_payment_settings_get_hides_secret_values(base_url: str, admin_session):
    response = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert response.status_code == 200, response.text

    payload = response.json()
    assert "razorpay_key_secret" not in payload
    assert "razorpay_webhook_secret" not in payload
    assert isinstance(payload.get("razorpay_key_secret_set"), bool)
    assert isinstance(payload.get("razorpay_webhook_secret_set"), bool)


@pytest.mark.parametrize("masked_value", ["***", "••••••••", "********", "Saved securely — enter only to replace"])
def test_masked_secret_submission_preserves_server_side_secret_state(base_url: str, admin_session, masked_value: str):
    before_admin = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert before_admin.status_code == 200, before_admin.text
    before_payload = before_admin.json()

    before_public = admin_session.get(f"{base_url}/api/payment-config", timeout=30)
    assert before_public.status_code == 200, before_public.text
    before_public_payload = before_public.json()

    submit_payload = {
        "razorpay_key_id": before_payload.get("razorpay_key_id", ""),
        "razorpay_key_secret": masked_value,
        "razorpay_webhook_secret": masked_value,
        "mode": before_payload.get("mode", "test"),
        "upi_enabled": before_payload.get("upi_enabled", True),
        "upi_id": before_payload.get("upi_id", ""),
        "card_enabled": before_payload.get("card_enabled", True),
        "netbanking_enabled": before_payload.get("netbanking_enabled", True),
        "cod_enabled": before_payload.get("cod_enabled", True),
        "wallet_enabled": before_payload.get("wallet_enabled", True),
        "bank_transfer_enabled": before_payload.get("bank_transfer_enabled", True),
        "bank_account_name": before_payload.get("bank_account_name", ""),
        "bank_account_number": before_payload.get("bank_account_number", ""),
        "bank_ifsc_code": before_payload.get("bank_ifsc_code", ""),
        "partial_payment_enabled": before_payload.get("partial_payment_enabled", False),
        "partial_payment_percent": before_payload.get("partial_payment_percent", 100),
    }

    save = admin_session.put(f"{base_url}/api/admin/payment-settings", json=submit_payload, timeout=30)
    assert save.status_code == 200, save.text
    saved_payload = save.json()

    assert "razorpay_key_secret" not in saved_payload
    assert "razorpay_webhook_secret" not in saved_payload
    assert saved_payload.get("razorpay_key_secret_set") == before_payload.get("razorpay_key_secret_set")
    assert saved_payload.get("razorpay_webhook_secret_set") == before_payload.get("razorpay_webhook_secret_set")

    after_admin = admin_session.get(f"{base_url}/api/admin/payment-settings", timeout=30)
    assert after_admin.status_code == 200, after_admin.text
    after_payload = after_admin.json()
    assert after_payload.get("razorpay_key_secret_set") == before_payload.get("razorpay_key_secret_set")
    assert after_payload.get("razorpay_webhook_secret_set") == before_payload.get("razorpay_webhook_secret_set")

    after_public = admin_session.get(f"{base_url}/api/payment-config", timeout=30)
    assert after_public.status_code == 200, after_public.text
    after_public_payload = after_public.json()
    assert after_public_payload.get("configured") == before_public_payload.get("configured")
    assert after_public_payload.get("key_id") == before_public_payload.get("key_id")


# CORS credentials module
def test_auth_preflight_has_allow_credentials_header(base_url: str):
    import requests

    response = requests.options(
        f"{base_url}/api/auth/login",
        headers={
            "Origin": "https://dashboard-design-20.preview.emergentagent.com",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
        timeout=30,
    )
    assert response.status_code == 200, response.text
    assert response.headers.get("access-control-allow-credentials") == "true"
    assert (
        response.headers.get("access-control-allow-origin")
        == "https://dashboard-design-20.preview.emergentagent.com"
    )
