import os

from flask import Flask
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy
from werkzeug.middleware.proxy_fix import ProxyFix

from app.exceptions import ConfigurationError
from config import Config

db = SQLAlchemy()
login = LoginManager()
login.login_view = 'auth.login'
limiter = Limiter(key_func=get_remote_address)


def create_app(config_class=Config, **test_config):
    # Get the absolute path to the app directory
    app_dir = os.path.dirname(os.path.abspath(__file__))

    app = Flask(
        __name__,
        static_folder=os.path.join(app_dir, 'static'),
        static_url_path='/onepiecetcg/static',
    )
    app.config.from_object(config_class)

    # Apply test configuration overrides before initializing extensions
    if test_config:
        app.config.update(test_config)

    # Validate required configuration in production (not during tests)
    if not app.config.get('TESTING'):
        if not app.config.get('SECRET_KEY'):
            raise ConfigurationError(
                'SECRET_KEY is required. Set it in .env or environment.',
                config_key='SECRET_KEY',
            )
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            raise ConfigurationError(
                'DATABASE_URL is required. Set it in .env or environment.',
                config_key='DATABASE_URL',
            )

    # Fix engine options and schema for SQLite (used in tests)
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', '')
    if db_uri.startswith('sqlite'):
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {'pool_pre_ping': True}
        # SQLite does not support schemas — patch all model __table_args__
        import re
        import sqlite3

        from sqlalchemy import event
        from sqlalchemy.engine import Engine

        def _regexp_replace(value, pattern, replacement, flags=''):
            """SQLite shim for PostgreSQL regexp_replace(value, pattern, replacement, flags)."""
            if value is None:
                return None
            re_flags = 0
            if 'g' in (flags or ''):
                return re.sub(pattern, replacement, str(value), flags=re_flags)
            return re.sub(pattern, replacement, str(value), count=1, flags=re_flags)

        @event.listens_for(Engine, 'connect')
        def set_sqlite_pragma(dbapi_conn, connection_record):
            if isinstance(dbapi_conn, sqlite3.Connection):
                # Register regexp_replace as a custom SQLite function
                dbapi_conn.create_function('regexp_replace', 4, _regexp_replace)
                dbapi_conn.create_function('regexp_replace', 3, _regexp_replace)
                cursor = dbapi_conn.cursor()
                # Attach onepiecetcg schema if not already attached
                cursor.execute('PRAGMA database_list')
                attached = {row[1] for row in cursor.fetchall()}
                if 'onepiecetcg' not in attached:
                    cursor.execute('ATTACH DATABASE ":memory:" AS onepiecetcg')
                cursor.close()

    # Make min/max available in all templates
    from builtins import max as _max
    from builtins import min as _min

    app.jinja_env.globals['min'] = _min
    app.jinja_env.globals['max'] = _max

    db.init_app(app)
    login.init_app(app)

    # Initialize rate limiter (disabled in tests by default)
    if app.config.get('TESTING'):
        app.config.setdefault('RATELIMIT_ENABLED', False)
    limiter.init_app(app)

    # Ensure Flask respects X-Forwarded-* and X-Forwarded-Prefix sent by NGINX
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=0)

    # Register auth blueprint
    from app.routes.auth import auth_bp

    app.register_blueprint(auth_bp)

    # Register main blueprint (dashboard)
    from app.routes.routes import main_bp

    app.register_blueprint(main_bp)

    # Register domain blueprints
    from app.routes.domains import (
        cards_bp,
        collection_bp,
        deck_bp,
        price_bp,
        profile_bp,
        sets_bp,
    )

    app.register_blueprint(sets_bp)
    app.register_blueprint(cards_bp)
    app.register_blueprint(collection_bp)
    app.register_blueprint(deck_bp)
    app.register_blueprint(price_bp)
    app.register_blueprint(profile_bp)

    from app.models import OpUser

    @login.user_loader
    def load_user(id):
        return OpUser.query.get(int(id))

    # Register error handlers
    from app.errors import register_error_handlers

    register_error_handlers(app)

    return app
