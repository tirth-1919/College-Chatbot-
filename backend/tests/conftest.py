"""
Shared pytest configuration.

Historical note: the build machine exports a global DEBUG=release environment
variable. The application Settings now normalize unrecognized DEBUG values
safely (backend/app/core/config.py), so no environment mangling is required
here any more. This file is kept for future shared test fixtures.
"""
import pytest
from sqlalchemy.orm import Session
from backend.app.core.database import SessionLocal


@pytest.fixture(scope="function")
def db():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    yield session
    session.close()
