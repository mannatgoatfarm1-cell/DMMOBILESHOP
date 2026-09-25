import uuid

import requests


# Auth + support chat polling regression checks for repeated 401 behavior and session flows


ADMIN_IDENTIFIER = "deepak143"
ADMIN_PASSWORD = "deepak143"
CUSTOMER_IDENTIFIER = "p0check_1790113956@example.com"
CUSTOMER_PASSWORD = "TestPass123!"


def _login(session: requests.Session, base_url: str, identifier: str, password: str):
    return session.post(
        f"{base_url}/api/auth/login",
        json={"identifier": identifier, "password": password},
        timeout=30,
    )


class TestIteration20AuthPollingRegression:
    def test_public_health_loads(self, anon_session, base_url: str):
        response = anon_session.get(f"{base_url}/api/health", timeout=30)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["status"] == "ok"

    def test_unauthenticated_admin_chat_polling_endpoints_return_401_without_html_errors(self, base_url: str):
        session = requests.Session()

        list_response = session.get(f"{base_url}/api/admin/chats", timeout=30)
        assert list_response.status_code == 401, list_response.text
        list_data = list_response.json()
        assert isinstance(list_data.get("detail"), str)

        thread_response = session.get(f"{base_url}/api/admin/chats/non-existent-thread", timeout=30)
        assert thread_response.status_code == 401, thread_response.text
        thread_data = thread_response.json()
        assert isinstance(thread_data.get("detail"), str)

    def test_customer_login_me_and_live_chat_flow(self, base_url: str):
        session = requests.Session()

        login = _login(session, base_url, CUSTOMER_IDENTIFIER, CUSTOMER_PASSWORD)
        assert login.status_code == 200, login.text
        login_data = login.json()
        assert login_data["role"] == "customer"
        assert "password_hash" not in login_data

        me = session.get(f"{base_url}/api/auth/me", timeout=30)
        assert me.status_code == 200, me.text
        me_data = me.json()
        assert me_data["email"].lower() == CUSTOMER_IDENTIFIER.lower()
        assert me_data["role"] == "customer"

        thread = session.get(f"{base_url}/api/chat/thread", timeout=30)
        assert thread.status_code == 200, thread.text
        thread_data = thread.json()
        assert "thread" in thread_data and "messages" in thread_data
        assert isinstance(thread_data["messages"], list)

        text = f"TEST_i20_customer_ping_{uuid.uuid4().hex[:8]}"
        sent = session.post(f"{base_url}/api/chat/messages", json={"message": text}, timeout=30)
        assert sent.status_code == 200, sent.text
        sent_data = sent.json()
        assert sent_data["message"] == text
        assert sent_data["sender_role"] == "customer"

    def test_admin_login_me_and_admin_routes_and_chat_reply(self, base_url: str):
        admin_session = requests.Session()

        login = _login(admin_session, base_url, ADMIN_IDENTIFIER, ADMIN_PASSWORD)
        assert login.status_code == 200, login.text
        login_data = login.json()
        assert login_data["role"] == "admin"
        assert "password_hash" not in login_data

        me = admin_session.get(f"{base_url}/api/auth/me", timeout=30)
        assert me.status_code == 200, me.text
        me_data = me.json()
        assert me_data["role"] == "admin"

        dashboard = admin_session.get(f"{base_url}/api/admin/dashboard", timeout=30)
        assert dashboard.status_code == 200, dashboard.text
        dashboard_data = dashboard.json()
        assert "metrics" in dashboard_data

        chats = admin_session.get(f"{base_url}/api/admin/chats", timeout=30)
        assert chats.status_code == 200, chats.text
        chats_data = chats.json()
        assert isinstance(chats_data, list)

        if chats_data:
            thread_id = chats_data[0]["id"]
            one_thread = admin_session.get(f"{base_url}/api/admin/chats/{thread_id}", timeout=30)
            assert one_thread.status_code == 200, one_thread.text
            one_thread_data = one_thread.json()
            assert "messages" in one_thread_data

            text = f"TEST_i20_admin_reply_{uuid.uuid4().hex[:8]}"
            reply = admin_session.post(
                f"{base_url}/api/admin/chats/{thread_id}/messages",
                json={"message": text},
                timeout=30,
            )
            assert reply.status_code == 200, reply.text
            reply_data = reply.json()
            assert reply_data["message"] == text
            assert reply_data["sender_role"] == "admin"

    def test_login_sets_secure_httponly_session_cookies(self, base_url: str):
        session = requests.Session()
        response = _login(session, base_url, ADMIN_IDENTIFIER, ADMIN_PASSWORD)
        assert response.status_code == 200, response.text
        raw_cookie_header = response.headers.get("set-cookie", "")
        assert "HttpOnly" in raw_cookie_header
        assert "Secure" in raw_cookie_header
        assert "samesite=none" in raw_cookie_header.lower()

    def test_cors_preflight_allows_credentials_with_explicit_origin(self, base_url: str):
        session = requests.Session()
        response = session.options(
            f"{base_url}/api/auth/login",
            headers={
                "Origin": base_url,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
            timeout=30,
        )
        assert response.status_code in [200, 204], response.text
        assert response.headers.get("access-control-allow-credentials") == "true"
        assert response.headers.get("access-control-allow-origin") in [base_url, f"{base_url}/"]

    def test_logout_then_auth_me_and_admin_chats_are_unauthorized_without_spam_loop_signal(self, base_url: str):
        session = requests.Session()
        login = _login(session, base_url, ADMIN_IDENTIFIER, ADMIN_PASSWORD)
        assert login.status_code == 200, login.text

        logout = session.post(f"{base_url}/api/auth/logout", timeout=30)
        assert logout.status_code == 204, logout.text

        me = session.get(f"{base_url}/api/auth/me", timeout=30)
        assert me.status_code == 401, me.text

        # Simulate 1-second polling behavior: endpoint should consistently 401, not 500.
        statuses = []
        for _ in range(5):
            response = session.get(f"{base_url}/api/admin/chats", timeout=30)
            statuses.append(response.status_code)
            assert isinstance(response.json().get("detail"), str)
        assert statuses == [401, 401, 401, 401, 401]

    def test_lockout_after_five_failed_attempts_unchanged(self, base_url: str):
        session = requests.Session()
        identifier = f"test-lockout-i20-{uuid.uuid4().hex[:8]}"

        for _ in range(5):
            failed = _login(session, base_url, identifier, "wrong-pass")
            assert failed.status_code == 401, failed.text

        locked = _login(session, base_url, identifier, "wrong-pass")
        assert locked.status_code == 429, locked.text
