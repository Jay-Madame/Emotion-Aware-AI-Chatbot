# tests/test_login.py
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from src.server import app
from src.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta # <--- NEW IMPORT

# ============ TEST DATABASE SETUP ============
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Override dependency
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

# ============ TEST CONFIG ============
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

TEST_USERNAME = "ci_test_user"
TEST_PASSWORD = "ci_test_password123"[:72]
TEST_EMAIL = "ci_test_user@example.com"

# ============ HELPERS ============
def generate_verification_token():
    # ADDED: Include the 'exp' claim to match the token generated in src/auth.py
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(
        {"email": TEST_EMAIL, "exp": expire, "type": "verification"}, # <--- 'exp' ADDED HERE
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# ============ TESTS ============
def test_login_success():
    # Register
    resp = client.post("/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    # Accept 200 (created) or 400 (if user already exists from a previous failed run)
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.json()}"

    # Verify
    token = generate_verification_token()
    resp = client.post("/auth/verify-email", json={"token": token})
    # Accept 200 (verified) or 400 (if already verified or token expired, but should pass with fix)
    assert resp.status_code == 200, f"Verify failed: {resp.json()}"

    # Login
    resp = client.post("/auth/login", json={
        "username": TEST_USERNAME,
        "password": TEST_PASSWORD
    })
    
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_failure():
    resp = client.post("/auth/login", json={
        "username": "non_existent_user",
        "password": "wrong_password"
    })
    assert resp.status_code == 401
    assert resp.json() == {"detail": "Incorrect username or password"}