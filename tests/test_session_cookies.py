"""
Tests for session cookie security flags.
"""

from app import create_app


class TestSessionCookieFlags:
    """Session cookies should have secure flags set."""

    def test_session_cookie_secure_flags(self):
        """Default config should have Secure, HttpOnly, and SameSite=Lax."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        assert app.config['SESSION_COOKIE_SECURE'] is True
        assert app.config['SESSION_COOKIE_HTTPONLY'] is True
        assert app.config['SESSION_COOKIE_SAMESITE'] == 'Lax'

    def test_session_cookie_secure_overridable(self):
        """SESSION_COOKIE_SECURE should be overridable for local HTTP dev."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
            SESSION_COOKIE_SECURE=False,
        )
        assert app.config['SESSION_COOKIE_SECURE'] is False
