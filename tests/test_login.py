# tests/test_login.py
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)

SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

TEST_USERNAME = "ci_test_user"
TEST_PASSWORD = "ci_test_password123"[:72]
TEST_EMAIL = "ci_test_user@example.com"


def generate_verification_token():
    return jwt.encode(
        {"email": TEST_EMAIL, "type": "verification"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )


def test_login_success():
    # Register
    resp = client.post("/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert resp.status_code in (200, 201, 400)  # already exists is fine

    # Verify
    token = generate_verification_token()
    resp = client.post("/auth/verify-email", json={"token": token})
    assert resp.status_code in (200, 400)

    # Login
    resp = client.post("/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data


def test_login_failure():
    resp = client.post("/auth/login", json={
        "username": "baduser",
        "password": "wrongpass"
    })
    assert resp.status_code == 401
