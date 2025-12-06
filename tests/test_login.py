# tests/test_login.py
import pytest
from jose import jwt
from fastapi.testclient import TestClient
from src.server import app
from src.database import Base, get_db
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta

# ============ TEST DATABASE SETUP ============
# Use an in-memory database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# CRITICAL FIX: Create tables here before test execution
# This ensures all SQLAlchemy models (User, etc.) are available and initialized
Base.metadata.create_all(bind=engine) 

# Override dependency to use the test session
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply the override
app.dependency_overrides[get_db] = override_get_db

# Initialize the TestClient AFTER all database setup
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
        {"email": TEST_EMAIL, "exp": expire, "type": "verification"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# ============ TESTS ============
def test_login_success():
    # Register
    # The first time the endpoint is called, it should pass now that tables are created.
    resp = client.post("/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    # Accept 200 (created) or 201 (created), 400 (if user already exists from cleanup error)
    # The 500 error due to missing tables is now fixed.
    assert resp.status_code in (200, 201, 400), f"Register failed: {resp.json()}"

    # Verify
    token = generate_verification_token()
    resp = client.post("/auth/verify-email", json={"token": token})
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
    # This should now return 401 Unauthorized, as the database is working
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.json()}"