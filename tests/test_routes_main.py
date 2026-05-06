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
