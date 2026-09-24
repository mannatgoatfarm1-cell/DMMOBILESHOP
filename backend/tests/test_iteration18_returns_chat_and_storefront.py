import uuid

import pytest


# Core storefront sanity: categories and category-filtered products
def test_categories_and_products_filter(anon_session, base_url):
    categories = anon_session.get(f"{base_url}/api/categories", timeout=30)
    assert categories.status_code == 200, categories.text
    category_rows = categories.json()
    assert isinstance(category_rows, list)
    assert any(row.get("slug") == "mobiles" for row in category_rows)

    products = anon_session.get(f"{base_url}/api/products?category=mobiles&page_size=12", timeout=30)
    assert products.status_code == 200, products.text
    payload = products.json()
    assert isinstance(payload.get("items"), list)


# Auth and security guard checks relevant to this iteration
def test_login_sets_secure_http_only_cookies_and_lockout(anon_session, base_url):
    login = anon_session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert login.status_code == 200, login.text
    set_cookie = " | ".join(login.headers.get_all("set-cookie") if hasattr(login.headers, "get_all") else [login.headers.get("set-cookie", "")])
    assert "access_token=" in set_cookie
    assert "refresh_token=" in set_cookie
    assert "HttpOnly" in set_cookie

    identifier = f"locktest_{uuid.uuid4().hex[:8]}@example.com"
    for _ in range(5):
        attempt = anon_session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": identifier, "password": "wrong-password"},
            timeout=30,
        )
        assert attempt.status_code == 401, attempt.text

    blocked = anon_session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": identifier, "password": "wrong-password"},
        timeout=30,
    )
    assert blocked.status_code == 429, blocked.text


def _new_customer_session(base_url: str):
    import requests

    session = requests.Session()
    uniq = uuid.uuid4().hex[:10]
    email = f"test_i18_{uniq}@example.com"
    password = "Passw0rd!234"
    register = session.post(
        f"{base_url}/api/auth/register",
        json={
            "name": f"TEST_I18_{uniq}",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        timeout=30,
    )
    assert register.status_code == 201, register.text
    return session, register.json()


def _add_default_address(session, base_url: str) -> str:
    response = session.post(
        f"{base_url}/api/auth/me/addresses",
        json={
            "label": "HOME",
            "recipient_name": "TEST USER",
            "phone": "+919999999999",
            "line1": "123 Test Street",
            "line2": "",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "110001",
            "country": "India",
        },
        timeout=30,
    )
    assert response.status_code == 201, response.text
    data = response.json()
    assert isinstance(data.get("id"), str)
    return data["id"]


def _create_disposable_product(admin_session, base_url: str, warranty_days: int, slug_suffix: str):
    slug = f"test-i18-{slug_suffix}-{uuid.uuid4().hex[:7]}"
    payload = {
        "name": f"TEST I18 Product {slug_suffix}",
        "slug": slug,
        "sub": "Disposable regression item",
        "description": "Test-only product for returns/chat/storefront verification",
        "category_slug": "mobiles",
        "price": 12345,
        "original_price": 19999,
        "stock": 9,
        "images": ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=700&q=70"],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
        "qc_grade": "new",
        "qc_status": {},
        "imei_number": f"IMEI-{uuid.uuid4().hex[:10]}",
        "barcode": f"BAR-{uuid.uuid4().hex[:10]}",
        "warranty_days": warranty_days,
    }
    created = admin_session.post(f"{base_url}/api/admin/products", json=payload, timeout=30)
    assert created.status_code == 201, created.text
    data = created.json()
    assert data["category_slug"] == "mobiles"
    assert data["warranty_days"] == warranty_days
    return data


def _cleanup_product(admin_session, base_url: str, product_id: str):
    response = admin_session.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)
    assert response.status_code == 204, response.text


def _pick_available_payment_method(session, base_url: str) -> str:
    config = session.get(f"{base_url}/api/payment-config", timeout=30)
    assert config.status_code == 200, config.text
    methods = config.json().get("methods", {})
    for candidate in ["bank_transfer", "cod", "upi", "card", "net_banking", "wallet"]:
        if methods.get(candidate) is True:
            return candidate
    pytest.skip("No enabled payment method available for order creation in this environment")


def _place_order_for_product(session, base_url: str, address_id: str, product_id: str):
    cart_add = session.post(
        f"{base_url}/api/cart/items",
        json={"product_id": product_id, "quantity": 1},
        timeout=30,
    )
    assert cart_add.status_code == 200, cart_add.text

    method = _pick_available_payment_method(session, base_url)

    order = session.post(
        f"{base_url}/api/orders",
        json={"address_id": address_id, "payment_method": method, "coupon_code": None},
        timeout=30,
    )
    assert order.status_code == 201, order.text
    order_data = order.json()
    assert order_data["payment"]["method"] == method
    assert len(order_data.get("items", [])) >= 1
    assert order_data["items"][0]["product_id"] == product_id
    return order_data


def _upload_evidence(session, base_url: str, kind: str, filename: str, content_type: str, content: bytes):
    response = session.post(
        f"{base_url}/api/returns/evidence?kind={kind}",
        files={"file": (filename, content, content_type)},
        timeout=60,
    )
    return response


# Admin add-product payload and public visibility check
def test_admin_product_create_visible_then_cleanup(admin_session, anon_session, base_url):
    product = _create_disposable_product(admin_session, base_url, warranty_days=365, slug_suffix="public")
    try:
        public_by_id = anon_session.get(f"{base_url}/api/products/{product['id']}", timeout=30)
        assert public_by_id.status_code == 200, public_by_id.text
        row = public_by_id.json()
        assert row["warranty_days"] == 365
        assert row["imei_number"].startswith("IMEI-")
        assert row["barcode"].startswith("BAR-")

        listing = anon_session.get(f"{base_url}/api/products?category=mobiles&page_size=100", timeout=30)
        assert listing.status_code == 200, listing.text
        assert any(item["id"] == product["id"] for item in listing.json().get("items", []))
    finally:
        _cleanup_product(admin_session, base_url, product["id"])


# Return backend checks: warranty/no-warranty and evidence ownership/visibility
def test_no_warranty_return_claim_rejected(admin_session, base_url):
    customer_session, _ = _new_customer_session(base_url)
    product = _create_disposable_product(admin_session, base_url, warranty_days=0, slug_suffix="nowarranty")
    try:
        address_id = _add_default_address(customer_session, base_url)
        order = _place_order_for_product(customer_session, base_url, address_id, product["id"])

        photo_1 = _upload_evidence(customer_session, base_url, "photo", "front.jpg", "image/jpeg", b"fake-jpeg-1")
        photo_2 = _upload_evidence(customer_session, base_url, "photo", "back.jpg", "image/jpeg", b"fake-jpeg-2")
        video = _upload_evidence(customer_session, base_url, "video", "device.mp4", "video/mp4", b"fake-mp4")
        assert photo_1.status_code == 200, photo_1.text
        assert photo_2.status_code == 200, photo_2.text
        assert video.status_code == 200, video.text

        claim = customer_session.post(
            f"{base_url}/api/returns/claim",
            json={
                "order_id": order["id"],
                "reason": "defective",
                "detail": "Device has display and battery issues",
                "photo_file_ids": [photo_1.json()["id"], photo_2.json()["id"]],
                "video_file_id": video.json()["id"],
            },
            timeout=30,
        )
        assert claim.status_code == 409, claim.text
    finally:
        _cleanup_product(admin_session, base_url, product["id"])


def test_warranty_claim_evidence_rules_and_admin_decision_flow(admin_session, anon_session, base_url):
    customer_session, _ = _new_customer_session(base_url)
    other_customer_session, _ = _new_customer_session(base_url)
    product = _create_disposable_product(admin_session, base_url, warranty_days=180, slug_suffix="warranty")

    try:
        address_id = _add_default_address(customer_session, base_url)
        order = _place_order_for_product(customer_session, base_url, address_id, product["id"])

        foreign_photo = _upload_evidence(other_customer_session, base_url, "photo", "other.jpg", "image/jpeg", b"other-photo")
        assert foreign_photo.status_code == 200, foreign_photo.text

        own_photo = _upload_evidence(customer_session, base_url, "photo", "front.jpg", "image/jpeg", b"p1")
        own_video = _upload_evidence(customer_session, base_url, "video", "device.mp4", "video/mp4", b"v1")
        assert own_photo.status_code == 200, own_photo.text
        assert own_video.status_code == 200, own_video.text

        invalid_claim = customer_session.post(
            f"{base_url}/api/returns/claim",
            json={
                "order_id": order["id"],
                "reason": "warranty_claim",
                "detail": "Need warranty support because charging fails",
                "photo_file_ids": [own_photo.json()["id"], foreign_photo.json()["id"]],
                "video_file_id": own_video.json()["id"],
            },
            timeout=30,
        )
        assert invalid_claim.status_code == 422, invalid_claim.text

        photo_2 = _upload_evidence(customer_session, base_url, "photo", "back.jpg", "image/jpeg", b"p2")
        assert photo_2.status_code == 200, photo_2.text

        public_blocked = anon_session.get(f"{base_url}/api/media/{own_photo.json()['id']}", timeout=30)
        assert public_blocked.status_code == 403, public_blocked.text

        admin_media = admin_session.get(f"{base_url}/api/admin/media/{own_photo.json()['id']}", timeout=60)
        assert admin_media.status_code == 200, admin_media.text

        claim = customer_session.post(
            f"{base_url}/api/returns/claim",
            json={
                "order_id": order["id"],
                "reason": "warranty_claim",
                "detail": "Screen flickers and phone heats up within warranty period",
                "photo_file_ids": [own_photo.json()["id"], photo_2.json()["id"]],
                "video_file_id": own_video.json()["id"],
            },
            timeout=30,
        )
        assert claim.status_code == 200, claim.text
        claim_data = claim.json()
        assert claim_data["status"] == "pending_admin_review"

        decision = admin_session.post(
            f"{base_url}/api/admin/returns/{claim_data['id']}/decision",
            json={"decision": "approve", "reason": "Evidence verified and warranty is valid"},
            timeout=30,
        )
        assert decision.status_code == 200, decision.text
        assert decision.json()["status"] == "approved"

        customer_claims = customer_session.get(f"{base_url}/api/returns", timeout=30)
        assert customer_claims.status_code == 200, customer_claims.text
        approved = next(item for item in customer_claims.json() if item["id"] == claim_data["id"])
        assert approved["data"]["admin_reason"] == "Evidence verified and warranty is valid"

        second_decision = admin_session.post(
            f"{base_url}/api/admin/returns/{claim_data['id']}/decision",
            json={"decision": "disapprove", "reason": "Second decision should fail"},
            timeout=30,
        )
        assert second_decision.status_code == 409, second_decision.text
    finally:
        _cleanup_product(admin_session, base_url, product["id"])


def test_return_evidence_upload_type_and_size_limits(customer_session, base_url):
    invalid_photo_type = _upload_evidence(customer_session, base_url, "photo", "x.gif", "image/gif", b"gif")
    assert invalid_photo_type.status_code == 415, invalid_photo_type.text

    too_large_photo = _upload_evidence(customer_session, base_url, "photo", "large.jpg", "image/jpeg", b"0" * (5 * 1024 * 1024 + 1))
    assert too_large_photo.status_code == 413, too_large_photo.text

    invalid_video_type = _upload_evidence(customer_session, base_url, "video", "x.avi", "video/x-msvideo", b"avi")
    assert invalid_video_type.status_code == 415, invalid_video_type.text


# Live chat integration checks with role and isolation guards
def test_live_chat_customer_admin_roundtrip_and_isolation(base_url, admin_session, anon_session):
    customer_one, customer_one_user = _new_customer_session(base_url)
    customer_two, _ = _new_customer_session(base_url)

    send = customer_one.post(
        f"{base_url}/api/chat/messages",
        json={"message": "TEST I18 customer message"},
        timeout=30,
    )
    assert send.status_code == 200, send.text
    customer_msg = send.json()
    assert customer_msg["sender_role"] == "customer"

    unauthorized_admin = anon_session.get(f"{base_url}/api/admin/chats", timeout=30)
    assert unauthorized_admin.status_code == 401, unauthorized_admin.text
    unauthorized_customer_chat = anon_session.get(f"{base_url}/api/chat/thread", timeout=30)
    assert unauthorized_customer_chat.status_code == 401, unauthorized_customer_chat.text

    admin_threads = admin_session.get(f"{base_url}/api/admin/chats", timeout=30)
    assert admin_threads.status_code == 200, admin_threads.text
    threads = admin_threads.json()
    thread = next(item for item in threads if item.get("user_email") == customer_one_user["email"])
    assert thread["id"] == customer_msg["thread_id"]

    admin_reply = admin_session.post(
        f"{base_url}/api/admin/chats/{thread['id']}/messages",
        json={"message": "TEST I18 admin reply"},
        timeout=30,
    )
    assert admin_reply.status_code == 200, admin_reply.text
    assert admin_reply.json()["sender_role"] == "admin"

    customer_one_thread = customer_one.get(f"{base_url}/api/chat/thread", timeout=30)
    assert customer_one_thread.status_code == 200, customer_one_thread.text
    messages_one = customer_one_thread.json().get("messages", [])
    assert any(message.get("message") == "TEST I18 admin reply" for message in messages_one)

    customer_two_thread = customer_two.get(f"{base_url}/api/chat/thread", timeout=30)
    assert customer_two_thread.status_code == 200, customer_two_thread.text
    messages_two = customer_two_thread.json().get("messages", [])
    assert not any(message.get("message") == "TEST I18 customer message" for message in messages_two)


# Checkout dependency checks for wallet option data source
def test_payment_config_exposes_wallet_and_methods(anon_session, base_url):
    response = anon_session.get(f"{base_url}/api/payment-config", timeout=30)
    assert response.status_code == 200, response.text
    config = response.json()
    assert isinstance(config.get("methods"), dict)
    assert "wallet" in config["methods"]


# Cleanup safety: remove disposable UI products created during manual/browser checks
def test_cleanup_disposable_ui_products(admin_session, base_url):
    listed = admin_session.get(f"{base_url}/api/admin/products?page_size=200", timeout=30)
    assert listed.status_code == 200, listed.text
    items = listed.json().get("items", [])
    disposable = [item for item in items if str(item.get("slug", "")).startswith("test-ui-i18-")]
    for product in disposable:
        removed = admin_session.delete(f"{base_url}/api/admin/products/{product['id']}", timeout=30)
        assert removed.status_code == 204, removed.text
