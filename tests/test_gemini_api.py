from dotenv import load_dotenv
from google import genai
from google.genai import errors as genai_errors  # <-- [NEW] import error types
import os
import pytest

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# test API Keys
@pytest.fixture(scope="module")
def gemini_client():
    # Check for API Key
    if not api_key:
        raise ValueError("GOOGLE_API_KEY env variable is missing. Check secrets")
    
    # Check for valid API Key
    try:
        return genai.Client(api_key=api_key)
    except Exception as e:
        raise RuntimeError("Failed to initialize Gemini Client. Check if the provided key is valid.")
    

# Test Connection
def test_gemini_api_connection(gemini_client):
    model_name = "gemini-2.5-flash"
    prompt = "Give me a simple response to confirm connection"

    try:
        response = gemini_client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

    # --- [NEW] handle server-side errors (like 503) separately ---
    except genai_errors.ServerError as e:
        msg = str(e)
        # If the model is overloaded / unavailable (503), don't fail CI – skip this test
        if "503" in msg or "UNAVAILABLE" in msg or "overloaded" in msg:
            pytest.skip("Gemini API overloaded (503 UNAVAILABLE). Skipping connectivity test.")
        else:
            pytest.fail(f"Gemini server error during content generation: {e}")

    # --- [UNCHANGED in spirit] any other client-side issue still fails the test ---
    except Exception as e:
        # connection fails on our side (bad key, wrong model, etc.)
        pytest.fail(f"API call failed during content generation: {e}")

    # --- [SAME ASSERTIONS, just a tiny safety tweak] ---
    # Use a local variable so we can inspect if needed
    text = getattr(response, "text", None)
    assert text is not None, "Response text was empty."
    assert len(text.strip()) > 0, "Response was only whitespace"

