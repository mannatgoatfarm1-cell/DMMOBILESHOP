import os
from pathlib import Path

import pytest
import requests


def _base_url() -> str:
    env_url = os.environ.get("REACT_APP_BACKEND_URL")
    if env_url:
        return env_url.rstrip("/")

    frontend_env = Path("/app/frontend/.env")
    if frontend_env.exists():
        for line in frontend_env.read_text().splitlines():
            if line.startswith("REACT_APP_BACKEND_URL="):
                value = line.split("=", 1)[1].strip()
                if value:
                    return value.rstrip("/")

    raise RuntimeError("REACT_APP_BACKEND_URL is required for backend tests")


@pytest.fixture(scope="session")
def base_url() -> str:
    return _base_url()


@pytest.fixture
def anon_session() -> requests.Session:
    session = requests.Session()
    return session


@pytest.fixture
def customer_credentials() -> dict:
    import uuid

    uniq = uuid.uuid4().hex[:8]
    return {
        "name": f"TEST_Customer_{uniq}",
        "email": f"test_customer_{uniq}@example.com",
        "password": "Passw0rd!234",
    }


@pytest.fixture
def customer_session(base_url: str, customer_credentials: dict) -> requests.Session:
    # Customer auth setup (register and receive secure cookies)
    session = requests.Session()
    register_payload = {
        **customer_credentials,
        "confirm_password": customer_credentials["password"],
    }
    register = session.post(f"{base_url}/api/auth/register", json=register_payload, timeout=30)
    assert register.status_code == 201, register.text
    return session


@pytest.fixture
def admin_session(base_url: str) -> requests.Session:
    # Seeded admin auth setup
    session = requests.Session()
    payload = {"identifier": "deepak143", "password": "deepak143"}
    response = session.post(f"{base_url}/api/auth/login", json=payload, timeout=30)
    assert response.status_code == 200, response.text
    return session
