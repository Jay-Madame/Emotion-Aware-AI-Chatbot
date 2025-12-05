import requests
import pytest
from jose import jwt

API_BASE = "http://localhost:8000"

REGISTER_URL = f"{API_BASE}/auth/register"
VERIFY_URL = f"{API_BASE}/auth/verify-email"
LOGIN_URL = f"{API_BASE}/auth/login"
CHAT_URL = f"{API_BASE}/chat"

# Must match backend
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

# Fixed CI credentials
TEST_USERNAME = "ci_test_user"
TEST_PASSWORD = "ci_test_password123"[:72]
TEST_EMAIL = "ci_test_user@example.com"

CHAT_PAYLOAD = {"message": "Hello test!"}


def register_test_user():
    """
    Register the CI user.
    Acceptable outcomes:
      • 200 (successful registration)
      • 400 (username/email already exists)
    Anything else = unexpected.
    """
    response = requests.post(
        REGISTER_URL,
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        timeout=5
    )

    if response.status_code in (200, 201):
        # Expected behavior: success message
        return

    if response.status_code == 400:
        # Already exists: acceptable
        return

    pytest.fail(f"Unexpected error during user registration: {response.text}")


def generate_verification_token():
    """
    Your backend does NOT return the token in /register.
    The test must generate the *same* token your backend would create.
    """
    return jwt.encode(
        {"email": TEST_EMAIL, "type": "verification"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def verify_test_user():
    """
    Verify the user using the verification endpoint.
    Acceptable:
      • 200 verification worked
      • 400 email already verified
    """
    token = generate_verification_token()

    resp = requests.post(
        VERIFY_URL,
        json={"token": token},
        timeout=5
    )

    if resp.status_code in (200, 400):
        return  # All good

    pytest.fail(f"Unexpected error during email verification: {resp.text}")


def login(username, password):
    return requests.post(
        LOGIN_URL,
        json={"username": username, "password": password},
        timeout=5
    )


# ------------------ TESTS ------------------ #


def test_login_success():
    """User should be able to login if verified."""
    
    register_test_user()
    verify_test_user()

    resp = login(TEST_USERNAME, TEST_PASSWORD)

    assert resp.status_code == 200, \
        f"Expected 200 but got {resp.status_code}. Response: {resp.text}"

    data = resp.json()
    assert "access_token" in data, "Missing access_token in login response."


def test_login_failure():
    """Invalid credentials should return 401."""
    resp = login("baduser", "wrongpass")
    assert resp.status_code == 401
