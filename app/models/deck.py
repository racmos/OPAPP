import copy
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

    def add_card(self, section: str, set_id: str, card_id: str, quantity: int = 1) -> list[dict]:
        """Add cards to a deck section.

        Raises:
            ValueError: If limits are exceeded (4-copy, 60-main, 15-sideboard).
        """
        cards = copy.deepcopy(self.opdck_cards) if self.opdck_cards else {'main': [], 'sideboard': []}
        section_list = list(cards.get(section, []))

        # Find existing entry
        existing = None
        for card in section_list:
            if card.get('set') == set_id and card.get('id') == card_id:
                existing = card
                break

        current_qty = existing.get('qty', 0) if existing else 0
        new_qty = current_qty + quantity

        # Enforce 4-copy limit
        if new_qty > 4:
            raise ValueError(f'Cannot exceed 4 copies of the same card (currently {current_qty})')

        # Enforce section size limits
        section_total = sum(c.get('qty', 0) for c in section_list)
        new_section_total = section_total + quantity
        if section == 'main' and new_section_total > 60:
            raise ValueError(f'Main deck cannot exceed 60 cards (currently {section_total})')
        if section == 'sideboard' and new_section_total > 15:
            raise ValueError(f'Sideboard cannot exceed 15 cards (currently {section_total})')

        if existing:
            existing['qty'] = new_qty
        else:
            section_list.append({'set': set_id, 'id': card_id, 'qty': quantity})

        cards[section] = section_list
        self.opdck_cards = cards
        self.opdck_ncards = (self.opdck_ncards or 0) + quantity
        return section_list

    def remove_card(self, section: str, set_id: str, card_id: str, quantity: int = 1) -> list[dict]:
        """Remove cards from a deck section.

        Raises:
            ValueError: If card is not found in the section.
        """
        cards = copy.deepcopy(self.opdck_cards) if self.opdck_cards else {'main': [], 'sideboard': []}
        section_list = list(cards.get(section, []))

        existing = None
        idx = -1
        for i, card in enumerate(section_list):
            if card.get('set') == set_id and card.get('id') == card_id:
                existing = card
                idx = i
                break

        if existing is None:
            raise ValueError(f'Card {set_id}-{card_id} not found in {section}')

        new_qty = existing.get('qty', 0) - quantity
        if new_qty <= 0:
            section_list.pop(idx)
        else:
            existing['qty'] = new_qty

        cards[section] = section_list
        self.opdck_cards = cards
        self.opdck_ncards = max(0, (self.opdck_ncards or 0) - quantity)
        return section_list
