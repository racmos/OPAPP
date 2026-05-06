"""
Domain route blueprints — full implementations (Phase 3).
"""

from .cards import cards_bp
from .collection import collection_bp
from .deck import deck_bp
from .price import price_bp
from .profile import profile_bp
from .sets import sets_bp

__all__ = [
    'cards_bp',
    'collection_bp',
    'deck_bp',
    'price_bp',
    'profile_bp',
    'sets_bp',
]
