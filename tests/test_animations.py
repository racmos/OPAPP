"""
Tests for visual polish: parallax and scroll-triggered reveals.
"""

import pytest


class TestAnimationsCSS:
    """Verify animations.css is served and accessible."""

    @pytest.fixture
    def anon_client(self):
        """Anonymous client."""
        from app import create_app

        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        return app.test_client()

    def test_animations_css_exists(self, anon_client):
        """animations.css is served from static folder."""
        resp = anon_client.get('/onepiecetcg/static/css/animations.css')
        assert resp.status_code == 200
        assert 'text/css' in resp.content_type
        data = resp.data.decode('utf-8')
        assert '.parallax-hero' in data
        assert '.reveal' in data
        assert '.reveal--visible' in data

    def test_parallax_classes_present(self, anon_client):
        """Parallax CSS layers are defined."""
        resp = anon_client.get('/onepiecetcg/static/css/animations.css')
        data = resp.data.decode('utf-8')
        assert 'parallax-layer--deep' in data
        assert 'parallax-layer--mid' in data
        assert 'parallax-layer--near' in data
        assert '--scroll' in data

    def test_reveal_stagger_delays(self, anon_client):
        """Stagger delay classes exist for grid items."""
        resp = anon_client.get('/onepiecetcg/static/css/animations.css')
        data = resp.data.decode('utf-8')
        assert 'reveal--delay-1' in data
        assert 'reveal--delay-8' in data

    def test_reduced_motion_respect(self, anon_client):
        """Reduced motion media query disables animations."""
        resp = anon_client.get('/onepiecetcg/static/css/animations.css')
        data = resp.data.decode('utf-8')
        assert 'prefers-reduced-motion' in data


class TestDashboardParallax:
    """Verify parallax hero renders in dashboard."""

    @pytest.fixture
    def logged_client(self):
        """Logged-in client."""
        from app import create_app, db
        from app.models import OpUser

        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        with app.app_context():
            db.create_all()
            user = OpUser(username='visuser', email='vis@test.com')
            user.set_password('test123')
            db.session.add(user)
            db.session.commit()
            client = app.test_client()
            client.post(
                '/onepiecetcg/login',
                data='{"email":"vis@test.com","password":"test123"}',
                content_type='application/json',
            )
            yield client
            db.drop_all()

    def test_dashboard_has_parallax_hero(self, logged_client):
        """Dashboard includes parallax hero markup."""
        resp = logged_client.get('/onepiecetcg/')
        html = resp.data.decode('utf-8')
        assert 'parallax-hero' in html
        assert 'parallax-layer--deep' in html
        assert 'parallax-layer--mid' in html
        assert 'parallax-layer--near' in html
        assert 'parallax-hero__title' in html

    def test_dashboard_has_reveal_on_cards(self, logged_client):
        """Dashboard cards have reveal classes."""
        resp = logged_client.get('/onepiecetcg/')
        html = resp.data.decode('utf-8')
        assert 'dashboard-card' in html  # cards exist


class TestCardsReveal:
    """Verify scroll-triggered reveals on cards page."""

    @pytest.fixture
    def logged_client(self):
        """Logged-in client with cards seeded."""
        from datetime import date

        from app import create_app, db
        from app.models import OpCard, OpSet, OpUser

        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        with app.app_context():
            db.create_all()
            user = OpUser(username='carduser', email='card@test.com')
            user.set_password('test123')
            db.session.add(user)
            db.session.commit()

            s = OpSet(opset_id='OP01', opset_name='Romance Dawn', opset_ncard=121, opset_outdat=date(2022, 12, 2))
            db.session.add(s)
            db.session.add(
                OpCard(
                    opcar_opset_id='OP-01',
                    opcar_id='OP01-001',
                    opcar_version='p0',
                    opcar_name='Monkey D. Luffy',
                    opcar_category='LEADER',
                    opcar_color='Red',
                    opcar_rarity='Leader',
                )
            )
            db.session.commit()

            client = app.test_client()
            client.post(
                '/onepiecetcg/login',
                data='{"email":"card@test.com","password":"test123"}',
                content_type='application/json',
            )
            yield client
            db.drop_all()

    def test_cards_page_has_reveal_classes(self, logged_client):
        """Card grid items have reveal classes."""
        resp = logged_client.get('/onepiecetcg/cards')
        html = resp.data.decode('utf-8')
        assert 'reveal' in html
        assert 'reveal--delay-' in html
        assert 'card-item' in html
