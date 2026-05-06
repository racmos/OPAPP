"""
Integration tests for auth routes (login, register, logout).
"""

import json

import pytest

from app import db
from app.models import OpUser


class TestAuthLogin:
    """Tests for GET/POST /onepiecetcg/login."""

    def test_login_page_renders(self, client):
        """GET /onepiecetcg/login returns 200 and renders login form."""
        response = client.get('/onepiecetcg/login')
        assert response.status_code == 200

    def test_login_post_valid_credentials(self, app, client):
        """POST /onepiecetcg/login with valid creds returns JSON success."""
        with app.app_context():
            user = OpUser(username='testuser', email='test@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        response = client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'test@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        # JSON-based login returns 200 with success + redirect URL
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert 'redirect' in data

    def test_login_post_valid_sets_session(self, app, client):
        """After successful login, subsequent requests are authenticated."""
        with app.app_context():
            user = OpUser(username='testuser2', email='test2@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        # Login via JSON
        login_resp = client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'test2@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )
        assert login_resp.status_code == 200

        # Access dashboard (should now be authenticated)
        dashboard_resp = client.get('/onepiecetcg/dashboard')
        assert dashboard_resp.status_code == 200

    def test_login_post_invalid_credentials(self, app, client):
        """POST /onepiecetcg/login with wrong creds returns 401 JSON error."""
        with app.app_context():
            user = OpUser(username='testuser3', email='test3@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        response = client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'test3@test.com', 'password': 'wrongpassword'}),
            content_type='application/json',
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False

    def test_login_post_nonexistent_user(self, client):
        """POST /onepiecetcg/login with non-existent user returns 401."""
        response = client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'nobody@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data['success'] is False

    def test_login_already_authenticated_redirects(self, app, client):
        """GET /onepiecetcg/login redirects if already logged in."""
        with app.app_context():
            user = OpUser(username='loggeduser', email='logged@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        # Login via JSON
        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'logged@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        # Now try to access login page
        response = client.get('/onepiecetcg/login', follow_redirects=False)
        # Should redirect away from login to dashboard
        assert response.status_code == 302
        assert '/onepiecetcg/' in response.headers.get('Location', '')


class TestAuthRegister:
    """Tests for GET/POST /onepiecetcg/register."""

    def test_register_page_renders(self, client):
        """GET /onepiecetcg/register returns 200 and renders register form."""
        response = client.get('/onepiecetcg/register')
        assert response.status_code == 200

    def test_register_post_creates_user(self, app, client):
        """POST /onepiecetcg/register creates a new user."""
        response = client.post(
            '/onepiecetcg/register',
            data=json.dumps({'username': 'newuser', 'email': 'new@test.com', 'password': 'secret123'}),
            content_type='application/json',
        )

        # JSON-based register returns 200 with success
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True

        # Verify user was created
        with app.app_context():
            user = OpUser.query.filter_by(username='newuser').first()
            assert user is not None
            assert user.email == 'new@test.com'
            assert user.check_password('secret123')

    def test_register_duplicate_username(self, app, client):
        """POST /onepiecetcg/register with duplicate username returns 400 JSON error."""
        with app.app_context():
            user = OpUser(username='dupeuser', email='dupe1@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        response = client.post(
            '/onepiecetcg/register',
            data=json.dumps({'username': 'dupeuser', 'email': 'dupe2@test.com', 'password': 'secret123'}),
            content_type='application/json',
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_register_duplicate_email(self, app, client):
        """POST /onepiecetcg/register with duplicate email returns 400 JSON error."""
        with app.app_context():
            user = OpUser(username='user1', email='dupe@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        response = client.post(
            '/onepiecetcg/register',
            data=json.dumps({'username': 'user2', 'email': 'dupe@test.com', 'password': 'secret123'}),
            content_type='application/json',
        )

        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False

    def test_register_already_authenticated_redirects(self, app, client):
        """GET /onepiecetcg/register redirects if already logged in."""
        with app.app_context():
            user = OpUser(username='loggedreg', email='loggedreg@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        # Login via JSON
        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'loggedreg@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        # Now try to access register page
        response = client.get('/onepiecetcg/register', follow_redirects=False)
        assert response.status_code == 302
        assert '/onepiecetcg/' in response.headers.get('Location', '')


class TestAuthLogout:
    """Tests for GET /onepiecetcg/logout."""

    def test_logout_authenticated(self, app, client):
        """GET /onepiecetcg/logout logs out and redirects to login."""
        with app.app_context():
            user = OpUser(username='logoutuser', email='logout@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        # Login via JSON
        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'logout@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        # Logout
        response = client.get('/onepiecetcg/logout', follow_redirects=False)
        assert response.status_code == 302
        assert '/onepiecetcg/login' in response.headers.get('Location', '')

    def test_logout_unauthenticated(self, client):
        """GET /onepiecetcg/logout when not logged in returns 401/302."""
        response = client.get('/onepiecetcg/logout')
        # Without login, login_manager may redirect to login
        assert response.status_code in (302, 401)
