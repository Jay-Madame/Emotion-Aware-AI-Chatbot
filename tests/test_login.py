# tests/test_login.py
import pytest
import os
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# ============ CRITICAL: SET ENV VARS BEFORE ANY IMPORTS ============
# These MUST be set before loading .env or importing any modules
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Prevent dotenv from overriding our test DATABASE_URL
os.environ["DOTENV_OVERRIDE"] = "0"

# ============ TEST DATABASE SETUP ============
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Import database module and replace engine BEFORE importing app
import src.database as db_module

# Replace the production engine and session with test versions
db_module.engine = test_engine
db_module.SessionLocal = TestingSessionLocal

# Now import the app (it will use the test engine)
from src.server import app
from src.database import Base, get_db

# ============ TEST CONFIG ============
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

TEST_USERNAME = "ci_test_user"
TEST_PASSWORD = "ci_test_password123"
TEST_EMAIL = "ci_test_user@example.com"

# ============ HELPERS ============
def generate_verification_token():
    expire = datetime.utcnow() + timedelta(hours=24) 
    return jwt.encode(
        {"email": TEST_EMAIL, "exp": expire, "type": "verification"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# ============ FIXTURES ============
@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Setup test database before each test"""
    # Create all tables in test database
    Base.metadata.create_all(bind=test_engine)
    
    # Override the get_db dependency to use test database
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # Cleanup after test
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client():
    """Create a test client"""
    with TestClient(app) as test_client:
        yield test_client

# ============ TESTS ============
def test_login_success(client):
    """Test successful registration, verification, and login flow"""
    # Register
    resp = client.post("/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert resp.status_code in (200, 201), f"Register failed: {resp.json()}"

    # Verify email
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
    assert data["username"] == TEST_USERNAME
    assert data["email"] == TEST_EMAIL


def test_login_failure(client):
    """Test login with non-existent user returns 401"""
    resp = client.post("/auth/login", json={
        "username": "non_existent_user",
        "password": "wrong_password"
    })
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.json()}"
    assert "Incorrect username or password" in resp.json()["detail"]


def test_login_unverified_user(client):
    """Test login with unverified email returns 403"""
    # Register user but don't verify
    resp = client.post("/auth/register", json={
        "username": "unverified_user",
        "email": "unverified@example.com",
        "password": TEST_PASSWORD
    })
    assert resp.status_code in (200, 201)

    # Try to login without verification
    resp = client.post("/auth/login", json={
        "username": "unverified_user",
        "password": TEST_PASSWORD
    })
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.json()}"
    assert "not verified" in resp.json()["detail"].lower()# tests/test_login.py
import pytest
from jose import jwt
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# conftest.py has already set environment variables
from src.server import app
from src.database import Base, get_db

# ============ TEST DATABASE SETUP ============
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# ============ TEST CONFIG ============
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"

TEST_USERNAME = "ci_test_user"
TEST_PASSWORD = "ci_test_password123"
TEST_EMAIL = "ci_test_user@example.com"

# ============ HELPERS ============
def generate_verification_token():
    expire = datetime.utcnow() + timedelta(hours=24) 
    return jwt.encode(
        {"email": TEST_EMAIL, "exp": expire, "type": "verification"},
        SECRET_KEY,
        algorithm=ALGORITHM
    )

# ============ FIXTURES ============
@pytest.fixture(scope="function", autouse=True)
def setup_test_database():
    """Setup test database before each test"""
    # Create all tables in test database
    Base.metadata.create_all(bind=test_engine)
    
    # Override the get_db dependency to use test database
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    
    yield
    
    # Cleanup after test
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def client():
    """Create a test client"""
    with TestClient(app) as test_client:
        yield test_client

# ============ TESTS ============
def test_login_success(client):
    """Test successful registration, verification, and login flow"""
    # Register
    resp = client.post("/auth/register", json={
        "username": TEST_USERNAME,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    })
    assert resp.status_code in (200, 201), f"Register failed: {resp.json()}"

    # Verify email
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
    assert data["username"] == TEST_USERNAME
    assert data["email"] == TEST_EMAIL


def test_login_failure(client):
    """Test login with non-existent user returns 401"""
    resp = client.post("/auth/login", json={
        "username": "non_existent_user",
        "password": "wrong_password"
    })
    assert resp.status_code == 401, f"Expected 401, got {resp.status_code}: {resp.json()}"
    assert "Incorrect username or password" in resp.json()["detail"]


def test_login_unverified_user(client):
    """Test login with unverified email returns 403"""
    # Register user but don't verify
    resp = client.post("/auth/register", json={
        "username": "unverified_user",
        "email": "unverified@example.com",
        "password": TEST_PASSWORD
    })
    assert resp.status_code in (200, 201)

    # Try to login without verification
    resp = client.post("/auth/login", json={
        "username": "unverified_user",
        "password": TEST_PASSWORD
    })
    assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.json()}"
    assert "not verified" in resp.json()["detail"].lower()
    