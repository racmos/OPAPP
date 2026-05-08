"""
Tests for security headers added to all HTTP responses.
"""

import pytest


class TestSecurityHeaders:
    """Verify security headers are present on responses."""

    @pytest.fixture
    def anon_client(self):
        """Anonymous client (no login required)."""
        from app import create_app

        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        return app.test_client()

    def test_x_frame_options_denies_embedding(self, anon_client):
        """X-Frame-Options: DENY prevents clickjacking."""
        resp = anon_client.get('/onepiecetcg/login')
        assert resp.headers.get('X-Frame-Options') == 'DENY'

    def test_x_content_type_options_nosniff(self, anon_client):
        """X-Content-Type-Options: nosniff prevents MIME sniffing."""
        resp = anon_client.get('/onepiecetcg/login')
        assert resp.headers.get('X-Content-Type-Options') == 'nosniff'

    def test_referrer_policy_set(self, anon_client):
        """Referrer-Policy controls referrer leakage."""
        resp = anon_client.get('/onepiecetcg/login')
        assert resp.headers.get('Referrer-Policy') == 'strict-origin-when-cross-origin'

    def test_permissions_policy_restricts_apis(self, anon_client):
        """Permissions-Policy disables unnecessary browser APIs."""
        resp = anon_client.get('/onepiecetcg/login')
        pp = resp.headers.get('Permissions-Policy')
        assert 'camera=()' in pp
        assert 'microphone=()' in pp
        assert 'geolocation=()' in pp

    def test_content_security_policy_present(self, anon_client):
        """CSP header is present with sane defaults."""
        resp = anon_client.get('/onepiecetcg/login')
        csp = resp.headers.get('Content-Security-Policy')
        assert "default-src 'self'" in csp
        assert "script-src 'self' 'unsafe-inline'" in csp
        assert "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com" in csp
        assert "font-src 'self' https://fonts.gstatic.com" in csp
        assert "img-src 'self' data: https:" in csp
        assert "connect-src 'self'" in csp

    def test_hsts_absent_in_testing(self, anon_client):
        """HSTS header is NOT sent during tests (TESTING=True)."""
        resp = anon_client.get('/onepiecetcg/login')
        assert 'Strict-Transport-Security' not in resp.headers

    def test_hsts_present_in_production(self):
        """HSTS header IS sent when TESTING=False."""
        from app import create_app

        app = create_app(
            TESTING=False,
            SECRET_KEY='prod-test-key',
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        )
        client = app.test_client()
        resp = client.get('/onepiecetcg/login')
        hsts = resp.headers.get('Strict-Transport-Security')
        assert hsts is not None
        assert 'max-age=31536000' in hsts
        assert 'includeSubDomains' in hsts
