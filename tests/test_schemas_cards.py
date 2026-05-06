"""
Unit tests for OpCardCreate Pydantic schema.
Strict TDD: tests written BEFORE production code.
"""

import pytest
from pydantic import ValidationError


class TestOpCardCreate:
    """Tests for OpCardCreate schema (app/schemas/cards.py)."""

    def test_opcardcreate_minimal_required_fields(self):
        """Only required fields (opcar_opset_id, opcar_id, opcar_name) → valid."""
        from app.schemas.cards import OpCardCreate

        card = OpCardCreate(
            opcar_opset_id='OP01',
            opcar_id='OP01-001',
            opcar_name='Monkey D. Luffy',
        )
        assert card.opcar_opset_id == 'OP01'
        assert card.opcar_id == 'OP01-001'
        assert card.opcar_name == 'Monkey D. Luffy'
        # Default version is 'p0'
        assert card.opcar_version == 'p0'
        # Optional fields default to None
        assert card.opcar_color is None
        assert card.opcar_category is None
        assert card.opcar_rarity is None

    def test_opcardcreate_all_fields(self):
        """All 17 fields provided → valid."""
        from app.schemas.cards import OpCardCreate

        card = OpCardCreate(
            opcar_opset_id='OP01',
            opcar_id='OP01-001',
            opcar_name='Monkey D. Luffy',
            opcar_version='P1',
            opcar_category='Leader',
            opcar_color='Red',
            opcar_rarity='Leader',
            opcar_cost=1,
            opcar_life=5,
            opcar_power=6000,
            opcar_counter=1000,
            opcar_attribute='Straw Hat',
            opcar_type='Supernova',
            opcar_effect='[Activate: Main] Draw 1 card.',
            image_src='OP01-001.png',
            opcar_banned='N',
            opcar_block_icon=1,
        )
        assert card.opcar_opset_id == 'OP01'
        assert card.opcar_id == 'OP01-001'
        assert card.opcar_name == 'Monkey D. Luffy'
        assert card.opcar_version == 'P1'
        assert card.opcar_category == 'Leader'
        assert card.opcar_color == 'Red'
        assert card.opcar_rarity == 'Leader'
        assert card.opcar_cost == 1
        assert card.opcar_life == 5
        assert card.opcar_power == 6000
        assert card.opcar_counter == 1000
        assert card.opcar_attribute == 'Straw Hat'
        assert card.opcar_type == 'Supernova'
        assert card.opcar_effect == '[Activate: Main] Draw 1 card.'
        assert card.image_src == 'OP01-001.png'
        assert card.opcar_banned == 'N'
        assert card.opcar_block_icon == 1

    def test_opcardcreate_missing_required_rejects(self):
        """Missing opcar_name → ValidationError."""
        from app.schemas.cards import OpCardCreate

        with pytest.raises(ValidationError) as exc_info:
            OpCardCreate(
                opcar_opset_id='OP01',
                opcar_id='OP01-001',
                # opcar_name is missing intentionally
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('opcar_name',) for e in errors)

    def test_opcardcreate_default_version_is_p0(self):
        """No version provided → defaults to 'p0'."""
        from app.schemas.cards import OpCardCreate

        card = OpCardCreate(
            opcar_opset_id='OP01',
            opcar_id='OP01-001',
            opcar_name='Test Card',
            # version NOT provided
        )
        assert card.opcar_version == 'p0'

    def test_opcardcreate_cost_must_be_non_negative(self):
        """cost=-1 → ValidationError."""
        from app.schemas.cards import OpCardCreate

        with pytest.raises(ValidationError) as exc_info:
            OpCardCreate(
                opcar_opset_id='OP01',
                opcar_id='OP01-001',
                opcar_name='Test Card',
                opcar_cost=-1,
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('opcar_cost',) for e in errors)

    def test_opcardcreate_counter_must_be_non_negative(self):
        """counter=-1 → ValidationError."""
        from app.schemas.cards import OpCardCreate

        with pytest.raises(ValidationError) as exc_info:
            OpCardCreate(
                opcar_opset_id='OP01',
                opcar_id='OP01-001',
                opcar_name='Test Card',
                opcar_counter=-1,
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('opcar_counter',) for e in errors)

    def test_opcardcreate_missing_set_id_rejects(self):
        """Missing opcar_opset_id → ValidationError."""
        from app.schemas.cards import OpCardCreate

        with pytest.raises(ValidationError) as exc_info:
            OpCardCreate(
                opcar_id='OP01-001',
                opcar_name='Test Card',
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('opcar_opset_id',) for e in errors)

    def test_opcardcreate_missing_card_id_rejects(self):
        """Missing opcar_id → ValidationError."""
        from app.schemas.cards import OpCardCreate

        with pytest.raises(ValidationError) as exc_info:
            OpCardCreate(
                opcar_opset_id='OP01',
                opcar_name='Test Card',
            )
        errors = exc_info.value.errors()
        assert any(e['loc'] == ('opcar_id',) for e in errors)
