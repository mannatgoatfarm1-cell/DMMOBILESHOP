import time
import uuid

import requests


# Core stock + payment guard + wishlist/category/admin regression tests


def _register_customer(base_url: str) -> requests.Session:
    session = requests.Session()
    unique = uuid.uuid4().hex[:10]
    password = "TestPass123!"
    payload = {
        "name": f"TEST_iter16_{unique}",
        "email": f"test_iter16_{unique}@example.com",
        "password": password,
        "confirm_password": password,
    }
    response = session.post(f"{base_url}/api/auth/register", json=payload, timeout=30)
    assert response.status_code == 201, response.text
    return session


def _create_address(session: requests.Session, base_url: str) -> str:
    payload = {
        "label": "HOME",
        "recipient_name": "TEST Receiver",
        "phone": "+919900001111",
        "line1": "123 Iteration Street",
        "line2": "",
        "city": "Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
    }
    response = session.post(f"{base_url}/api/auth/me/addresses", json=payload, timeout=30)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def _create_admin_product(admin_session: requests.Session, base_url: str, *, stock: int, category_slug: str = "mobiles") -> dict:
    token = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST_ITER16 Product {token}",
        "slug": f"test-iter16-{token}",
        "sub": "Disposable product for integration regression",
        "description": "TEMP product for automated stock/payment tests",
        "category_slug": category_slug,
        "price": 12999,
        "original_price": 15999,
        "stock": stock,
        "images": ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=85"],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
        "qc_grade": "new",
        "qc_status": {},
    }
    response = admin_session.post(f"{base_url}/api/admin/products", json=payload, timeout=30)
    assert response.status_code == 201, response.text
    return response.json()


def _admin_login(base_url: str) -> requests.Session:
    session = requests.Session()
    response = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": "deepak143", "password": "deepak143"},
        timeout=30,
    )
    assert response.status_code == 200, response.text
    return session


def test_stock_zero_public_and_cart_guards(base_url: str, admin_session: requests.Session):
    """Stock 0 is exposed publicly and cart add/increase paths block with 409."""
    customer = _register_customer(base_url)
    product = _create_admin_product(admin_session, base_url, stock=1)
    product_id = product["id"]

    try:
        add_response = customer.post(
            f"{base_url}/api/cart/items",
            json={"product_id": product_id, "quantity": 1},
            timeout=30,
        )
        assert add_response.status_code == 200, add_response.text

        reduce_stock = admin_session.patch(
            f"{base_url}/api/admin/products/{product_id}",
            json={
                "name": product["name"],
                "slug": product["slug"],
                "sub": product["sub"],
                "description": product["description"],
                "category_slug": product["category_slug"],
                "price": product["price"],
                "original_price": product["original_price"],
                "stock": 0,
                "images": product["images"],
                "tag": product["tag"],
                "variants": product.get("variants", []),
                "active": True,
                "featured": product.get("featured", False),
                "qc_grade": product.get("qc_grade", "new"),
                "qc_status": product.get("qc_status", {}),
            },
            timeout=30,
        )
        assert reduce_stock.status_code == 200, reduce_stock.text

        public_product = requests.get(f"{base_url}/api/products/{product_id}", timeout=30)
        assert public_product.status_code == 200, public_product.text
        assert public_product.json()["stock"] == 0

        add_again = customer.post(
            f"{base_url}/api/cart/items",
            json={"product_id": product_id, "quantity": 1},
            timeout=30,
        )
        assert add_again.status_code == 409, add_again.text

        increase = customer.patch(
            f"{base_url}/api/cart/items/{product_id}",
            json={"product_id": product_id, "quantity": 2},
            timeout=30,
        )
        assert increase.status_code == 409, increase.text
    finally:
        customer.delete(f"{base_url}/api/cart/items/{product_id}", timeout=30)
        admin_session.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)


def test_upi_fail_marks_order_failed_restores_stock_and_history(base_url: str, admin_session: requests.Session):
    """UPI fail endpoint marks payment failed, restores stock, and keeps failed order in history."""
    customer = _register_customer(base_url)
    address_id = _create_address(customer, base_url)
    product = _create_admin_product(admin_session, base_url, stock=1)
    product_id = product["id"]

    try:
        add = customer.post(
            f"{base_url}/api/cart/items",
            json={"product_id": product_id, "quantity": 1},
            timeout=30,
        )
        assert add.status_code == 200, add.text

        order_response = customer.post(
            f"{base_url}/api/orders",
            json={"address_id": address_id, "payment_method": "upi"},
            timeout=30,
        )
        assert order_response.status_code == 201, order_response.text
        order_data = order_response.json()
        assert order_data["status"] == "payment_pending"
        assert order_data["payment"]["status"] == "pending"

        fail_response = customer.post(
            f"{base_url}/api/payments/razorpay/fail",
            json={"order_id": order_data["id"], "reason": "iter16_manual_fail"},
            timeout=30,
        )
        assert fail_response.status_code == 200, fail_response.text
        failed_order = fail_response.json()
        assert failed_order["status"] == "payment_failed"
        assert failed_order["payment"]["status"] == "failed"
        assert any(event.get("status") == "Payment failed" for event in failed_order["tracking"]["events"])

        # Allow consistency refresh for storefront polling/write completion.
        time.sleep(1)
        product_after_fail = requests.get(f"{base_url}/api/products/{product_id}", timeout=30)
        assert product_after_fail.status_code == 200, product_after_fail.text
        assert product_after_fail.json()["stock"] == 1

        history = customer.get(f"{base_url}/api/orders", timeout=30)
        assert history.status_code == 200, history.text
        order_ids = [row["id"] for row in history.json()["items"]]
        assert order_data["id"] in order_ids
    finally:
        customer.delete(f"{base_url}/api/cart/items/{product_id}", timeout=30)
        admin_session.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)


def test_payment_config_public_safe_and_verify_mismatch_guard(base_url: str):
    """Public config never leaks secrets; verify endpoint rejects order mismatch before signature checks."""
    admin = _admin_login(base_url)
    customer = _register_customer(base_url)
    address_id = _create_address(customer, base_url)
    product = _create_admin_product(admin, base_url, stock=1)
    product_id = product["id"]

    try:
        public_config = requests.get(f"{base_url}/api/payment-config", timeout=30)
        assert public_config.status_code == 200, public_config.text
        config_data = public_config.json()
        assert "key_id" in config_data
        assert "razorpay_key_secret" not in config_data
        assert "razorpay_webhook_secret" not in config_data
        assert "key_secret" not in config_data

        customer.post(
            f"{base_url}/api/cart/items",
            json={"product_id": product_id, "quantity": 1},
            timeout=30,
        )
        order_response = customer.post(
            f"{base_url}/api/orders",
            json={"address_id": address_id, "payment_method": "upi"},
            timeout=30,
        )
        assert order_response.status_code == 201, order_response.text
        order_data = order_response.json()

        mismatch = customer.post(
            f"{base_url}/api/payments/razorpay/verify",
            json={
                "order_id": order_data["id"],
                "razorpay_order_id": "order_mismatch_iter16",
                "razorpay_payment_id": "pay_iter16_dummy123",
                "razorpay_signature": "dummy_signature_iter16",
            },
            timeout=30,
        )
        assert mismatch.status_code == 400, mismatch.text
        assert "mismatch" in mismatch.text.lower()
    finally:
        customer.delete(f"{base_url}/api/cart/items/{product_id}", timeout=30)
        admin.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)


def test_wishlist_add_remove_and_hash_target_data(base_url: str, admin_session: requests.Session):
    """Wishlist backend save/load/remove works for signed-in customer."""
    customer = _register_customer(base_url)
    product = _create_admin_product(admin_session, base_url, stock=2)
    product_id = product["id"]
    try:
        add = customer.put(f"{base_url}/api/wishlist/{product_id}", timeout=30)
        assert add.status_code == 204, add.text

        listed = customer.get(f"{base_url}/api/wishlist", timeout=30)
        assert listed.status_code == 200, listed.text
        ids = [row["id"] for row in listed.json()]
        assert product_id in ids

        remove = customer.delete(f"{base_url}/api/wishlist/{product_id}", timeout=30)
        assert remove.status_code == 204, remove.text

        listed_after = customer.get(f"{base_url}/api/wishlist", timeout=30)
        assert listed_after.status_code == 200, listed_after.text
        ids_after = [row["id"] for row in listed_after.json()]
        assert product_id not in ids_after
    finally:
        admin_session.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)


def test_admin_categories_and_category_filter_live_product(base_url: str, admin_session: requests.Session):
    """Admin categories are available for product creation and public category filter returns created product."""
    categories = admin_session.get(f"{base_url}/api/admin/categories", timeout=30)
    assert categories.status_code == 200, categories.text
    rows = categories.json()
    active_public = requests.get(f"{base_url}/api/categories", timeout=30)
    assert active_public.status_code == 200, active_public.text
    public_slugs = {row["slug"] for row in active_public.json()}

    assert len(rows) >= len(public_slugs)
    assert len(public_slugs) > 0
    selected_slug = sorted(public_slugs)[0]

    product = _create_admin_product(admin_session, base_url, stock=3, category_slug=selected_slug)
    product_id = product["id"]
    try:
        filtered = requests.get(f"{base_url}/api/products?category={selected_slug}&page_size=100", timeout=30)
        assert filtered.status_code == 200, filtered.text
        ids = [item["id"] for item in filtered.json()["items"]]
        assert product_id in ids
    finally:
        admin_session.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)


def test_admin_user_and_order_regressions(base_url: str, admin_session: requests.Session):
    """Admin users active/suspend API and admin order list/detail endpoints remain functional."""
    customer = _register_customer(base_url)

    me = customer.get(f"{base_url}/api/auth/me", timeout=30)
    assert me.status_code == 200, me.text
    user_id = me.json()["id"]

    users = admin_session.get(f"{base_url}/api/admin/users?role=customer", timeout=30)
    assert users.status_code == 200, users.text
    listed_ids = {row["id"] for row in users.json()}
    assert user_id in listed_ids

    suspend = admin_session.patch(f"{base_url}/api/admin/users/{user_id}", json={"active": False}, timeout=30)
    assert suspend.status_code == 200, suspend.text
    assert suspend.json()["active"] is False

    blocked_me = customer.get(f"{base_url}/api/auth/me", timeout=30)
    assert blocked_me.status_code == 401, blocked_me.text

    restore = admin_session.patch(f"{base_url}/api/admin/users/{user_id}", json={"active": True}, timeout=30)
    assert restore.status_code == 200, restore.text
    assert restore.json()["active"] is True

    # Re-login customer after suspension to refresh session validity.
    login = customer.post(
        f"{base_url}/api/auth/login",
        json={"identifier": me.json()["email"], "password": "TestPass123!"},
        timeout=30,
    )
    assert login.status_code == 200, login.text

    order_list = admin_session.get(f"{base_url}/api/orders", timeout=30)
    assert order_list.status_code == 200, order_list.text
    assert isinstance(order_list.json().get("items", []), list)

    if order_list.json()["items"]:
        order_id = order_list.json()["items"][0]["id"]
        order_detail = admin_session.get(f"{base_url}/api/orders/{order_id}", timeout=30)
        assert order_detail.status_code == 200, order_detail.text
        assert order_detail.json()["id"] == order_id