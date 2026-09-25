import base64
import uuid
from urllib.parse import parse_qs, urlparse

import pytest


# Module coverage: admin product IDs, payment settings, manual transfer proof/review, invoice branding.


TINY_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Z"
    "x9kAAAAASUVORK5CYII="
)


@pytest.fixture
def disposable_product(admin_session, base_url):
    categories_res = admin_session.get(f"{base_url}/api/admin/categories", timeout=30)
    assert categories_res.status_code == 200, categories_res.text
    categories = categories_res.json()
    active_category = next((c for c in categories if c.get("active") is True), None)
    assert active_category is not None

    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST_IT17_{unique}",
        "slug": f"test-it17-{unique}",
        "sub": "Disposable regression product",
        "description": "Disposable product for IMEI/barcode + payment tests",
        "category_slug": active_category["slug"],
        "price": 12345,
        "original_price": 22345,
        "stock": 5,
        "images": ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9"],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
        "qc_grade": "new",
        "qc_status": {},
        "imei_number": f"IMEI-{unique}",
        "barcode": f"BAR-{unique}",
    }
    create_res = admin_session.post(f"{base_url}/api/admin/products", json=payload, timeout=30)
    assert create_res.status_code == 201, create_res.text
    created = create_res.json()

    yield {
        "id": created["id"],
        "slug": created["slug"],
        "category_slug": created["category_slug"],
        "imei": created["imei_number"],
        "barcode": created["barcode"],
    }

    admin_session.delete(f"{base_url}/api/admin/products/{created['id']}", timeout=30)


@pytest.fixture
def disposable_customer_with_address(base_url):
    unique = uuid.uuid4().hex[:8]
    email = f"test_it17_{unique}@example.com"
    password = "Passw0rd!234"

    session = __import__("requests").Session()
    register_payload = {
        "name": f"TEST_IT17_USER_{unique}",
        "email": email,
        "password": password,
        "confirm_password": password,
    }
    register = session.post(f"{base_url}/api/auth/register", json=register_payload, timeout=30)
    assert register.status_code == 201, register.text

    address_payload = {
        "label": "HOME",
        "recipient_name": "Test User",
        "phone": "+919999999999",
        "line1": "123 Test Lane",
        "line2": "",
        "city": "Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
    }
    address_res = session.post(f"{base_url}/api/auth/me/addresses", json=address_payload, timeout=30)
    assert address_res.status_code == 201, address_res.text
    address = address_res.json()

    return {"session": session, "address_id": address["id"], "email": email, "password": password}


def _add_to_cart(base_url, customer_session, product_id, qty=1):
    cart_res = customer_session.post(
        f"{base_url}/api/cart/items",
        json={"product_id": product_id, "quantity": qty},
        timeout=30,
    )
    assert cart_res.status_code == 200, cart_res.text
    return cart_res.json()


def _create_bank_transfer_order(base_url, customer_session, address_id):
    order_res = customer_session.post(
        f"{base_url}/api/orders",
        json={"address_id": address_id, "payment_method": "bank_transfer"},
        timeout=30,
    )
    assert order_res.status_code == 201, order_res.text
    return order_res.json()


def _upload_proof(base_url, customer_session, order_id):
    png_data = base64.b64decode(TINY_PNG_BASE64)
    files = {"file": ("proof.png", png_data, "image/png")}
    proof_res = customer_session.post(
        f"{base_url}/api/payments/manual-proof?order_id={order_id}",
        files=files,
        data={"payment_reference": "UPI-TEST-123456"},
        timeout=30,
    )
    assert proof_res.status_code == 200, proof_res.text
    return proof_res.json()


def test_auth_login_sets_secure_httponly_cookies(base_url):
    requests = __import__("requests")
    session = requests.Session()
    response = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    set_cookie = "; ".join(response.headers.get("set-cookie", "").split(","))
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie


def test_admin_product_identifier_and_public_category_filter(base_url, admin_session, disposable_product):
    public = admin_session.get(
        f"{base_url}/api/products?category={disposable_product['category_slug']}&query=TEST_IT17",
        timeout=30,
    )
    assert public.status_code == 200, public.text
    items = public.json()["items"]
    match = next((p for p in items if p["id"] == disposable_product["id"]), None)
    assert match is not None
    assert match["imei_number"] == disposable_product["imei"]
    assert match["barcode"] == disposable_product["barcode"]


def test_payment_settings_persist_and_public_config_hides_secrets(base_url, admin_session):
    update_payload = {
        "razorpay_key_id": "",
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": "test",
        "upi_enabled": True,
        "upi_id": "dmobilemart@upi",
        "card_enabled": True,
        "netbanking_enabled": True,
        "cod_enabled": True,
        "wallet_enabled": True,
        "bank_transfer_enabled": True,
        "bank_account_name": "DMobileMart",
        "bank_account_number": "123456789012",
        "bank_ifsc_code": "HDFC0123456",
        "partial_payment_enabled": False,
        "partial_payment_percent": 100,
    }
    save = admin_session.put(f"{base_url}/api/admin/payment-settings", json=update_payload, timeout=30)
    assert save.status_code == 200, save.text
    saved = save.json()
    assert saved["bank_ifsc_code"] == "HDFC0123456"
    assert saved["bank_account_number"] == "123456789012"
    assert saved["bank_transfer_enabled"] is True

    public_cfg_res = admin_session.get(f"{base_url}/api/payment-config", timeout=30)
    assert public_cfg_res.status_code == 200, public_cfg_res.text
    public_cfg = public_cfg_res.json()
    assert public_cfg["manual_transfer"]["ifsc_code"] == "HDFC0123456"
    assert public_cfg["manual_transfer"]["account_number"] == "123456789012"
    assert "razorpay_key_secret" not in public_cfg
    assert "razorpay_webhook_secret" not in public_cfg


def test_manual_transfer_order_snapshot_proof_and_invoice(
    base_url,
    admin_session,
    disposable_product,
    disposable_customer_with_address,
):
    customer = disposable_customer_with_address["session"]

    _add_to_cart(base_url, customer, disposable_product["id"], qty=1)
    order = _create_bank_transfer_order(base_url, customer, disposable_customer_with_address["address_id"])

    line = order["items"][0]
    assert line["imei_number"] == disposable_product["imei"]
    assert line["barcode"] == disposable_product["barcode"]
    assert order["status"] == "payment_proof_required"

    instructions = customer.get(f"{base_url}/api/payments/manual-upi/{order['id']}", timeout=30)
    assert instructions.status_code == 200, instructions.text
    manual_upi = instructions.json()
    parsed_uri = parse_qs(urlparse(manual_upi["upi_uri"]).query)
    assert manual_upi["order_id"] == order["id"]
    assert manual_upi["amount"] == order["total"]
    assert parsed_uri["am"] == [f"{order['total']:.2f}"]
    assert parsed_uri["cu"] == ["INR"]
    assert "pa" in parsed_uri and parsed_uri["pa"][0]

    proof_order = _upload_proof(base_url, customer, order["id"])
    assert proof_order["status"] == "payment_review"
    assert proof_order["payment"]["status"] == "review_pending"
    assert proof_order["payment"]["payment_reference"] == "UPI-TEST-123456"

    proof_customer = customer.get(f"{base_url}/api/admin/orders/{order['id']}/payment-proof", timeout=30)
    assert proof_customer.status_code in (401, 403)

    proof_admin = admin_session.get(f"{base_url}/api/admin/orders/{order['id']}/payment-proof", timeout=30)
    assert proof_admin.status_code == 200, proof_admin.text
    assert proof_admin.headers.get("content-type", "").startswith("image/")

    invoice = customer.get(f"{base_url}/api/orders/{order['id']}/invoice", timeout=30)
    assert invoice.status_code == 200, invoice.text
    assert invoice.headers.get("content-type", "").startswith("application/pdf")
    assert len(invoice.content) > 500


def test_admin_capture_confirms_review_pending_order(
    base_url,
    admin_session,
    disposable_product,
    disposable_customer_with_address,
):
    customer = disposable_customer_with_address["session"]
    _add_to_cart(base_url, customer, disposable_product["id"], qty=1)
    order = _create_bank_transfer_order(base_url, customer, disposable_customer_with_address["address_id"])
    _upload_proof(base_url, customer, order["id"])

    capture = admin_session.post(
        f"{base_url}/api/admin/orders/{order['id']}/payment-review",
        json={"action": "capture", "note": "ok"},
        timeout=30,
    )
    assert capture.status_code == 200, capture.text
    reviewed = capture.json()
    assert reviewed["status"] == "confirmed"
    assert reviewed["payment"]["status"] == "captured"


def test_admin_reject_restores_stock_once(
    base_url,
    admin_session,
    disposable_product,
    disposable_customer_with_address,
):
    customer = disposable_customer_with_address["session"]
    before = admin_session.get(f"{base_url}/api/products/{disposable_product['id']}", timeout=30)
    assert before.status_code == 200, before.text
    stock_before = before.json()["stock"]

    _add_to_cart(base_url, customer, disposable_product["id"], qty=1)
    order = _create_bank_transfer_order(base_url, customer, disposable_customer_with_address["address_id"])
    _upload_proof(base_url, customer, order["id"])

    after_order = admin_session.get(f"{base_url}/api/products/{disposable_product['id']}", timeout=30)
    assert after_order.status_code == 200
    assert after_order.json()["stock"] == stock_before - 1

    reject = admin_session.post(
        f"{base_url}/api/admin/orders/{order['id']}/payment-review",
        json={"action": "reject", "note": "proof mismatch"},
        timeout=30,
    )
    assert reject.status_code == 200, reject.text
    rejected = reject.json()
    assert rejected["status"] == "payment_failed"
    assert rejected["payment"]["status"] == "failed"

    after_reject = admin_session.get(f"{base_url}/api/products/{disposable_product['id']}", timeout=30)
    assert after_reject.status_code == 200
    assert after_reject.json()["stock"] == stock_before

    reject_again = admin_session.post(
        f"{base_url}/api/admin/orders/{order['id']}/payment-review",
        json={"action": "reject", "note": "retry"},
        timeout=30,
    )
    assert reject_again.status_code == 409, reject_again.text

    after_second = admin_session.get(f"{base_url}/api/products/{disposable_product['id']}", timeout=30)
    assert after_second.status_code == 200
    assert after_second.json()["stock"] == stock_before


def test_invalid_ifsc_rejected(base_url, admin_session):
    bad_payload = {
        "razorpay_key_id": "",
        "razorpay_key_secret": "",
        "razorpay_webhook_secret": "",
        "mode": "test",
        "upi_enabled": True,
        "upi_id": "dmobilemart@upi",
        "card_enabled": True,
        "netbanking_enabled": True,
        "cod_enabled": True,
        "wallet_enabled": True,
        "bank_transfer_enabled": True,
        "bank_account_name": "DMobileMart",
        "bank_account_number": "123456789012",
        "bank_ifsc_code": "BADIFSC",
        "partial_payment_enabled": False,
        "partial_payment_percent": 100,
    }
    response = admin_session.put(f"{base_url}/api/admin/payment-settings", json=bad_payload, timeout=30)
    assert response.status_code == 422, response.text
