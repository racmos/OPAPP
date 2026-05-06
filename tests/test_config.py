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

    def test_default_secret_key(self):
        """Config should have a default SECRET_KEY when env var is not set."""
        os.environ.pop('SECRET_KEY', None)
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SECRET_KEY == 'you-will-never-guess'

    def test_secret_key_from_env(self):
        """Config should read SECRET_KEY from environment variable."""
        os.environ['SECRET_KEY'] = 'env-secret-key'
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert cfg.SECRET_KEY == 'env-secret-key'
        os.environ.pop('SECRET_KEY', None)

    def test_default_database_uri(self):
        """Config should have a default DATABASE_URL pointing to PostgreSQL."""
        os.environ.pop('DATABASE_URL', None)
        config_mod = _reload_config()

        cfg = config_mod.Config()
        assert 'postgresql+psycopg' in cfg.SQLALCHEMY_DATABASE_URI
        assert '192.168.1.33' in cfg.SQLALCHEMY_DATABASE_URI
        assert '5432' in cfg.SQLALCHEMY_DATABASE_URI
        assert 'postgres' in cfg.SQLALCHEMY_DATABASE_URI

    def test_database_url_from_env(self):
        """Config should read DATABASE_URL from environment variable."""
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
