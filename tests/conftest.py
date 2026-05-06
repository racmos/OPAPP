"""
Pytest configuration and fixtures for OPAPP tests.
"""

import pytest

from app import create_app, db


@pytest.fixture
def app():
    """Create application for testing with SQLite in-memory."""
    app = create_app(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        SECRET_KEY='test-secret-key',
    )

    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()
