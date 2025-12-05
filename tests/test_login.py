import requests
import pytest
from jose import jwt

API_BASE = "http://localhost:8000"

REGISTER_URL = f"{API_BASE}/auth/register"
VERIFY_URL = f"{API_BASE}/auth/verify-email"
LOGIN_URL = f"{API_BASE}/auth/login"
CHAT_URL = f"{API_BASE}/chat"

SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

# Fixed credentials for CI tests
TEST_USERNAME = "ci_test_user"
TEST_PASSWORD = "ci_test_password123"
TEST_EMAIL = "ci_test_user@example.com"

CHAT_PAYLOAD = {"message": "Hello test!"}


def register_test_user():
    """Register the CI test user. If it already exists, ignore the error."""
    response = requests.post(
        REGISTER_URL,
        json={
            "username": TEST_USERNAME,
            "email": TEST_EMAIL,
            "password": TEST_PASSWORD
        },
        timeout=5
    )
    
    # If already registered, we can ignore error 400
    if response.status_code not in (200, 400):
        pytest.fail(f"Unexpected error during user registration: {response.text}")
    
    return response


def extract_verification_token(registration_response):
    """
    Since email sending is disabled in CI, we rely on your backend printing:
        ⚠️ Email not configured. Would send to test@example.com:
        Subject: Verify Your Email - ...
        <token is in the generated verification link>
    
    BUT since the API does not return the token,
    we decode it from the URL your backend constructs.

    This assumes your FAST API handler for registration returns the user object
    and the backend prints the verification link containing the token.
    """
    # The backend does not directly return a token.
    # So we generate our own — identical to backend logic.
    token = jwt.encode(
        {"email": TEST_EMAIL, "type": "verification"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )
    return token


def verify_test_user():
    """Call the verify-email endpoint using the generated token."""
    token = extract_verification_token(None)

    resp = requests.post(
        VERIFY_URL,
        json={"token": token},
        timeout=5
    )

    if resp.status_code not in (200, 400):
        pytest.fail(f"Unexpected error during email verification: {resp.text}")


def login(username, password):
    return requests.post(
        LOGIN_URL,
        json={"username": username, "password": password},
        timeout=5
    )


# ------------------ TESTS ------------------ #

def test_login_success():
    """User should be able to login successfully after verification."""
    
    register_test_user()
    verify_test_user()

    resp = login(TEST_USERNAME, TEST_PASSWORD)

    assert resp.status_code == 200, \
        f"Expected 200 but got {resp.status_code}. Response: {resp.text}"

    data = resp.json()
    assert "access_token" in data, "Missing access_token in login response."


def test_login_failure():
    """Invalid credentials must return 401."""
    resp = login("not_a_real_user", "wrongpass")
    assert resp.status_code == 401, \
        f"Expected 401 but got {resp.status_code}."
