# tests/test_chat_api.py
"""
Simple API tests for the chat endpoint.
These tests verify basic functionality without complex authentication or database setup.
"""
import pytest
import os

# Set test environment
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from fastapi.testclient import TestClient
from src.server import app

client = TestClient(app)


def test_health_endpoint():
    """Test health check endpoint - most basic test"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "message" in data


def test_chat_empty_message():
    """UT-03: Test that empty messages are rejected"""
    payload = {
        "message": "",
        "user_id": 1,
        "chat_history": []
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 400, f"Expected 400 for empty message, got {response.status_code}"
    data = response.json()
    assert "empty" in data["detail"].lower()


def test_chat_missing_fields():
    """Test that missing required fields are rejected (validation)"""
    payload = {
        "message": "Hello"
        # Missing user_id
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 422, f"Expected 422 (validation error), got {response.status_code}"


def test_chat_invalid_user_id():
    """Test that invalid user_id types are rejected"""
    payload = {
        "message": "Hello",
        "user_id": "invalid",  # Should be int
        "chat_history": []
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 422, f"Expected 422 (validation error), got {response.status_code}"


def test_auth_endpoints_exist():
    """Test that authentication endpoints exist"""
    # Test register endpoint exists
    response = client.post("/auth/register", json={
        "username": "test",
        "email": "test@example.com",
        "password": "test123"
    })
    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "Register endpoint should exist"
    
    # Test login endpoint exists
    response = client.post("/auth/login", json={
        "username": "test",
        "password": "test123"
    })
    # Should not return 404 (endpoint exists)
    assert response.status_code != 404, "Login endpoint should exist"
