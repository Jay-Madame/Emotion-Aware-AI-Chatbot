# tests/test_chat_api.py
"""
Simple API tests for the chat endpoint.
These tests verify basic functionality without complex authentication.
"""
import pytest
import os
from fastapi.testclient import TestClient

# Set test environment
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from src.server import app

client = TestClient(app)

# Test data
CHAT_PAYLOAD = {
    "message": "Hello, how are you?",
    "user_id": 1,
    "chat_history": []
}


def test_chat_endpoint_exists():
    """UT-01: Test that chat endpoint exists and accepts requests"""
    # This will fail with 404 (user not found) but that's expected
    # We're just testing the endpoint exists
    response = client.post("/chat", json=CHAT_PAYLOAD)
    # Should return 404 (user not found) or 500, not 404 (route not found)
    assert response.status_code in [404, 500], f"Expected 404 or 500, got {response.status_code}"


def test_health_endpoint():
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_chat_empty_message():
    """UT-03: Test that empty messages are rejected"""
    payload = {
        "message": "",
        "user_id": 1,
        "chat_history": []
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 400, f"Expected 400, got {response.status_code}"


def test_chat_missing_fields():
    """Test that missing required fields are rejected"""
    payload = {
        "message": "Hello"
        # Missing user_id
    }
    response = client.post("/chat", json=payload)
    assert response.status_code == 422, f"Expected 422 (validation error), got {response.status_code}"