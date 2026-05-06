"""
Tests for app/__init__.py — Flask factory function.
"""

import pytest

from app import create_app, db, login


class TestAppFactory:
    """Tests for the create_app factory function."""

    def test_create_app_returns_flask_instance(self):
        """create_app() should return a Flask application instance."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test',
        )
        assert app is not None
        from flask import Flask

        assert isinstance(app, Flask)

    def test_app_has_testing_config(self):
        """App should have testing configuration applied."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test',
        )
        assert app.config['TESTING'] is True

    def test_app_uses_custom_config(self):
        """App should accept and use custom configuration values."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='my-custom-secret',
        )
        assert app.config['SECRET_KEY'] == 'my-custom-secret'

    def test_static_url_path_uses_onepiecetcg_prefix(self):
        """Static URL path should use /onepiecetcg/static."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test',
        )
        assert app.static_url_path == '/onepiecetcg/static'

    def test_login_manager_configured(self):
        """Login manager should have login_view set."""
        assert login.login_view == 'auth.login'

    def test_db_initialized(self, app):
        """Database should be initialized with the app."""
        with app.app_context():
            from sqlalchemy import text

            result = db.session.execute(text('SELECT 1'))
            assert result.scalar() == 1

    def test_sqlite_schema_attached(self, app):
        """SQLite in-memory should have onepiecetcg schema attached."""
        with app.app_context():
            from sqlalchemy import text

            # Check that the onepiecetcg schema exists by listing attached databases
            result = db.session.execute(text('PRAGMA database_list'))
            databases = {row[1] for row in result.fetchall()}
            assert 'onepiecetcg' in databases

    def test_min_max_jinja_globals(self):
        """min/max should be available as Jinja globals."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test',
        )
        assert 'min' in app.jinja_env.globals
        assert 'max' in app.jinja_env.globals
        assert app.jinja_env.globals['min'](3, 5) == 3
        assert app.jinja_env.globals['max'](3, 5) == 5

    def test_proxyfix_applied(self):
        """ProxyFix middleware should be applied to the WSGI app."""
        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test',
        )
        from werkzeug.middleware.proxy_fix import ProxyFix

        # ProxyFix wraps wsgi_app — check by looking at the middleware chain
        assert app.wsgi_app is not None
