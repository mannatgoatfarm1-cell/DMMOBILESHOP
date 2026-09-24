import uuid
from datetime import datetime, timedelta, timezone

import pytest


# Auth/session/CORS and admin auction lifecycle regression checks


def _iso(offset_hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=offset_hours)).isoformat()


def _active_category_slug(admin_session, base_url: str) -> str:
    response = admin_session.get(f"{base_url}/api/admin/categories", timeout=30)
    assert response.status_code == 200, response.text
    categories = response.json()
    assert isinstance(categories, list) and categories, "No categories available for product creation"
    active = next((category for category in categories if category.get("active") is True), categories[0])
    return active["slug"]


def _create_disposable_product(admin_session, base_url: str, *, active: bool = True) -> dict:
    unique = uuid.uuid4().hex[:10]
    slug = f"test-auction-i19-{unique}"
    payload = {
        "name": f"TEST Auction Product {unique}",
        "slug": slug,
        "sub": "Disposable test product",
        "description": "Created by pytest for admin auction regression.",
        "category_slug": _active_category_slug(admin_session, base_url),
        "price": 25000,
        "original_price": 30000,
        "stock": 5,
        "images": ["https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=800&q=85"],
        "tag": "TEST",
        "variants": [],
        "active": active,
        "featured": False,
        "qc_grade": "new",
        "qc_status": {},
        "imei_number": "",
        "barcode": "",
        "warranty_days": 0,
    }
    response = admin_session.post(f"{base_url}/api/admin/products", json=payload, timeout=30)
    assert response.status_code == 201, response.text
    return response.json()


def _delete_product(admin_session, base_url: str, product_id: str) -> None:
    admin_session.delete(f"{base_url}/api/admin/products/{product_id}", timeout=30)


class TestIteration19AuthPlaybookChecks:
    def test_login_sets_secure_httponly_cookies(self, base_url: str):
        session = __import__("requests").Session()
        response = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "deepak143", "password": "deepak143"},
            timeout=30,
        )
        assert response.status_code == 200, response.text
        set_cookie = response.headers.get("set-cookie", "")
        assert "HttpOnly" in set_cookie
        assert "Secure" in set_cookie
        assert "samesite=none" in set_cookie.lower()

    def test_login_cors_preflight_allows_credentials(self, base_url: str):
        session = __import__("requests").Session()
        headers = {
            "Origin": base_url,
        }
        response = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": "deepak143", "password": "deepak143"},
            headers=headers,
            timeout=30,
        )
        assert response.status_code == 200, response.text
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert response.headers.get("access-control-allow-origin") in [base_url, f"{base_url}/"]

    def test_bruteforce_lockout_after_five_failures(self, base_url: str):
        session = __import__("requests").Session()
        identifier = f"test-lockout-{uuid.uuid4().hex[:8]}"
        for _ in range(5):
            response = session.post(
                f"{base_url}/api/auth/login",
                json={"identifier": identifier, "password": "wrong-password"},
                timeout=30,
            )
            assert response.status_code == 401
        sixth = session.post(
            f"{base_url}/api/auth/login",
            json={"identifier": identifier, "password": "wrong-password"},
            timeout=30,
        )
        assert sixth.status_code == 429, sixth.text


class TestIteration19AdminAuctions:
    def test_admin_auctions_list_shape(self, admin_session, base_url: str):
        response = admin_session.get(f"{base_url}/api/admin/auctions", timeout=30)
        assert response.status_code == 200, response.text
        auctions = response.json()
        assert isinstance(auctions, list)
        if auctions:
            first = auctions[0]
            assert isinstance(first.get("bid_count"), int)
            assert first.get("product") is None or isinstance(first["product"], dict)

    def test_create_auction_validates_end_after_start(self, admin_session, base_url: str):
        product = _create_disposable_product(admin_session, base_url, active=True)
        try:
            response = admin_session.post(
                f"{base_url}/api/admin/auctions",
                json={
                    "product_id": product["id"],
                    "starting_price": 100,
                    "bid_increment": 50,
                    "starts_at": _iso(4),
                    "ends_at": _iso(1),
                },
                timeout=30,
            )
            assert response.status_code == 422
        finally:
            _delete_product(admin_session, base_url, product["id"])

    def test_create_auction_rejects_inactive_product_expected(self, admin_session, base_url: str):
        inactive_product = _create_disposable_product(admin_session, base_url, active=False)
        created_auction_id = None
        try:
            response = admin_session.post(
                f"{base_url}/api/admin/auctions",
                json={
                    "product_id": inactive_product["id"],
                    "starting_price": 500,
                    "bid_increment": 50,
                    "starts_at": _iso(0),
                    "ends_at": _iso(2),
                },
                timeout=30,
            )
            if response.status_code == 201:
                created_auction_id = response.json().get("id")
            assert response.status_code == 422, response.text
        finally:
            if created_auction_id:
                admin_session.post(f"{base_url}/api/admin/auctions/{created_auction_id}/close", timeout=30)
            _delete_product(admin_session, base_url, inactive_product["id"])

    def test_create_live_auction_bid_close_and_repeat_close_safely(self, admin_session, customer_session, base_url: str):
        product = _create_disposable_product(admin_session, base_url, active=True)
        auction_id = None
        try:
            create_response = admin_session.post(
                f"{base_url}/api/admin/auctions",
                json={
                    "product_id": product["id"],
                    "starting_price": 1200,
                    "bid_increment": 100,
                    "starts_at": _iso(-1),
                    "ends_at": _iso(4),
                },
                timeout=30,
            )
            assert create_response.status_code == 201, create_response.text
            auction = create_response.json()
            auction_id = auction["id"]
            assert auction["status"] in ["live", "upcoming"]

            public_live = customer_session.get(f"{base_url}/api/auctions?status=live", timeout=30)
            assert public_live.status_code == 200, public_live.text
            live_ids = {row["id"] for row in public_live.json()}
            assert auction_id in live_ids

            bid_response = customer_session.post(
                f"{base_url}/api/auctions/{auction_id}/bids",
                json={"amount": 1300},
                timeout=30,
            )
            assert bid_response.status_code == 201, bid_response.text
            bid = bid_response.json()
            assert bid["auction_id"] == auction_id
            assert bid["amount"] == 1300

            close_response = admin_session.post(f"{base_url}/api/admin/auctions/{auction_id}/close", timeout=30)
            assert close_response.status_code == 200, close_response.text
            closed = close_response.json()
            assert closed["status"] == "closed"
            assert closed["winner_user_id"] == bid["user_id"]

            close_again = admin_session.post(f"{base_url}/api/admin/auctions/{auction_id}/close", timeout=30)
            assert close_again.status_code in [200, 409], close_again.text
            if close_again.status_code == 200:
                second = close_again.json()
                assert second["status"] == "closed"
        finally:
            if auction_id:
                admin_session.post(f"{base_url}/api/admin/auctions/{auction_id}/close", timeout=30)
            _delete_product(admin_session, base_url, product["id"])
