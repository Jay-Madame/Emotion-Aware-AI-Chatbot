# tests/test_gemini_api.py
"""
Test Gemini API connection.
CT-04: Component test for Gemini API.
"""
import os
import pytest
from dotenv import load_dotenv

load_dotenv()

def test_gemini_api_connection():
    """CT-04: Test Gemini API connection and response"""
    from langchain_google_genai import ChatGoogleGenerativeAI
    
    # Check if API key is available
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        pytest.skip("GOOGLE_API_KEY not set")
    
    try:
        # Initialize Gemini model
        model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3)
        
        # Test with a simple prompt
        response = model.invoke("Say 'Hello' in one word")
        
        # Verify response
        assert response is not None, "Response should not be None"
        assert hasattr(response, 'content'), "Response should have content attribute"
        assert len(response.content) > 0, "Response content should not be empty"
        
        print(f"✓ Gemini API test passed. Response: {response.content[:50]}...")
        
    except Exception as e:
        pytest.fail(f"Gemini API connection failed: {str(e)}")