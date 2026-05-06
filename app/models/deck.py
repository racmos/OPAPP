from datetime import datetime

from app import db


class OpDeck(db.Model):
    __tablename__ = 'opdecks'
    __table_args__ = (
        db.UniqueConstraint('opdck_user', 'opdck_name', 'opdck_seq', name='uq_deck_user_name_seq'),
        {'schema': 'onepiecetcg'},
    )

    # Primary key autoincremental
    id = db.Column(db.Integer, primary_key=True)

    # Deck identification
    opdck_user = db.Column(db.Text, nullable=False, index=True)
    opdck_name = db.Column(db.Text, nullable=False, index=True)

    # Sequential: allows multiple decks with same name per user
    opdck_seq = db.Column(db.SmallInteger, default=1)

    # Snapshot with full date/time
    opdck_snapshot = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)

    # Deck metadata
    opdck_description = db.Column(db.Text)
    opdck_mode = db.Column(db.Text, nullable=False, default='1v1')
    opdck_format = db.Column(db.Text, nullable=False, default='Standard')
    opdck_max_set = db.Column(db.Text)
    opdck_ncards = db.Column(db.Integer, default=0)
    opdck_orden = db.Column(db.Numeric)

    # Cards in JSON format
    opdck_cards = db.Column(db.JSON)

    # Class methods for common queries
    @classmethod
    def get_by_user_and_name(cls, user, name, seq=None):
        """Get deck by user, name, and optionally seq."""
        query = cls.query.filter_by(opdck_user=user, opdck_name=name)
        if seq:
            return query.filter_by(opdck_seq=seq).first()
        return query.order_by(cls.opdck_seq.desc()).first()

    @classmethod
    def get_versions(cls, user, name):
        """Get all versions of a deck."""
        return cls.query.filter_by(opdck_user=user, opdck_name=name).order_by(cls.opdck_seq.desc()).all()

    @classmethod
    def get_next_seq(cls, user, name):
        """Calculate the next sequential number for a deck."""
        last_deck = cls.query.filter_by(opdck_user=user, opdck_name=name).order_by(cls.opdck_seq.desc()).first()

        return (last_deck.opdck_seq + 1) if last_deck and last_deck.opdck_seq else 1

    # Properties for accessing cards
    @property
    def cards_main(self):
        """Cards in the main deck."""
        if self.opdck_cards:
            return self.opdck_cards.get('main', [])
        return []

    @property
    def cards_sideboard(self):
        """Cards in the sideboard."""
        if self.opdck_cards:
            return self.opdck_cards.get('sideboard', [])
        return []

    @property
    def cards(self):
        """All cards (for template compatibility)."""
        main = self.cards_main
        sideboard = self.cards_sideboard
        return main + sideboard

    @property
    def name(self):
        """Alias for opdck_name (compatibility)."""
        return self.opdck_name

    @property
    def description(self):
        """Alias for opdck_description (compatibility)."""
        return self.opdck_description

    @property
    def mode(self):
        """Alias for opdck_mode (compatibility)."""
        return self.opdck_mode

    @property
    def format(self):
        """Alias for opdck_format (compatibility)."""
        return self.opdck_format

    @property
    def user(self):
        """Alias for opdck_user (compatibility)."""
        return self.opdck_user

    @property
    def snapshot(self):
        """Alias for opdck_snapshot (compatibility)."""
        return self.opdck_snapshot

    @property
    def max_set(self):
        """Alias for opdck_max_set (compatibility)."""
        return self.opdck_max_set
