# tests/conftest.py
"""
Pytest configuration file that runs before all tests.
This ensures the test database is set up correctly.
"""
import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Set test environment variables BEFORE any imports
os.environ["TESTING"] = "1"
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

# Create test database engine
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# Now import database module and monkey-patch it
import src.database as db_module

# Replace the engine and SessionLocal
db_module.engine = test_engine
db_module.SessionLocal = TestingSessionLocal

# Store for cleanup
_original_engine = None
_original_sessionlocal = None