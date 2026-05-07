"""
Tests for rate limiting on auth endpoints.
"""

import pytest

from app import create_app, db


@pytest.fixture
def app_with_ratelimit():
    """Create application with rate limiting enabled for testing."""
    app = create_app(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        SECRET_KEY='test-secret-key',
        RATELIMIT_ENABLED=True,
        RATELIMIT_STORAGE_URI='memory://',
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client_with_ratelimit(app_with_ratelimit):
    """Create test client with rate limiting enabled."""
    return app_with_ratelimit.test_client()


class TestRateLimitingDisabledInTests:
    """Rate limiting should be disabled by default in tests."""

    def test_rate_limiting_disabled_in_tests(self, client):
        """Default test fixture should not rate-limit auth endpoints."""
        for _ in range(15):
            response = client.post(
                '/onepiecetcg/login',
                json={'email': 'test@example.com', 'password': 'wrong'},
            )
        assert response.status_code in (200, 401)
        assert response.status_code != 429


class TestLoginRateLimit:
    """Login endpoint should be rate-limited to 10 POSTs per minute."""

    def test_login_rate_limit_under_threshold(self, client_with_ratelimit):
        """10 login POSTs within a minute should not trigger 429."""
        for _ in range(10):
            response = client_with_ratelimit.post(
                '/onepiecetcg/login',
                json={'email': 'test@example.com', 'password': 'wrong'},
            )
            assert response.status_code in (200, 401)
            assert response.status_code != 429

    def test_login_rate_limit_exceeded_429(self, client_with_ratelimit):
        """11th login POST within a minute should return 429."""
        for _ in range(10):
            client_with_ratelimit.post(
                '/onepiecetcg/login',
                json={'email': 'test@example.com', 'password': 'wrong'},
            )
        response = client_with_ratelimit.post(
            '/onepiecetcg/login',
            json={'email': 'test@example.com', 'password': 'wrong'},
        )
        assert response.status_code == 429


class TestRegisterRateLimit:
    """Register endpoint should be rate-limited to 10 POSTs per minute."""

    def test_register_rate_limit_exceeded_429(self, client_with_ratelimit):
        """11th register POST within a minute should return 429."""
        for i in range(10):
            client_with_ratelimit.post(
                '/onepiecetcg/register',
                json={
                    'username': f'user{i}',
                    'email': f'user{i}@example.com',
                    'password': 'password123',
                },
            )
        response = client_with_ratelimit.post(
            '/onepiecetcg/register',
            json={
                'username': 'user10',
                'email': 'user10@example.com',
                'password': 'password123',
            },
        )
        assert response.status_code == 429
