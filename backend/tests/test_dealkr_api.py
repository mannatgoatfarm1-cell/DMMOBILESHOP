import io


def test_health_and_catalog_load(anon_session, base_url):
    # Health + storefront catalog validation
    health = anon_session.get(f"{base_url}/api/health", timeout=30)
    assert health.status_code == 200
    assert health.json().get("status") == "ok"

    products = anon_session.get(f"{base_url}/api/products?page=1&page_size=6", timeout=30)
    assert products.status_code == 200
    data = products.json()
    assert isinstance(data.get("items"), list)
    assert data.get("total", 0) >= len(data["items"])
    assert len(data["items"]) > 0


def test_search_filter_pagination(anon_session, base_url):
    # Search/filter/pagination API behavior
    searched = anon_session.get(f"{base_url}/api/products?query=iphone&page=1&page_size=2&sort=price_desc", timeout=30)
    assert searched.status_code == 200
    s_data = searched.json()
    assert s_data["page"] == 1
    assert s_data["page_size"] == 2
    assert s_data["pages"] >= 1

    filtered = anon_session.get(f"{base_url}/api/products?category=mobiles&min_price=1000&max_price=200000", timeout=30)
    assert filtered.status_code == 200
    f_data = filtered.json()
    assert isinstance(f_data["items"], list)
    for row in f_data["items"]:
        assert row["category_slug"] == "mobiles"
        assert 1000 <= row["price"] <= 200000


def test_login_sets_http_only_cookies(anon_session, base_url, customer_credentials):
    # Login cookie security headers
    anon_session.post(f"{base_url}/api/auth/register", json=customer_credentials, timeout=30)
    login = anon_session.post(
        f"{base_url}/api/auth/login",
        json={"email": customer_credentials["email"], "password": customer_credentials["password"]},
        timeout=30,
    )
    assert login.status_code == 200
    set_cookie = login.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie


def test_private_routes_require_auth_and_customer_gets_403(anon_session, customer_session, base_url):
    # Access control checks (401/403)
    unauth_cart = anon_session.get(f"{base_url}/api/cart", timeout=30)
    assert unauth_cart.status_code == 401

    customer_admin = customer_session.get(f"{base_url}/api/admin/dashboard", timeout=30)
    assert customer_admin.status_code == 403


def test_customer_address_cart_order_history_flow(customer_session, base_url):
    # Customer profile/address/cart/order workflow
    me = customer_session.get(f"{base_url}/api/auth/me", timeout=30)
    assert me.status_code == 200
    user = me.json()
    assert user["role"] == "customer"

    address_payload = {
        "label": "TEST_HOME",
        "recipient_name": "TEST Receiver",
        "phone": "+919876543210",
        "line1": "123 TEST Street",
        "line2": "",
        "city": "Delhi",
        "state": "Delhi",
        "postal_code": "110001",
        "country": "India",
    }
    addr = customer_session.post(f"{base_url}/api/auth/me/addresses", json=address_payload, timeout=30)
    assert addr.status_code == 201
    address = addr.json()
    assert address["label"] == "TEST_HOME"

    products = customer_session.get(f"{base_url}/api/products?page=1&page_size=1", timeout=30)
    assert products.status_code == 200
    product = products.json()["items"][0]

    add_cart = customer_session.post(
        f"{base_url}/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        timeout=30,
    )
    assert add_cart.status_code == 200
    assert add_cart.json()["item_count"] >= 1

    patch_cart = customer_session.patch(
        f"{base_url}/api/cart/items/{product['id']}",
        json={"product_id": product["id"], "quantity": 2},
        timeout=30,
    )
    assert patch_cart.status_code == 200

    order = customer_session.post(
        f"{base_url}/api/orders",
        json={"address_id": address["id"], "payment_method": "cod"},
        timeout=30,
    )
    assert order.status_code == 201
    order_data = order.json()
    assert order_data["payment"]["method"] == "cod"
    assert order_data["payment"]["status"] == "cash_on_delivery"

    history = customer_session.get(f"{base_url}/api/orders", timeout=30)
    assert history.status_code == 200
    assert any(row["id"] == order_data["id"] for row in history.json()["items"])

    remove_result = customer_session.delete(f"{base_url}/api/cart/items/{product['id']}", timeout=30)
    assert remove_result.status_code == 204


def test_auction_list_bid_and_bid_history(customer_session, base_url):
    # Auction listing, bid placement, and bid history
    auctions = customer_session.get(f"{base_url}/api/auctions", timeout=30)
    assert auctions.status_code == 200
    rows = auctions.json()
    assert isinstance(rows, list)
    assert len(rows) > 0

    auction = rows[0]
    amount = auction["current_bid"] + auction["bid_increment"]
    bid = customer_session.post(
        f"{base_url}/api/auctions/{auction['id']}/bids",
        json={"amount": amount},
        timeout=30,
    )
    assert bid.status_code == 201
    b_data = bid.json()
    assert b_data["amount"] == amount

    history = customer_session.get(f"{base_url}/api/auctions/{auction['id']}/bids", timeout=30)
    assert history.status_code == 200
    h_data = history.json()
    assert any(item["id"] == b_data["id"] for item in h_data)


def test_admin_login_dashboard_and_protected_endpoints(anon_session, admin_session, base_url):
    # Admin auth and role-protected endpoint checks
    unauth_products = anon_session.get(f"{base_url}/api/admin/products", timeout=30)
    assert unauth_products.status_code == 401

    unauth_upload = anon_session.post(
        f"{base_url}/api/admin/uploads",
        files={"file": ("x.txt", b"x", "text/plain")},
        timeout=30,
    )
    assert unauth_upload.status_code == 401

    dashboard = admin_session.get(f"{base_url}/api/admin/dashboard", timeout=30)
    assert dashboard.status_code == 200
    d_data = dashboard.json()
    assert "metrics" in d_data
    assert "total_products" in d_data["metrics"]

    admin_products = admin_session.get(f"{base_url}/api/admin/products?page=1&page_size=5", timeout=30)
    assert admin_products.status_code == 200
    p_data = admin_products.json()
    assert isinstance(p_data["items"], list)


def test_upload_rejects_non_image_for_admin(admin_session, base_url):
    # Upload validation checks
    bad_upload = admin_session.post(
        f"{base_url}/api/admin/uploads",
        files={"file": ("invalid.txt", io.BytesIO(b"abc"), "text/plain")},
        timeout=30,
    )
    assert bad_upload.status_code == 415


def test_admin_category_order_auction_authz_and_success(anon_session, admin_session, base_url):
    # Admin category/product/order/auction endpoint auth and success checks
    import time

    unauth_category = anon_session.post(
        f"{base_url}/api/admin/categories",
        json={"name": "Blocked", "slug": f"blocked-{int(time.time())}", "active": True},
        timeout=30,
    )
    assert unauth_category.status_code == 401

    unauth_order_update = anon_session.patch(
        f"{base_url}/api/admin/orders/any-id/status?status=packed",
        timeout=30,
    )
    assert unauth_order_update.status_code == 401

    unauth_auction = anon_session.post(
        f"{base_url}/api/admin/auctions",
        json={"product_id": "iphone", "starting_price": 1000, "bid_increment": 100, "starts_at": "2026-01-01T00:00:00+00:00", "ends_at": "2026-01-02T00:00:00+00:00"},
        timeout=30,
    )
    assert unauth_auction.status_code == 401

    slug = f"test-cat-{int(time.time())}"
    created_category = admin_session.post(
        f"{base_url}/api/admin/categories",
        json={"name": "Test Category", "slug": slug, "image": None, "active": True},
        timeout=30,
    )
    assert created_category.status_code == 201
    category = created_category.json()
    assert category["slug"] == slug

    product_slug = f"test-prod-{int(time.time())}"
    created_product = admin_session.post(
        f"{base_url}/api/admin/products",
        json={
            "name": "TEST Product",
            "slug": product_slug,
            "sub": "TEST sub",
            "description": "TEST description",
            "category_slug": slug,
            "price": 999,
            "original_price": 1299,
            "stock": 10,
            "images": ["https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=600&q=80"],
            "tag": "DEAL",
            "variants": [],
            "active": True,
            "featured": False,
        },
        timeout=30,
    )
    assert created_product.status_code == 201
    product = created_product.json()
    assert product["slug"] == product_slug

    starts_at = "2026-01-01T00:00:00+00:00"
    ends_at = "2030-01-02T00:00:00+00:00"
    created_auction = admin_session.post(
        f"{base_url}/api/admin/auctions",
        json={"product_id": product["id"], "starting_price": 500, "bid_increment": 50, "starts_at": starts_at, "ends_at": ends_at},
        timeout=30,
    )
    assert created_auction.status_code == 201
    auction = created_auction.json()
    assert auction["product_id"] == product["id"]

    orders = admin_session.get(f"{base_url}/api/orders", timeout=30)
    assert orders.status_code == 200
    order_rows = orders.json()["items"]
    assert isinstance(order_rows, list)
    if order_rows:
        update_status = admin_session.patch(
            f"{base_url}/api/admin/orders/{order_rows[0]['id']}/status?status=packed",
            timeout=30,
        )
        assert update_status.status_code == 200
        assert update_status.json()["status"] == "packed"


def test_brute_force_lockout_after_five_failures(anon_session, base_url):
    # Auth brute-force lockout behavior
    import uuid

    email = f"test_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"
    register = anon_session.post(
        f"{base_url}/api/auth/register",
        json={"name": "TEST Lock", "email": email, "password": password},
        timeout=30,
    )
    assert register.status_code == 201

    anon_session.post(f"{base_url}/api/auth/logout", timeout=30)

    for _ in range(5):
        r = anon_session.post(
            f"{base_url}/api/auth/login",
            json={"email": email, "password": "wrong-password"},
            timeout=30,
        )
        assert r.status_code == 401

    locked = anon_session.post(
        f"{base_url}/api/auth/login",
        json={"email": email, "password": password},
        timeout=30,
    )
    assert locked.status_code == 429
