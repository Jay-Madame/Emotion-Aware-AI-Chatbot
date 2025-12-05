import os
import pytest
import requests
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Base URLs for the API
API_BASE = "http://localhost:8000"
LOGIN_URL = f"{API_BASE}/auth/login"
CHAT_URL = f"{API_BASE}/chat"

# These should be defined in your .env for testing purposes
TEST_USERNAME = os.getenv("TEST_USERNAME")
TEST_PASSWORD = os.getenv("TEST_PASSWORD")

if not TEST_USERNAME or not TEST_PASSWORD:
    pytest.exit(
        "ERROR: TEST_USERNAME or TEST_PASSWORD not set in the .env file. "
        "Add them so the login tests can run."
    )

# Basic payload used for accessing the chat route
CHAT_PAYLOAD = {"message": "test message"}


def login(username, password):
    """
    Helper function for sending login requests.
    Returns the full requests.Response object.
    """
    return requests.post(
        LOGIN_URL,
        json={"username": username, "password": password},
        timeout=5
    )


def test_login_success():
    """Test that valid credentials return a token."""
    resp = login(TEST_USERNAME, TEST_PASSWORD)

    assert resp.status_code == 200, \
        f"Expected 200 but got {resp.status_code}. Response: {resp.text}"

    data = resp.json()
    assert "access_token" in data, "Login did not return an access token."


def test_login_failure():
    """Test that invalid credentials are rejected."""
    resp = login("wronguser", "nottherightpassword")

    # Most APIs return 401 for invalid login, so we expect that here
    assert resp.status_code == 401, \
        f"Expected 401 for invalid login but got {resp.status_code}."


def test_chat_requires_auth():
    """
    Ensures the /chat endpoint blocks unauthenticated requests.
    The endpoint should return 401 without a token.
    """
    resp = requests.post(
        CHAT_URL,
        json=CHAT_PAYLOAD,
        timeout=5
    )

    assert resp.status_code == 401, \
        "Chat endpoint accepted an unauthenticated request (expected 401)."


def test_chat_with_token():
    """
    Login with valid credentials, then try using the token
    to make sure authenticated chat requests work.
    """
    # First login
    login_resp = login(TEST_USERNAME, TEST_PASSWORD)
    assert login_resp.status_code == 200, "Login failed unexpectedly."

    token = login_resp.json().get("access_token")
    assert token, "Login response missing access token."

    # Now hit the chat endpoint with the token
    resp = requests.post(
        CHAT_URL,
        json=CHAT_PAYLOAD,
        headers={"Authorization": f"Bearer {token}"},
        timeout=5
    )

    assert resp.status_code == 200, \
        f"Expected 200 but got {resp.status_code}. Response: {resp.text}"

    data = resp.json()
    assert "reply" in data, "Chat response missing 'reply' field."
