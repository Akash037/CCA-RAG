"""Test configuration and fixtures."""

import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.core.database import get_db_session


# Test database setup
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Create test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=settings.debug
    )
    
    # Create tables
    SQLModel.metadata.create_all(engine)
    
    yield engine
    
    engine.dispose()


@pytest.fixture(scope="function")
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def sample_query_request():
    """Sample query request for testing."""
    return {
        "query": "What is the weather like today?",
        "session_id": "test_session_123",
        "user_id": "test_user_456",
        "max_results": 5,
        "include_sources": True
    }


@pytest.fixture
def sample_feedback_request():
    """Sample feedback request for testing."""
    return {
        "query_id": "query_123",
        "session_id": "test_session_123",
        "rating": 4,
        "feedback_text": "Good response",
        "improvement_suggestions": "Could be more detailed"
    }
