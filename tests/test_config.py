"""
Tests for config.py — Config class and engine_options helper.
"""

import importlib
import os

import pytest


def _reload_config():
    """Reload config module to re-evaluate class attributes with current env."""
    import config

    return importlib.reload(config)


class TestConfig:
    """Tests for the Config class."""

    def test_secret_key_no_hardcoded_fallback(self):
        """Config should NOT have a hardcoded SECRET_KEY fallback."""
        os.environ.pop('SECRET_KEY', None)
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SECRET_KEY is None

    def test_secret_key_from_env(self):
        """Config should read SECRET_KEY from environment variable."""
        os.environ['SECRET_KEY'] = 'env-secret-key'
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SECRET_KEY == 'env-secret-key'
        os.environ.pop('SECRET_KEY', None)

    def test_raises_without_secret_key_in_production(self):
        """create_app should raise RuntimeError if SECRET_KEY is unset and not TESTING."""

        class _TestConfig:
            SECRET_KEY = None
            SQLALCHEMY_DATABASE_URI = 'postgresql+psycopg://user:pass@host:5432/db'
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SQLALCHEMY_ENGINE_OPTIONS = {}

        from app import create_app

        with pytest.raises(RuntimeError, match='SECRET_KEY'):
            create_app(config_class=_TestConfig)

    def test_accepts_secret_key_from_env(self):
        """Config should accept SECRET_KEY from environment."""
        os.environ['SECRET_KEY'] = 'env-secret-key'
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SECRET_KEY == 'env-secret-key'
        os.environ.pop('SECRET_KEY', None)

    def test_database_uri_no_hardcoded_fallback(self):
        """Config should NOT have a hardcoded DATABASE_URL fallback."""
        os.environ.pop('DATABASE_URL', None)
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SQLALCHEMY_DATABASE_URI is None

    def test_database_url_from_env(self):
        """Config should read DATABASE_URL from environment variable."""
        os.environ['DATABASE_URL'] = 'postgresql+psycopg://user:pass@host:5432/db'
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SQLALCHEMY_DATABASE_URI == 'postgresql+psycopg://user:pass@host:5432/db'
        os.environ.pop('DATABASE_URL', None)

    def test_raises_without_database_url_in_production(self):
        """create_app should raise RuntimeError if DATABASE_URL is unset and not TESTING."""

        class _TestConfig:
            SECRET_KEY = 'test-secret-key'
            SQLALCHEMY_DATABASE_URI = None
            SQLALCHEMY_TRACK_MODIFICATIONS = False
            SQLALCHEMY_ENGINE_OPTIONS = {}

        from app import create_app

        with pytest.raises(RuntimeError, match='DATABASE_URL'):
            create_app(config_class=_TestConfig)

    def test_accepts_database_url_from_env(self):
        """Config should accept DATABASE_URL from environment."""
        os.environ['DATABASE_URL'] = 'postgresql+psycopg://user:pass@host:5432/db'
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SQLALCHEMY_DATABASE_URI == 'postgresql+psycopg://user:pass@host:5432/db'
        os.environ.pop('DATABASE_URL', None)

    def test_sqlalchemy_track_modifications_is_false(self):
        """Config should disable SQLALCHEMY_TRACK_MODIFICATIONS."""
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SQLALCHEMY_TRACK_MODIFICATIONS is False

    def test_engine_options_for_postgresql(self):
        """Engine options for PostgreSQL should include client_encoding."""
        config_mod = _reload_config()
        opts = config_mod._engine_options('postgresql+psycopg://host/db')
        assert 'connect_args' in opts
        assert opts['connect_args']['client_encoding'] == 'utf8'
        assert opts['pool_pre_ping'] is True

    def test_engine_options_for_sqlite(self):
        """Engine options for SQLite should NOT include client_encoding."""
        config_mod = _reload_config()
        opts = config_mod._engine_options('sqlite:///:memory:')
        assert 'connect_args' not in opts
        assert opts['pool_pre_ping'] is True


class TestFocusVisibleCSS:
    """CSS should use :focus-visible instead of hiding focus outlines."""

    def test_focus_visible_outline(self):
        """style.css should have :focus-visible rule and no outline:none on :focus."""
        import os

        css_path = os.path.join(os.path.dirname(__file__), '..', 'app', 'static', 'css', 'style.css')
        with open(css_path) as f:
            css = f.read()

        # Must NOT have outline: none in any :focus rule
        assert 'outline: none' not in css, 'Global outline:none found in CSS'

        # Must have :focus-visible rule with styled outline
        assert ':focus-visible' in css, ':focus-visible rule not found in CSS'
        assert 'outline: 2px solid var(--accent)' in css, 'Styled focus-visible outline not found'
