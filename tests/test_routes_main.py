"""
Integration tests for main routes (dashboard, root redirect) and profile route.
"""

import json

import pytest

from app import db
from app.models import OpUser


class TestMainDashboard:
    """Tests for dashboard and root redirect."""

    def test_root_redirects_to_dashboard(self, client):
        """GET /onepiecetcg/ redirects to /onepiecetcg/dashboard."""
        response = client.get('/onepiecetcg/', follow_redirects=False)
        assert response.status_code in (302, 301)
        # Should redirect to dashboard
        location = response.headers.get('Location', '')
        assert '/onepiecetcg/' in location or '/onepiecetcg/dashboard' in location

    def test_dashboard_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/dashboard redirects to login when not authenticated."""
        response = client.get('/onepiecetcg/dashboard', follow_redirects=False)
        # login_manager should redirect to login
        assert response.status_code in (302, 401)

    def test_dashboard_authenticated_renders(self, app, client):
        """GET /onepiecetcg/dashboard returns 200 when authenticated."""
        with app.app_context():
            user = OpUser(username='dashuser', email='dash@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        # Login via JSON
        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'dash@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        # Access dashboard
        response = client.get('/onepiecetcg/dashboard')
        assert response.status_code == 200

    def test_dashboard_contains_welcome(self, app, client):
        """Dashboard page contains welcome message."""
        with app.app_context():
            user = OpUser(username='dashuser2', email='dash2@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'dash2@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        response = client.get('/onepiecetcg/dashboard')
        assert response.status_code == 200
        # Check for One Piece TCG branding
        html = response.data.decode('utf-8')
        assert 'One Piece' in html or 'OP TCG' in html or 'Manager' in html


class TestProfileRoute:
    """Tests for /onepiecetcg/profile."""

    def test_profile_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/profile redirects to login when not authenticated."""
        response = client.get('/onepiecetcg/profile', follow_redirects=False)
        assert response.status_code in (302, 401)

    def test_profile_authenticated_renders(self, app, client):
        """GET /onepiecetcg/profile returns 200 when authenticated."""
        with app.app_context():
            user = OpUser(username='profuser', email='prof@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'prof@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        response = client.get('/onepiecetcg/profile')
        assert response.status_code == 200

    def test_profile_shows_username(self, app, client):
        """Profile page shows the username."""
        with app.app_context():
            user = OpUser(username='profuser2', email='prof2@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'prof2@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        response = client.get('/onepiecetcg/profile')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'profuser2' in html

    def test_profile_has_current_password_input(self, app, client):
        """Profile form includes current_password input."""
        with app.app_context():
            user = OpUser(username='profuser3', email='prof3@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'prof3@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        response = client.get('/onepiecetcg/profile')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'current_password' in html
        assert 'id="current_password"' in html or 'name="current_password"' in html

    def test_profile_js_includes_current_password_in_payload(self, app, client):
        """Profile JS fetch payload includes current_password."""
        with app.app_context():
            user = OpUser(username='profuser4', email='prof4@test.com')
            user.set_password('testpass123')
            db.session.add(user)
            db.session.commit()

        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'prof4@test.com', 'password': 'testpass123'}),
            content_type='application/json',
        )

        response = client.get('/onepiecetcg/profile')
        assert response.status_code == 200
        html = response.data.decode('utf-8')
        assert 'current_password' in html
        # JS should reference current_password field in the fetch payload
        assert (
            "document.getElementById('current_password').value" in html
            or "document.getElementById('current_password').value" in html
        )


class TestProfileUpdate:
    """Tests for POST /onepiecetcg/profile/update."""

    def _login(self, client, app, email, password, username):
        """Helper to create user and login."""
        with app.app_context():
            user = OpUser(username=username, email=email)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
        client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': email, 'password': password}),
            content_type='application/json',
        )
        return user

    def test_update_email_success(self, app, client):
        """T1: Successful email update."""
        self._login(client, app, 'old@example.com', 'correctpass', 'upduser')
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps({'current_password': 'correctpass', 'email': 'new@example.com'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            from app.models import OpUser

            user = OpUser.query.filter_by(username='upduser').first()
            assert user.email == 'new@example.com'

    def test_update_password_success(self, app, client):
        """T2: Successful password update."""
        self._login(client, app, 'pwd@test.com', 'oldpass123', 'pwduser')
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps({'current_password': 'oldpass123', 'new_password': 'newpass456'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        # Verify can log in with new password
        client.get('/onepiecetcg/logout')
        login_resp = client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'pwd@test.com', 'password': 'newpass456'}),
            content_type='application/json',
        )
        assert login_resp.status_code == 200

    def test_update_email_and_password_together(self, app, client):
        """T3: Successful email and password update simultaneously."""
        self._login(client, app, 'both@test.com', 'bothpass123', 'bothuser')
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps(
                {'current_password': 'bothpass123', 'email': 'newboth@test.com', 'new_password': 'newbothpass456'}
            ),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            from app.models import OpUser

            user = OpUser.query.filter_by(username='bothuser').first()
            assert user.email == 'newboth@test.com'
        # Verify new password works
        client.get('/onepiecetcg/logout')
        login_resp = client.post(
            '/onepiecetcg/login',
            data=json.dumps({'email': 'newboth@test.com', 'password': 'newbothpass456'}),
            content_type='application/json',
        )
        assert login_resp.status_code == 200

    def test_update_wrong_current_password(self, app, client):
        """T4: Wrong current password returns 403."""
        self._login(client, app, 'wrong@test.com', 'correctpass', 'wronguser')
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps({'current_password': 'wrongpass', 'email': 'new@example.com'}),
            content_type='application/json',
        )
        assert resp.status_code == 403
        data = resp.get_json()
        assert data['success'] is False
        with app.app_context():
            from app.models import OpUser

            user = OpUser.query.filter_by(username='wronguser').first()
            assert user.email == 'wrong@test.com'

    def test_update_missing_current_password(self, app, client):
        """T5: Missing current_password returns 400."""
        self._login(client, app, 'miss@test.com', 'pass123', 'missuser')
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps({'email': 'new@example.com'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_update_no_changes(self, app, client):
        """T6: No changes provided returns 400."""
        self._login(client, app, 'nochg@test.com', 'pass123', 'nochguser')
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps({'current_password': 'pass123'}),
            content_type='application/json',
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_update_unauthenticated(self, client):
        """T7: Unauthenticated access returns 401/302."""
        resp = client.post(
            '/onepiecetcg/profile/update',
            data=json.dumps({'current_password': 'pass123', 'email': 'new@example.com'}),
            content_type='application/json',
            follow_redirects=False,
        )
        assert resp.status_code in (302, 401)
