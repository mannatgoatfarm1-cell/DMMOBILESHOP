import os
import time
import uuid
from pathlib import Path

import pytest
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


@pytest.fixture
def live_test_context(admin_session, base_url: str):
    # Admin product + announcement live-sync flow setup/teardown
    marker = uuid.uuid4().hex[:8]
    slug = f"test-live-{marker}"
    product_payload = {
        "name": f"TEST Live Sync {marker}",
        "slug": slug,
        "sub": "Temporary live sync validation item",
        "description": "Temporary test product for live sync verification",
        "category_slug": "mobiles",
        "price": 32123,
        "original_price": 39999,
        "stock": 5,
        "images": [
            "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?auto=format&fit=crop&w=800&q=85"
        ],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
    }

    create = admin_session.post(f"{base_url}/api/admin/products", json=product_payload, timeout=40)
    assert create.status_code == 201, create.text
    product = create.json()

    ctx = {
        "marker": marker,
        "slug": slug,
        "product_id": product["id"],
        "product_name": product_payload["name"],
        "explicit_announcement_id": None,
        "auto_announcement_id": None,
    }

    # Find auto-announcement id for cleanup validation
    announcement_rows = admin_session.get(
        f"{base_url}/api/admin/resources/announcements?page_size=100", timeout=30
    )
    if announcement_rows.status_code == 200:
        for row in announcement_rows.json().get("items", []):
            if row.get("title") == f"New arrival: {ctx['product_name']}":
                ctx["auto_announcement_id"] = row.get("id")
                break

    try:
        yield ctx
    finally:
        # Soft cleanup product from storefront
        admin_session.delete(f"{base_url}/api/admin/products/{ctx['product_id']}", timeout=30)

        # Cleanup created announcements if present
        if ctx.get("explicit_announcement_id"):
            admin_session.delete(
                f"{base_url}/api/admin/resources/announcements/{ctx['explicit_announcement_id']}",
                timeout=30,
            )
        if ctx.get("auto_announcement_id"):
            admin_session.delete(
                f"{base_url}/api/admin/resources/announcements/{ctx['auto_announcement_id']}",
                timeout=30,
            )


# Auth/security module: cookie flags, bcrypt format, brute-force lockout wrong-attempt gating.
def test_auth_cookie_bcrypt_and_lockout_basics(base_url: str, mongo_db):
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

    deepak = mongo_db.users.find_one({"username": "deepak143"}, {"_id": 0, "password_hash": 1})
    assert deepak is not None
    assert str(deepak["password_hash"]).startswith("$2b$")

    ident = f"test_iter11_lock_{uuid.uuid4().hex[:8]}@example.com"
    password = "Passw0rd!234"
    register = session.post(
        f"{base_url}/api/auth/register",
        json={"name": "TEST Iter11", "email": ident, "password": password, "confirm_password": password},
        timeout=30,
    )
    assert register.status_code == 201, register.text
    session.post(f"{base_url}/api/auth/logout", timeout=30)

    for _ in range(5):
        wrong = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": ident, "password": "WrongPass!999"},
            timeout=30,
        )
        assert wrong.status_code == 401, wrong.text

    sixth_wrong = session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": ident, "password": "WrongPass!999"},
        timeout=30,
    )
    assert sixth_wrong.status_code == 429, sixth_wrong.text

    mongo_db.users.delete_one({"email": ident})
    mongo_db.login_attempts.delete_one({"identifier": ident})


# Live catalog + announcement module: admin-created active product must surface quickly in public APIs.
def test_live_product_and_auto_announcement_visibility_within_2_seconds(base_url: str, admin_session, live_test_context):
    deadline = time.time() + 2.0
    product_visible = False
    announcement_visible = False

    while time.time() < deadline and (not product_visible or not announcement_visible):
        if not product_visible:
            products = admin_session.get(
                f"{base_url}/api/products?category=mobiles&page_size=100&_live={int(time.time()*1000)}",
                timeout=30,
            )
            assert products.status_code == 200, products.text
            items = products.json().get("items", [])
            product_visible = any(item.get("id") == live_test_context["product_id"] for item in items)

        if not announcement_visible:
            announcements = admin_session.get(
                f"{base_url}/api/content/announcements?_live={int(time.time()*1000)}",
                timeout=30,
            )
            assert announcements.status_code == 200, announcements.text
            rows = announcements.json()
            expected_title = f"New arrival: {live_test_context['product_name']}"
            announcement_visible = any(row.get("title") == expected_title for row in rows)

        if not product_visible or not announcement_visible:
            time.sleep(0.35)

    assert product_visible is True
    assert announcement_visible is True


# Product update/publish module: edits + publish toggles reflect quickly in public APIs.
def test_admin_product_edit_and_publish_unpublish_reflects_public_data(base_url: str, admin_session, live_test_context):
    edited_name = f"TEST Live Sync Edited {live_test_context['marker']}"
    edited_price = 33333

    existing = admin_session.get(f"{base_url}/api/admin/products?page_size=200", timeout=30)
    assert existing.status_code == 200, existing.text
    target = next((item for item in existing.json()["items"] if item["id"] == live_test_context["product_id"]), None)
    assert target is not None

    update_payload = {
        "name": edited_name,
        "slug": target["slug"],
        "sub": target.get("sub", ""),
        "description": target.get("description", ""),
        "category_slug": target["category_slug"],
        "price": edited_price,
        "original_price": target["original_price"],
        "stock": target["stock"],
        "images": target["images"],
        "tag": target.get("tag", "DEAL"),
        "variants": target.get("variants", []),
        "active": True,
        "featured": target.get("featured", False),
    }

    update = admin_session.patch(
        f"{base_url}/api/admin/products/{live_test_context['product_id']}",
        json=update_payload,
        timeout=30,
    )
    assert update.status_code == 200, update.text
    assert update.json()["name"] == edited_name
    assert update.json()["price"] == edited_price

    deadline = time.time() + 2.0
    reflected = False
    while time.time() < deadline and not reflected:
        public_product = admin_session.get(
            f"{base_url}/api/products/{live_test_context['product_id']}?_live={int(time.time()*1000)}",
            timeout=30,
        )
        if public_product.status_code == 200:
            payload = public_product.json()
            reflected = payload.get("name") == edited_name and payload.get("price") == edited_price
        if not reflected:
            time.sleep(0.35)
    assert reflected is True

    unpublish = admin_session.delete(f"{base_url}/api/admin/products/{live_test_context['product_id']}", timeout=30)
    assert unpublish.status_code == 204, unpublish.text

    hidden = admin_session.get(f"{base_url}/api/products/{live_test_context['product_id']}", timeout=30)
    assert hidden.status_code == 404, hidden.text

    republish = admin_session.patch(
        f"{base_url}/api/admin/products/{live_test_context['product_id']}",
        json={**update_payload, "active": True},
        timeout=30,
    )
    assert republish.status_code == 200, republish.text
    assert republish.json()["active"] is True


# Admin announcements module: add/update/publish controls and public content exposure.
def test_admin_announcements_crud_and_public_content(base_url: str, admin_session, live_test_context):
    marker = live_test_context["marker"]
    create_payload = {
        "title": f"TEST Announcement {marker}",
        "description": "Temporary announcement for regression",
        "status": "draft",
        "data": {"code": f"ANN-{marker}"},
    }
    created = admin_session.post(
        f"{base_url}/api/admin/resources/announcements",
        json=create_payload,
        timeout=30,
    )
    assert created.status_code == 201, created.text
    row = created.json()
    live_test_context["explicit_announcement_id"] = row["id"]
    assert row["title"] == create_payload["title"]
    assert row["status"] == "draft"

    publish_payload = {
        "title": f"TEST Announcement {marker} Updated",
        "description": "Published announcement",
        "status": "published",
        "data": {"code": f"ANN-{marker}-UPD"},
    }
    updated = admin_session.patch(
        f"{base_url}/api/admin/resources/announcements/{row['id']}",
        json=publish_payload,
        timeout=30,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["status"] == "published"
    assert updated.json()["title"] == publish_payload["title"]

    public_rows = admin_session.get(
        f"{base_url}/api/content/announcements?_live={int(time.time()*1000)}",
        timeout=30,
    )
    assert public_rows.status_code == 200, public_rows.text
    titles = [entry.get("title") for entry in public_rows.json()]
    assert publish_payload["title"] in titles


# CORS/auth module: preflight must keep credentials and explicit origin on auth endpoint.
def test_auth_preflight_origin_and_credentials_headers(base_url: str):
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
    assert preflight.headers.get("access-control-allow-origin") == "https://dashboard-design-20.preview.emergentagent.com"