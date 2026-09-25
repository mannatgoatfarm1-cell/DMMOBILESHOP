import uuid
from datetime import datetime, timedelta, timezone

import pytest
import requests


# Auction hub + live bidding regression checks for iteration 22


def _iso(delta_hours: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(hours=delta_hours)).isoformat()


def _request_with_retry(session: requests.Session, method: str, url: str, **kwargs):
    last_error = None
    for _ in range(3):
        try:
            response = session.request(method, url, **kwargs)
            if response.status_code != 503:
                return response
        except requests.RequestException as error:
            last_error = error
    if last_error:
        raise last_error
    return response


def _active_category_slug(admin_session: requests.Session, base_url: str) -> str:
    response = _request_with_retry(admin_session, "GET", f"{base_url}/api/admin/categories", timeout=30)
    assert response.status_code == 200, response.text
    categories = response.json()
    assert isinstance(categories, list) and categories
    active = next((category for category in categories if category.get("active") is True), categories[0])
    return active["slug"]


def _create_disposable_product(admin_session: requests.Session, base_url: str) -> dict:
    unique = uuid.uuid4().hex[:8]
    payload = {
        "name": f"TEST Auction Hub {unique}",
        "slug": f"test-auction-hub-{unique}",
        "sub": "Disposable auction regression product",
        "description": "Temporary product for auction regression coverage",
        "category_slug": _active_category_slug(admin_session, base_url),
        "price": 23000,
        "original_price": 28000,
        "stock": 3,
        "images": ["https://images.unsplash.com/photo-1546868871-7041f2a55e12?auto=format&fit=crop&w=800&q=85"],
        "tag": "TEST",
        "variants": [],
        "active": True,
        "featured": False,
        "qc_grade": "new",
        "qc_status": {},
        "imei_number": "",
        "barcode": "",
        "warranty_days": 0,
    }
    response = _request_with_retry(admin_session, "POST", f"{base_url}/api/admin/products", json=payload, timeout=30)
    assert response.status_code == 201, response.text
    return response.json()


def _create_auction(admin_session: requests.Session, base_url: str, product_id: str, starts_at: str, ends_at: str) -> dict:
    response = _request_with_retry(
        admin_session,
        "POST",
        f"{base_url}/api/admin/auctions",
        json={
            "product_id": product_id,
            "starting_price": 1000,
            "bid_increment": 100,
            "starts_at": starts_at,
            "ends_at": ends_at,
        },
        timeout=30,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _cleanup(admin_session: requests.Session, base_url: str, auction_id: str | None, product_id: str | None) -> None:
    if auction_id:
        _request_with_retry(admin_session, "POST", f"{base_url}/api/admin/auctions/{auction_id}/close", timeout=30)
    if product_id:
        _request_with_retry(admin_session, "DELETE", f"{base_url}/api/admin/products/{product_id}", timeout=30)


class TestIteration22AuctionExperienceBackend:
    def test_live_auctions_have_future_end_time(self, anon_session: requests.Session, base_url: str):
        response = anon_session.get(f"{base_url}/api/auctions?status=live", timeout=30)
        assert response.status_code == 200, response.text
        auctions = response.json()
        now_utc = datetime.now(timezone.utc)
        for auction in auctions:
            ends_at = datetime.fromisoformat(auction["ends_at"])
            assert ends_at > now_utc

    def test_expired_live_auction_is_reconciled_to_closed(self, admin_session: requests.Session, anon_session: requests.Session, base_url: str):
        product_id = None
        auction_id = None
        try:
            product = _create_disposable_product(admin_session, base_url)
            product_id = product["id"]
            created = _create_auction(admin_session, base_url, product_id, starts_at=_iso(-4), ends_at=_iso(-1))
            auction_id = created["id"]

            public_live = anon_session.get(f"{base_url}/api/auctions?status=live", timeout=30)
            assert public_live.status_code == 200, public_live.text
            live_ids = {row["id"] for row in public_live.json()}
            assert auction_id not in live_ids

            admin_rows = admin_session.get(f"{base_url}/api/admin/auctions", timeout=30)
            assert admin_rows.status_code == 200, admin_rows.text
            matched = next((row for row in admin_rows.json() if row["id"] == auction_id), None)
            assert matched is not None
            assert matched["status"] == "closed"
        finally:
            _cleanup(admin_session, base_url, auction_id, product_id)

    def test_live_auction_payload_supports_frontend_filters(self, anon_session: requests.Session, base_url: str):
        response = anon_session.get(f"{base_url}/api/auctions?status=live", timeout=30)
        assert response.status_code == 200, response.text
        rows = response.json()
        for row in rows:
            assert isinstance(row.get("current_bid"), int)
            assert isinstance(row.get("bid_increment"), int)
            assert isinstance(row.get("bid_count"), int)
            assert row.get("product") is None or isinstance(row["product"].get("category_slug"), str)
            if row.get("product"):
                assert row["product"].get("qc_grade") in ["new", "excellent", "good", "fair"]

    def test_customer_can_place_valid_bid_and_bid_history_updates(self, admin_session: requests.Session, base_url: str):
        product_id = None
        auction_id = None
        customer = requests.Session()
        try:
            product = _create_disposable_product(admin_session, base_url)
            product_id = product["id"]
            auction = _create_auction(admin_session, base_url, product_id, starts_at=_iso(-1), ends_at=_iso(3))
            auction_id = auction["id"]

            login = customer.post(
                f"{base_url}/api/auth/login",
                json={"identifier": "p0check_1790113956@example.com", "password": "TestPass123!"},
                timeout=30,
            )
            assert login.status_code == 200, login.text

            too_low = customer.post(
                f"{base_url}/api/auctions/{auction_id}/bids",
                json={"amount": auction["current_bid"]},
                timeout=30,
            )
            assert too_low.status_code == 409, too_low.text

            valid_amount = auction["current_bid"] + auction["bid_increment"]
            valid = customer.post(
                f"{base_url}/api/auctions/{auction_id}/bids",
                json={"amount": valid_amount},
                timeout=30,
            )
            assert valid.status_code == 201, valid.text
            bid = valid.json()
            assert bid["auction_id"] == auction_id
            assert bid["amount"] == valid_amount

            updated = customer.get(f"{base_url}/api/auctions/{auction_id}", timeout=30)
            assert updated.status_code == 200, updated.text
            updated_data = updated.json()
            assert updated_data["current_bid"] == valid_amount
            assert updated_data["bid_count"] >= 1

            history = customer.get(f"{base_url}/api/auctions/{auction_id}/bids", timeout=30)
            assert history.status_code == 200, history.text
            history_rows = history.json()
            assert len(history_rows) >= 1
            assert history_rows[0]["amount"] == valid_amount
        finally:
            _cleanup(admin_session, base_url, auction_id, product_id)
