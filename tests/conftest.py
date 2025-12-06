# tests/conftest.py
"""
Pytest configuration file that runs before all tests.
This ensures the test database is set up correctly.
"""
import os
import sys

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables BEFORE any imports
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
