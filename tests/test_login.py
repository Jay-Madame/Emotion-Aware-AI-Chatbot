import requests
import pytest
import os
from dotenv import load_dotenv # New Import

# Load environment variables from .env file
# This must match the behavior of your server.py
load_dotenv()

# --- Configuration ---
API_URL = "http://localhost:8000/chat"

# --- Credentials loaded from the environment ---
# These MUST be set in your .env file
VALID_USERNAME = os.getenv("AUTH_USERNAME")
VALID_PASSWORD = os.getenv("AUTH_PASSWORD")

# We still hardcode bad credentials for the failure test
INVALID_USERNAME = "baduser"
INVALID_PASSWORD = "wrongpassword"

# Check if required environment variables are loaded
if not VALID_USERNAME or not VALID_PASSWORD:
    pytest.exit("❌ ERROR: AUTH_USERNAME or AUTH_PASSWORD not set in your environment or .env file.")


# Define the JSON body required by the FastAPI endpoint
CHAT_PAYLOAD = {"message": "Test auth"}

# Helper tuple for requests Basic Auth
VALID_AUTH = (VALID_USERNAME, VALID_PASSWORD)
INVALID_AUTH = (INVALID_USERNAME, INVALID_PASSWORD)

def test_successful_login():
    """
    Test Case 1: Attempts to access the chat endpoint with valid credentials 
    (loaded from AUTH_USERNAME/AUTH_PASSWORD).
    Expected outcome: HTTP 200 OK and a successful response message.
    """
    print("\n--- Running Test 1: Successful Login ---")
    try:
        response = requests.post(
            API_URL, 
            json=CHAT_PAYLOAD, 
            auth=VALID_AUTH,
            timeout=5  # Set a timeout for the request
        )
        
        # 1. Check HTTP Status Code
        assert response.status_code == 200, \
            f"Expected Status 200, but got {response.status_code}. Response: {response.text}"

        # 2. Check response body content
        data = response.json()
        assert "reply" in data, "Response body missing 'reply' field."
        print(f"✅ SUCCESS: Valid credentials accepted (Status: 200). API Reply: {data.get('reply')}")

    except requests.exceptions.ConnectionError:
        pytest.fail(f"Connection Error: Could not connect to the API at {API_URL}. Is the FastAPI server running?")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during Test 1: {e}")


def test_failed_login():
    """
    Test Case 2: Attempts to access the chat endpoint with invalid credentials.
    Expected outcome: HTTP 401 Unauthorized.
    """
    print("\n--- Running Test 2: Failed Login ---")
    try:
        response = requests.post(
            API_URL, 
            json=CHAT_PAYLOAD, 
            auth=INVALID_AUTH,
            timeout=5
        )

        # 1. Check HTTP Status Code
        assert response.status_code == 401, \
            f"Expected Status 401 Unauthorized, but got {response.status_code}. Invalid credentials were accepted!"

        print("✅ SUCCESS: Invalid credentials correctly rejected (Status: 401 Unauthorized).")

    except requests.exceptions.ConnectionError:
        pytest.fail(f"Connection Error: Could not connect to the API at {API_URL}. Is the FastAPI server running?")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during Test 2: {e}")


def test_missing_header():
    """
    Test Case 3: Attempts to access the chat endpoint with no Authorization header (missing 'auth' parameter).
    Expected outcome: HTTP 401 Unauthorized.
    """
    print("\n--- Running Test 3: Missing Header Test ---")
    try:
        response = requests.post(
            API_URL, 
            json=CHAT_PAYLOAD,
            # auth is intentionally omitted here
            timeout=5
        )

        # 1. Check HTTP Status Code
        assert response.status_code == 401, \
            f"Expected Status 401 Unauthorized, but got {response.status_code}. Missing header was accepted!"

        print("✅ SUCCESS: Missing Authorization header correctly rejected (Status: 401 Unauthorized).")

    except requests.exceptions.ConnectionError:
        pytest.fail(f"Connection Error: Could not connect to the API at {API_URL}. Is the FastAPI server running?")
    except Exception as e:
        pytest.fail(f"An unexpected error occurred during Test 3: {e}")