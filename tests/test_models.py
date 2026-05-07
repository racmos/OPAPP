"""
Tests for SQLAlchemy models — verify table names, schemas, columns, and properties.
"""

import pytest

from app import db


class TestOpUser:
    """Tests for the OpUser model."""

    def test_table_name_is_opusers(self):
        from app.models import OpUser

        assert OpUser.__tablename__ == 'opusers'

    def test_schema_is_onepiecetcg(self):
        from app.models import OpUser

        assert OpUser.__table_args__ == {'schema': 'onepiecetcg'}

    def test_has_required_columns(self):
        from app.models import OpUser

        columns = {c.name for c in OpUser.__table__.columns}
        assert 'id' in columns
        assert 'username' in columns
        assert 'email' in columns
        assert 'password_hash' in columns
        assert 'created_at' in columns

    def test_username_is_unique_indexed(self, app):
        from app.models import OpUser

        with app.app_context():
            user1 = OpUser(username='testuser1', email='test1@test.com')
            user1.set_password('pass')
            db.session.add(user1)
            db.session.commit()

            user2 = OpUser(username='testuser1', email='test2@test.com')  # duplicate username
            user2.set_password('pass')
            db.session.add(user2)
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()


class TestOpSet:
    """Tests for the OpSet model."""

    def test_table_name_is_opsets(self):
        from app.models import OpSet

        assert OpSet.__tablename__ == 'opsets'

    def test_schema_is_onepiecetcg(self):
        from app.models import OpSet

        assert OpSet.__table_args__ == {'schema': 'onepiecetcg'}

    def test_has_required_columns(self):
        from app.models import OpSet

        columns = {c.name for c in OpSet.__table__.columns}
        assert 'opset_id' in columns
        assert 'opset_name' in columns
        assert 'opset_ncard' in columns
        assert 'opset_outdat' in columns

    def test_opset_id_is_primary_key(self):
        from app.models import OpSet

        pk_cols = [c.name for c in OpSet.__table__.primary_key.columns]
        assert 'opset_id' in pk_cols


class TestOpCard:
    """Tests for the OpCard model."""

    def test_table_name_is_opcards(self):
        from app.models import OpCard

        assert OpCard.__tablename__ == 'opcards'

    def test_schema_is_onepiecetcg(self):
        from app.models import OpCard

        assert OpCard.__table_args__ == {'schema': 'onepiecetcg'}

    def test_has_composite_primary_key(self):
        from app.models import OpCard

        pk_cols = {c.name for c in OpCard.__table__.primary_key.columns}
        assert pk_cols == {'opcar_opset_id', 'opcar_id', 'opcar_version'}

    def test_has_one_piece_fields(self):
        from app.models import OpCard

        columns = {c.name for c in OpCard.__table__.columns}
        expected_fields = {
            'opcar_opset_id',
            'opcar_id',
            'opcar_version',
            'opcar_name',
            'opcar_category',
            'opcar_color',
            'opcar_rarity',
            'opcar_cost',
            'opcar_life',
            'opcar_power',
            'opcar_counter',
            'opcar_attribute',
            'opcar_type',
            'opcar_effect',
            'opcar_block_icon',
            'opcar_banned',
            'image_url',
            'image',
        }
        for field in expected_fields:
            assert field in columns, f'Missing field: {field}'
        assert 'opcar_illustration_type' not in columns
        assert 'opcar_artist' not in columns

    def test_opcar_version_defaults_to_p0(self):
        from app.models import OpCard

        card = OpCard(
            opcar_opset_id='OP-01',
            opcar_id='OP01-001',
            opcar_name='Test Card',
        )
        assert card.opcar_version == 'p0'

    def test_image_src_property_with_image(self):
        from app.models import OpCard

        card = OpCard(
            opcar_opset_id='OP-01',
            opcar_id='OP01-001',
            opcar_name='Test Card',
            image='op01_001.png',
        )
        assert card.image_src == '/onepiecetcg/static/images/cards/op-01/op01_001.png'

    def test_image_src_property_with_variant_image(self):
        from app.models import OpCard

        card = OpCard(
            opcar_opset_id='EB-04',
            opcar_id='EB04-001',
            opcar_name='Variant Card',
            image='EB04-001_p1.jpg',
        )
        assert card.image_src == '/onepiecetcg/static/images/cards/eb-04/EB04-001_p1.jpg'

    def test_image_src_property_with_none_image(self):
        from app.models import OpCard

        card = OpCard(
            opcar_opset_id='OP-01',
            opcar_id='OP01-001',
            opcar_name='No Image Card',
        )
        assert card.image_src is None

    def test_image_src_with_promo_set(self):
        """Promo sets should use normalized opset_id folder."""
        from app.models import OpCard

        card = OpCard(
            opcar_opset_id='P',
            opcar_id='P-001',
            opcar_name='Promo Card',
            image='p_001.png',
        )
        assert card.image_src == '/onepiecetcg/static/images/cards/p/p_001.png'


class TestOpCollection:
    """Tests for the OpCollection model."""

    def test_table_name_is_opcollection(self):
        from app.models import OpCollection

        assert OpCollection.__tablename__ == 'opcollection'

    def test_schema_is_onepiecetcg(self):
        from app.models import OpCollection

        assert OpCollection.__table_args__ == {'schema': 'onepiecetcg'}

    def test_has_required_columns(self):
        from app.models import OpCollection

        columns = {c.name for c in OpCollection.__table__.columns}
        expected = {
            'opcol_id',
            'opcol_opset_id',
            'opcol_opcar_id',
            'opcol_opcar_version',
            'opcol_foil',
            'opcol_user',
            'opcol_quantity',
            'opcol_selling',
            'opcol_playset',
            'opcol_sell_price',
            'opcol_condition',
            'opcol_language',
            'opcol_chadat',
        }
        for field in expected:
            assert field in columns, f'Missing field: {field}'

    def test_opcol_id_is_auto_increment(self):
        from app.models import OpCollection

        assert OpCollection.__table__.columns['opcol_id'].autoincrement is True


class TestOpDeck:
    """Tests for the OpDeck model."""

    def test_table_name_is_opdecks(self):
        from app.models import OpDeck

        assert OpDeck.__tablename__ == 'opdecks'

    def test_schema_is_onepiecetcg(self):
        from app.models import OpDeck

        # Deck has UniqueConstraint + schema
        assert OpDeck.__table_args__[1] == {'schema': 'onepiecetcg'}

    def test_has_required_columns(self):
        from app.models import OpDeck

        columns = {c.name for c in OpDeck.__table__.columns}
        expected = {
            'id',
            'opdck_user',
            'opdck_name',
            'opdck_seq',
            'opdck_snapshot',
            'opdck_description',
            'opdck_mode',
            'opdck_format',
            'opdck_max_set',
            'opdck_ncards',
            'opdck_orden',
            'opdck_cards',
        }
        for field in expected:
            assert field in columns, f'Missing field: {field}'

    def test_cards_main_returns_main_deck_cards(self):
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'id': 'OP01-001', 'qty': 4}], 'sideboard': [{'id': 'OP01-002', 'qty': 2}]},
        )
        assert len(deck.cards_main) == 1
        assert deck.cards_main[0]['id'] == 'OP01-001'

    def test_cards_sideboard_returns_sideboard_cards(self):
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'id': 'OP01-001', 'qty': 4}], 'sideboard': [{'id': 'OP01-002', 'qty': 2}]},
        )
        assert len(deck.cards_sideboard) == 1
        assert deck.cards_sideboard[0]['id'] == 'OP01-002'

    def test_cards_combines_main_and_sideboard(self):
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'id': 'OP01-001', 'qty': 4}], 'sideboard': [{'id': 'OP01-002', 'qty': 2}]},
        )
        all_cards = deck.cards
        assert len(all_cards) == 2

    def test_cards_main_empty_when_no_cards(self):
        from app.models import OpDeck

        deck = OpDeck(opdck_user='testuser', opdck_name='Empty')
        assert deck.cards_main == []

    def test_name_alias_returns_opdck_name(self):
        from app.models import OpDeck

        deck = OpDeck(opdck_user='testuser', opdck_name='My Deck')
        assert deck.name == 'My Deck'

    def test_user_alias_returns_opdck_user(self):
        from app.models import OpDeck

        deck = OpDeck(opdck_user='testuser', opdck_name='My Deck')
        assert deck.user == 'testuser'


class TestOpDeckCardMethods:
    """Unit tests for OpDeck.add_card and remove_card instance methods."""

    def test_add_card_creates_new_entry(self):
        """add_card creates a new card entry in the section."""
        from app.models import OpDeck

        deck = OpDeck(opdck_user='testuser', opdck_name='Test Deck')
        result = deck.add_card('main', 'OP01', '001', 2)
        assert len(result) == 1
        assert result[0] == {'set': 'OP01', 'id': '001', 'qty': 2}
        assert deck.opdck_ncards == 2
        assert deck.opdck_cards['main'] == [{'set': 'OP01', 'id': '001', 'qty': 2}]

    def test_add_card_increments_existing(self):
        """add_card increments qty for an existing card."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'set': 'OP01', 'id': '001', 'qty': 1}]},
            opdck_ncards=1,
        )
        result = deck.add_card('main', 'OP01', '001', 1)
        assert result[0]['qty'] == 2
        assert deck.opdck_ncards == 2

    def test_add_card_enforces_4_copy_limit(self):
        """add_card raises ValueError when exceeding 4 copies."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'set': 'OP01', 'id': '001', 'qty': 4}]},
            opdck_ncards=4,
        )
        with pytest.raises(ValueError) as exc_info:
            deck.add_card('main', 'OP01', '001', 1)
        assert '4' in str(exc_info.value)
        assert deck.opdck_ncards == 4  # unchanged

    def test_add_card_enforces_60_main_limit(self):
        """add_card raises ValueError when main deck exceeds 60 cards."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'set': 'OP01', 'id': '001', 'qty': 60}]},
            opdck_ncards=60,
        )
        with pytest.raises(ValueError) as exc_info:
            deck.add_card('main', 'OP01', '002', 1)
        assert '60' in str(exc_info.value)

    def test_add_card_enforces_15_sideboard_limit(self):
        """add_card raises ValueError when sideboard exceeds 15 cards."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'sideboard': [{'set': 'OP01', 'id': '001', 'qty': 15}]},
            opdck_ncards=15,
        )
        with pytest.raises(ValueError) as exc_info:
            deck.add_card('sideboard', 'OP01', '002', 1)
        assert '15' in str(exc_info.value)

    def test_add_card_to_empty_deck_initializes_structure(self):
        """add_card initializes cards structure when None."""
        from app.models import OpDeck

        deck = OpDeck(opdck_user='testuser', opdck_name='Test Deck')
        deck.add_card('sideboard', 'OP02', '999', 1)
        assert deck.opdck_cards == {'main': [], 'sideboard': [{'set': 'OP02', 'id': '999', 'qty': 1}]}
        assert deck.opdck_ncards == 1

    def test_remove_card_decrements_entry(self):
        """remove_card reduces qty for an existing card."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'set': 'OP01', 'id': '001', 'qty': 3}]},
            opdck_ncards=3,
        )
        result = deck.remove_card('main', 'OP01', '001', 1)
        assert result[0]['qty'] == 2
        assert deck.opdck_ncards == 2

    def test_remove_card_deletes_entry_at_zero(self):
        """remove_card removes entry entirely when qty reaches zero."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'set': 'OP01', 'id': '001', 'qty': 2}]},
            opdck_ncards=2,
        )
        result = deck.remove_card('main', 'OP01', '001', 2)
        assert result == []
        assert deck.opdck_ncards == 0
        assert deck.opdck_cards['main'] == []

    def test_remove_card_raises_when_not_found(self):
        """remove_card raises ValueError when card is not in deck."""
        from app.models import OpDeck

        deck = OpDeck(
            opdck_user='testuser',
            opdck_name='Test Deck',
            opdck_cards={'main': [{'set': 'OP01', 'id': '001', 'qty': 2}]},
            opdck_ncards=2,
        )
        with pytest.raises(ValueError) as exc_info:
            deck.remove_card('main', 'OP02', '999', 1)
        assert 'not found' in str(exc_info.value).lower()

    def test_remove_card_raises_when_section_empty(self):
        """remove_card raises ValueError when section has no cards."""
        from app.models import OpDeck

        deck = OpDeck(opdck_user='testuser', opdck_name='Test Deck')
        with pytest.raises(ValueError) as exc_info:
            deck.remove_card('main', 'OP01', '001', 1)
        assert 'not found' in str(exc_info.value).lower()


class TestCardmarketModels:
    """Tests for Cardmarket models."""

    def test_opcm_product_table_name(self):
        from app.models import OpcmProduct

        assert OpcmProduct.__tablename__ == 'opcm_products'

    def test_opcm_product_schema(self):
        from app.models import OpcmProduct

        assert OpcmProduct.__table_args__ == {'schema': 'onepiecetcg'}

    def test_opcm_product_columns(self):
        from app.models import OpcmProduct

        columns = {c.name for c in OpcmProduct.__table__.columns}
        expected = {
            'opprd_date',
            'opprd_id_product',
            'opprd_name',
            'opprd_id_category',
            'opprd_category_name',
            'opprd_id_expansion',
            'opprd_id_metacard',
            'opprd_date_added',
            'opprd_type',
        }
        for field in expected:
            assert field in columns, f'Missing: {field}'

    def test_opcm_price_table_name(self):
        from app.models import OpcmPrice

        assert OpcmPrice.__tablename__ == 'opcm_price'

    def test_opcm_price_schema(self):
        from app.models import OpcmPrice

        assert OpcmPrice.__table_args__ == {'schema': 'onepiecetcg'}

    def test_opcm_price_columns(self):
        from app.models import OpcmPrice

        columns = {c.name for c in OpcmPrice.__table__.columns}
        expected = {
            'opprc_date',
            'opprc_id_product',
            'opprc_id_category',
            'opprc_avg',
            'opprc_low',
            'opprc_trend',
            'opprc_avg1',
            'opprc_avg7',
            'opprc_avg30',
            'opprc_avg_foil',
            'opprc_low_foil',
            'opprc_trend_foil',
            'opprc_avg1_foil',
            'opprc_avg7_foil',
            'opprc_avg30_foil',
            'opprc_low_ex',
        }
        for field in expected:
            assert field in columns, f'Missing: {field}'

    def test_opcm_category_table_name(self):
        from app.models import OpcmCategory

        assert OpcmCategory.__tablename__ == 'opcm_categories'

    def test_opcm_expansion_table_name(self):
        from app.models import OpcmExpansion

        assert OpcmExpansion.__tablename__ == 'opcm_expansions'

    def test_opcm_expansion_uses_opexp_opset_id(self):
        from app.models import OpcmExpansion

        columns = {c.name for c in OpcmExpansion.__table__.columns}
        assert 'opexp_opset_id' in columns

    def test_opcm_load_history_table_name(self):
        from app.models import OpcmLoadHistory

        assert OpcmLoadHistory.__tablename__ == 'opcm_load_history'

    def test_opcm_product_card_map_table_name(self):
        from app.models import OpcmProductCardMap

        assert OpcmProductCardMap.__tablename__ == 'opcm_product_card_map'

    def test_opcm_product_card_map_has_version_column(self):
        from app.models import OpcmProductCardMap

        columns = {c.name for c in OpcmProductCardMap.__table__.columns}
        assert 'oppcm_opcar_version' in columns

    def test_opcm_ignored_table_name(self):
        from app.models import OpcmIgnored

        assert OpcmIgnored.__tablename__ == 'opcm_ignored'

    def test_opproducts_table_name(self):
        from app.models import OpProducts

        assert OpProducts.__tablename__ == 'opproducts'

    def test_opproducts_columns(self):
        from app.models import OpProducts

        columns = {c.name for c in OpProducts.__table__.columns}
        expected = {
            'oppdt_id_set',
            'oppdt_id_product',
            'oppdt_name',
            'oppdt_description',
            'oppdt_type',
            'oppdt_image_url',
            'oppdt_image',
        }
        for field in expected:
            assert field in columns, f'Missing: {field}'
