import uuid


# Admin section endpoint coverage for sidebar-backed routes
def test_admin_sidebar_endpoints_load(admin_session, base_url):
    endpoint_expectations = [
        ("/api/admin/dashboard", 200),
        ("/api/admin/users", 200),
        ("/api/admin/products?page_size=20", 200),
        ("/api/admin/categories", 200),
        ("/api/admin/orders/does-not-exist/status?status=packed", 404),
        ("/api/admin/payments", 200),
        ("/api/admin/auctions", 200),
        ("/api/admin/reports", 200),
        ("/api/admin/support-tickets", 200),
        ("/api/admin/returns", 200),
    ]

    for path, expected in endpoint_expectations:
        method = "PATCH" if "/orders/" in path else "GET"
        if method == "PATCH":
            response = admin_session.patch(f"{base_url}{path}", timeout=30)
        else:
            response = admin_session.get(f"{base_url}{path}", timeout=30)
        assert response.status_code == expected, f"{path} expected {expected}, got {response.status_code}"


# Generic admin managed-resources CRUD (create -> list/update -> delete)
def test_generic_resource_crud_and_cleanup(admin_session, base_url):
    resource = "campaigns"
    marker = f"TEST_CAMPAIGN_{uuid.uuid4().hex[:8]}"
    create_payload = {
        "title": marker,
        "description": "temporary regression campaign",
        "status": "active",
        "data": {"channel": "test", "priority": "low"},
    }

    created = admin_session.post(f"{base_url}/api/admin/resources/{resource}", json=create_payload, timeout=30)
    assert created.status_code == 201
    created_row = created.json()
    assert created_row["title"] == marker
    record_id = created_row["id"]

    listed = admin_session.get(f"{base_url}/api/admin/resources/{resource}?query={marker}", timeout=30)
    assert listed.status_code == 200
    listed_data = listed.json()
    assert any(item["id"] == record_id for item in listed_data["items"])

    update_payload = {
        "title": marker,
        "description": "temporary regression campaign",
        "status": "inactive",
        "data": {"channel": "test", "priority": "high"},
    }
    updated = admin_session.patch(
        f"{base_url}/api/admin/resources/{resource}/{record_id}",
        json=update_payload,
        timeout=30,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "inactive"

    deleted = admin_session.delete(f"{base_url}/api/admin/resources/{resource}/{record_id}", timeout=30)
    assert deleted.status_code == 204

    after_delete = admin_session.patch(
        f"{base_url}/api/admin/resources/{resource}/{record_id}",
        json=update_payload,
        timeout=30,
    )
    assert after_delete.status_code == 404


# AuthZ checks for admin generic resources and special admin groups
def test_unauthenticated_and_customer_admin_access_controls(anon_session, customer_session, base_url):
    unauth_admin_resource = anon_session.get(f"{base_url}/api/admin/resources/vendors", timeout=30)
    assert unauth_admin_resource.status_code == 401

    unauth_admin_users = anon_session.get(f"{base_url}/api/admin/users", timeout=30)
    assert unauth_admin_users.status_code == 401

    customer_admin_resource = customer_session.get(f"{base_url}/api/admin/resources/vendors", timeout=30)
    assert customer_admin_resource.status_code == 403

    customer_admin_reports = customer_session.get(f"{base_url}/api/admin/reports", timeout=30)
    assert customer_admin_reports.status_code == 403


# Public content visibility rules for allowed resources + status filtering
def test_public_content_exposes_allowed_active_and_published_records_only(admin_session, anon_session, base_url):
    resource = "brands"
    active_title = f"TEST_BRAND_ACTIVE_{uuid.uuid4().hex[:6]}"
    inactive_title = f"TEST_BRAND_INACTIVE_{uuid.uuid4().hex[:6]}"

    active_created = admin_session.post(
        f"{base_url}/api/admin/resources/{resource}",
        json={"title": active_title, "description": "visible", "status": "active", "data": {"slug": active_title.lower()}},
        timeout=30,
    )
    assert active_created.status_code == 201
    active_id = active_created.json()["id"]

    inactive_created = admin_session.post(
        f"{base_url}/api/admin/resources/{resource}",
        json={"title": inactive_title, "description": "hidden", "status": "inactive", "data": {"slug": inactive_title.lower()}},
        timeout=30,
    )
    assert inactive_created.status_code == 201
    inactive_id = inactive_created.json()["id"]

    public_rows = anon_session.get(f"{base_url}/api/content/{resource}", timeout=30)
    assert public_rows.status_code == 200
    content = public_rows.json()
    titles = [row["title"] for row in content]
    assert active_title in titles
    assert inactive_title not in titles

    forbidden_resource = anon_session.get(f"{base_url}/api/content/vendors", timeout=30)
    assert forbidden_resource.status_code == 404

    admin_session.delete(f"{base_url}/api/admin/resources/{resource}/{active_id}", timeout=30)
    admin_session.delete(f"{base_url}/api/admin/resources/{resource}/{inactive_id}", timeout=30)


# Public content endpoints should be available only for allowed resources
def test_public_content_allowed_resources_are_reachable(anon_session, base_url):
    for resource in ["brands", "campaigns", "coupons", "banners", "shipping"]:
        response = anon_session.get(f"{base_url}/api/content/{resource}", timeout=30)
        assert response.status_code == 200
        rows = response.json()
        assert isinstance(rows, list)
        for row in rows:
            assert row["status"] in ["active", "published"]


# Admin workflow actions for orders/payments/auctions/returns/support using generated data
def test_admin_workflow_actions_with_generated_data(customer_session, admin_session, base_url):
    # Create customer order prerequisites
    address = customer_session.post(
        f"{base_url}/api/auth/me/addresses",
        json={
            "label": "TEST_WORKFLOW",
            "recipient_name": "Workflow User",
            "phone": "+919900000001",
            "line1": "Workflow Street 1",
            "line2": "",
            "city": "Delhi",
            "state": "Delhi",
            "postal_code": "110001",
            "country": "India",
        },
        timeout=30,
    )
    assert address.status_code == 201
    address_id = address.json()["id"]

    products = customer_session.get(f"{base_url}/api/products?page=1&page_size=1", timeout=30)
    assert products.status_code == 200
    product = products.json()["items"][0]

    add_cart = customer_session.post(
        f"{base_url}/api/cart/items",
        json={"product_id": product["id"], "quantity": 1},
        timeout=30,
    )
    assert add_cart.status_code == 200

    created_order = customer_session.post(
        f"{base_url}/api/orders",
        json={"address_id": address_id, "payment_method": "upi"},
        timeout=30,
    )
    assert created_order.status_code == 201
    order = created_order.json()

    packed = admin_session.patch(
        f"{base_url}/api/admin/orders/{order['id']}/status?status=packed",
        timeout=30,
    )
    assert packed.status_code == 200
    assert packed.json()["status"] == "packed"

    captured = admin_session.patch(
        f"{base_url}/api/admin/payments/{order['id']}",
        json={"status": "captured", "transaction_id": f"TEST_TXN_{uuid.uuid4().hex[:8]}"},
        timeout=30,
    )
    assert captured.status_code == 200
    assert captured.json()["payment"]["status"] == "captured"

    created_return = customer_session.post(
        f"{base_url}/api/returns",
        json={
            "title": "TEST Return",
            "description": "Requesting return",
            "status": "requested",
            "data": {"order_id": order["id"], "reason": "test"},
        },
        timeout=30,
    )
    assert created_return.status_code == 201
    return_row = created_return.json()

    approved = admin_session.patch(
        f"{base_url}/api/admin/returns/{return_row['id']}",
        json={
            "title": return_row["title"],
            "description": return_row["description"],
            "status": "approved",
            "data": return_row["data"],
        },
        timeout=30,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    created_ticket = customer_session.post(
        f"{base_url}/api/support/tickets",
        json={"title": "TEST Ticket", "description": "Need help", "status": "open", "data": {"topic": "workflow"}},
        timeout=30,
    )
    assert created_ticket.status_code == 201
    ticket = created_ticket.json()

    resolved = admin_session.patch(
        f"{base_url}/api/admin/support-tickets/{ticket['id']}",
        json={
            "title": ticket["title"],
            "description": ticket["description"],
            "status": "resolved",
            "data": ticket["data"],
        },
        timeout=30,
    )
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"

    created_auction = admin_session.post(
        f"{base_url}/api/admin/auctions",
        json={
            "product_id": product["id"],
            "starting_price": 1234,
            "bid_increment": 100,
            "starts_at": "2025-01-01T00:00:00+00:00",
            "ends_at": "2030-01-01T00:00:00+00:00",
        },
        timeout=30,
    )
    assert created_auction.status_code == 201
    auction = created_auction.json()

    closed = admin_session.post(f"{base_url}/api/admin/auctions/{auction['id']}/close", timeout=30)
    assert closed.status_code == 200
    assert closed.json()["status"] == "closed"


# Admin user active-state controls should return active flag for UI correctness
def test_admin_user_toggle_response_contains_active_field(customer_session, admin_session, base_url):
    me = customer_session.get(f"{base_url}/api/auth/me", timeout=30)
    assert me.status_code == 200
    customer_id = me.json()["id"]

    toggled = admin_session.patch(
        f"{base_url}/api/admin/users/{customer_id}",
        json={"active": False},
        timeout=30,
    )
    assert toggled.status_code == 200
    payload = toggled.json()
    assert "active" in payload, "Admin user update response is missing 'active'; UI cannot reflect state changes"

    # Restore test user even if active field is missing in response
    admin_session.patch(
        f"{base_url}/api/admin/users/{customer_id}",
        json={"active": True},
        timeout=30,
    )
