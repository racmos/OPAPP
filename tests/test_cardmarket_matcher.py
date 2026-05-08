"""
Unit tests for cardmarket_matcher service.
Strict TDD: Tests written BEFORE production code.
"""

import pytest

from app import db
from app.models import OpCard, OpSet
from app.models.cardmarket import (
    OpcmExpansion,
    OpcmIgnored,
    OpcmPrice,
    OpcmProduct,
    OpcmProductCardMap,
)
from app.services.cardmarket_matcher import (
    _build_card_index,
    _expand_slots,
    _get_expansion_to_set_map,
    _get_latest_prices,
    _group_products_by_metacard,
    auto_match,
    card_rank_key,
    normalize_name,
)

# ============================================================
# Helpers
# ============================================================


def _seed_set(set_id='OP-01', set_name='Romance Dawn'):
    """Seed a test set."""
    from datetime import date

    s = OpSet(
        opset_id=set_id,
        opset_name=set_name,
        opset_ncard=121,
        opset_outdat=date.fromisoformat('2022-12-02'),
    )
    db.session.add(s)
    db.session.commit()
    return s


def _seed_card(
    set_id='OP-01',
    card_id='OP01-001',
    name='Monkey D. Luffy',
    rarity='Leader',
    version='p0',
):
    """Seed a test card."""
    c = OpCard(
        opcar_opset_id=set_id,
        opcar_id=card_id,
        opcar_version=version,
        opcar_name=name,
        opcar_category='LEADER',
        opcar_color='Red',
        opcar_rarity=rarity,
    )
    db.session.add(c)
    db.session.commit()
    return c


def _seed_product(date_str, id_product, name, id_expansion, id_metacard=None, ptype='single'):
    """Seed a test product."""
    p = OpcmProduct(
        opprd_date=date_str,
        opprd_id_product=id_product,
        opprd_name=name,
        opprd_id_expansion=id_expansion,
        opprd_id_metacard=id_metacard,
        opprd_type=ptype,
    )
    db.session.add(p)
    db.session.commit()
    return p


def _seed_price(date_str, id_product, low=None, low_foil=None, avg7=None, avg7_foil=None):
    """Seed a test price."""
    pr = OpcmPrice(
        opprc_date=date_str,
        opprc_id_product=id_product,
        opprc_low=low,
        opprc_low_foil=low_foil,
        opprc_avg7=avg7,
        opprc_avg7_foil=avg7_foil,
    )
    db.session.add(pr)
    db.session.commit()
    return pr


# ============================================================
# normalize_name
# ============================================================


class TestNormalizeName:
    """Tests for normalize_name() pure function."""

    @pytest.mark.parametrize(
        'input_name,expected',
        [
            ('Monkey D. Luffy', 'monkey d luffy'),
            ('Roronoa Zoro (Foil)', 'roronoa zoro'),
            ('Nami - Alternate Art', 'nami'),
            ('"Sanji" [Showcase]', 'sanji'),
            ('Brook v.2 Promo', 'brook'),
            ('Tony Tony Chopper Version 3', 'tony tony chopper'),
            ('', ''),
            (None, ''),
            ('FOIL SHOWCASE SIGNED', ''),
            ('123a', ''),  # digits-only after noise removal
            ('Ace 5th', 'ace 5th'),
        ],
    )
    def test_normalize_variants(self, input_name, expected):
        """normalize_name strips variant suffixes, punctuation, and collapses whitespace."""
        assert normalize_name(input_name) == expected

    def test_normalize_preserves_core_name(self):
        """Core card name is preserved after stripping noise."""
        assert normalize_name('Monkey D. Luffy [Foil]') == 'monkey d luffy'

    def test_normalize_lowercases(self):
        """Result is always lowercase."""
        assert normalize_name('MONKEY D. LUFFY') == 'monkey d luffy'


# ============================================================
# card_rank_key
# ============================================================


class TestCardRankKey:
    """Tests for card_rank_key() sort key function."""

    def test_leader_ranks_low(self):
        """Leader rarity has default rank (not in _RARITY_RANK dict → 3.0)."""
        card = OpCard(opcar_rarity='Leader', opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p0')
        key = card_rank_key(card)
        assert key[0] == 3.0  # default rank for unknown rarity

    def test_common_vs_secret_rare(self):
        """Common ranks lower (cheaper) than Secret Rare."""
        common = OpCard(opcar_rarity='Common', opcar_opset_id='OP-01', opcar_id='OP01-001')
        secret = OpCard(opcar_rarity='Secret Rare', opcar_opset_id='OP-01', opcar_id='OP01-002')
        assert card_rank_key(common)[0] < card_rank_key(secret)[0]

    def test_parallel_version_bonus(self):
        """Parallel versions (p1, p2...) get +0.30 bonus."""
        base = OpCard(opcar_rarity='Rare', opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p0')
        parallel = OpCard(opcar_rarity='Rare', opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p1')
        assert card_rank_key(parallel)[0] > card_rank_key(base)[0]

    def test_reprint_version_bonus(self):
        """Reprint versions (r1, r2...) get +0.30 +0.10 = +0.40 bonus."""
        base = OpCard(opcar_rarity='Rare', opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p0')
        reprint = OpCard(opcar_rarity='Rare', opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='r1')
        assert card_rank_key(reprint)[0] > card_rank_key(base)[0]
        # Should be higher than parallel too
        parallel = OpCard(opcar_rarity='Rare', opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p1')
        assert card_rank_key(reprint)[0] > card_rank_key(parallel)[0]

    def test_promo_set_bonus(self):
        """Promo sets (ending in X or starting with PR) get set bonus."""
        normal = OpCard(opcar_rarity='Super Rare', opcar_opset_id='OP-01', opcar_id='OP01-001')
        promo = OpCard(opcar_rarity='Super Rare', opcar_opset_id='PR-01', opcar_id='P-001')
        assert card_rank_key(promo)[0] > card_rank_key(normal)[0]

    def test_sorts_by_set_and_card_id(self):
        """Tie-breaker: opset_id, then opcar_id, then version."""
        card_a = OpCard(opcar_rarity='Common', opcar_opset_id='OP-01', opcar_id='OP01-001')
        card_b = OpCard(opcar_rarity='Common', opcar_opset_id='OP-02', opcar_id='OP02-001')
        assert card_rank_key(card_a) < card_rank_key(card_b)


# ============================================================
# _expand_slots
# ============================================================


class TestExpandSlots:
    """Tests for _expand_slots()."""

    def test_common_has_two_slots(self):
        """Common/Uncommon cards get N and S slots."""
        card = OpCard(opcar_rarity='Common', opcar_opset_id='OP-01', opcar_id='OP01-001')
        slots = _expand_slots(card)
        assert len(slots) == 2
        assert slots[0] == (card, 'N')
        assert slots[1] == (card, 'S')

    def test_rare_has_one_slot(self):
        """Rare cards get one slot (no foil)."""
        card = OpCard(opcar_rarity='Rare', opcar_opset_id='OP-01', opcar_id='OP01-001')
        slots = _expand_slots(card)
        assert len(slots) == 1
        assert slots[0] == (card, None)

    def test_taken_slots_filtered(self):
        """Slots already taken are excluded."""
        card = OpCard(opcar_rarity='Common', opcar_opset_id='OP-01', opcar_id='OP01-001')
        taken = {('OP-01', 'OP01-001', 'p0', 'N')}
        slots = _expand_slots(card, taken=taken)
        assert len(slots) == 1
        assert slots[0] == (card, 'S')

    def test_all_taken_returns_empty(self):
        """When all slots are taken, returns empty list."""
        card = OpCard(opcar_rarity='Common', opcar_opset_id='OP-01', opcar_id='OP01-001')
        taken = {('OP-01', 'OP01-001', 'p0', 'N'), ('OP-01', 'OP01-001', 'p0', 'S')}
        slots = _expand_slots(card, taken=taken)
        assert slots == []


# ============================================================
# _get_latest_prices
# ============================================================


class TestGetLatestPrices:
    """Tests for _get_latest_prices() DB query."""

    def test_empty_db_returns_empty_dict(self, app):
        """No prices in DB → empty dict."""
        with app.app_context():
            result = _get_latest_prices()
            assert result == {}

    def test_returns_latest_price_per_product(self, app):
        """Returns only the latest date's price for each product."""
        with app.app_context():
            _seed_price('20260101', 100, low=5.0, avg7=6.0)
            _seed_price('20260102', 100, low=4.0, avg7=5.5)  # newer
            _seed_price('20260102', 200, low=10.0, avg7=12.0)

            result = _get_latest_prices()

            assert len(result) == 2
            assert result[100] == 4.0  # latest low
            assert result[200] == 10.0

    def test_falls_back_to_low_foil(self, app):
        """When low is None, falls back to low_foil."""
        with app.app_context():
            _seed_price('20260101', 100, low=None, low_foil=15.0)
            result = _get_latest_prices()
            assert result[100] == 15.0

    def test_falls_back_to_avg7(self, app):
        """When low and low_foil are None, falls back to avg7."""
        with app.app_context():
            _seed_price('20260101', 100, low=None, low_foil=None, avg7=8.0)
            result = _get_latest_prices()
            assert result[100] == 8.0

    def test_zero_when_no_price_fields(self, app):
        """Product with all NULL price fields gets 0.0."""
        with app.app_context():
            _seed_price('20260101', 100)
            result = _get_latest_prices()
            assert result[100] == 0.0


# ============================================================
# _get_expansion_to_set_map
# ============================================================


class TestGetExpansionToSetMap:
    """Tests for _get_expansion_to_set_map()."""

    def test_empty_db_returns_empty(self, app):
        """No mapped expansions → empty dict."""
        with app.app_context():
            assert _get_expansion_to_set_map() == {}

    def test_returns_only_mapped_expansions(self, app):
        """Only expansions with opexp_opset_id are included."""
        with app.app_context():
            db.session.add(OpcmExpansion(opexp_id=1001, opexp_opset_id='OP-01'))
            db.session.add(OpcmExpansion(opexp_id=1002, opexp_opset_id=None))  # unmapped
            db.session.commit()

            result = _get_expansion_to_set_map()
            assert result == {1001: 'OP-01'}


# ============================================================
# _group_products_by_metacard
# ============================================================


class TestGroupProductsByMetacard:
    """Tests for _group_products_by_metacard()."""

    def test_no_products_returns_empty(self, app):
        """No products in DB → empty groups."""
        with app.app_context():
            groups, skipped, ignored = _group_products_by_metacard()
            assert groups == {}
            assert skipped == 0
            assert ignored == 0

    def test_groups_by_metacard(self, app):
        """Products grouped by idMetacard."""
        with app.app_context():
            _seed_product('20260101', 100, 'Card A', 1, id_metacard=5001)
            _seed_product('20260101', 101, 'Card B', 1, id_metacard=5001)
            _seed_product('20260101', 200, 'Card C', 2, id_metacard=5002)

            groups, skipped, _ignored = _group_products_by_metacard()

            assert len(groups) == 2
            assert len(groups[5001]) == 2
            assert len(groups[5002]) == 1
            assert skipped == 0

    def test_skips_mapped_products(self, app):
        """Already mapped products are excluded."""
        with app.app_context():
            _seed_product('20260101', 100, 'Card A', 1, id_metacard=5001)
            db.session.add(
                OpcmProductCardMap(
                    oppcm_id_product=100,
                    oppcm_opset_id='OP-01',
                    oppcm_opcar_id='OP01-001',
                    oppcm_opcar_version='p0',
                )
            )
            db.session.commit()

            groups, _skipped, _ignored = _group_products_by_metacard()
            assert 100 not in [p.opprd_id_product for g in groups.values() for p in g]

    def test_skips_no_metacard(self, app):
        """Products without metacard are counted as skipped."""
        with app.app_context():
            _seed_product('20260101', 100, 'Card A', 1, id_metacard=None)

            groups, skipped, _ignored = _group_products_by_metacard()
            assert skipped == 1
            assert 100 not in [p.opprd_id_product for g in groups.values() for p in g]

    def test_skips_ignored(self, app):
        """Ignored products are excluded and counted."""
        with app.app_context():
            _seed_product('20260101', 100, 'Ignore Me', 1, id_metacard=5001)
            db.session.add(OpcmIgnored(opig_id_product=100, opig_name='Ignore Me'))
            db.session.commit()

            ignored_set = {(r.opig_id_product, r.opig_name) for r in OpcmIgnored.query.all()}
            groups, _skipped, ignored_count = _group_products_by_metacard(ignored=ignored_set)
            assert ignored_count == 1
            assert 100 not in [p.opprd_id_product for g in groups.values() for p in g]

    def test_uses_latest_date_only(self, app):
        """Only products from the latest date are considered."""
        with app.app_context():
            _seed_product('20260101', 100, 'Old Card', 1, id_metacard=5001)
            _seed_product('20260102', 200, 'New Card', 1, id_metacard=5002)

            groups, _skipped, _ignored = _group_products_by_metacard()
            assert len(groups) == 1
            assert 5002 in groups


# ============================================================
# _build_card_index
# ============================================================


class TestBuildCardIndex:
    """Tests for _build_card_index()."""

    def test_empty_db(self, app):
        """No cards → empty index."""
        with app.app_context():
            assert _build_card_index() == {}

    def test_indexes_by_normalized_name(self, app):
        """Cards indexed by normalized name."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_card('OP-01', 'OP01-002', 'Roronoa Zoro')

            idx = _build_card_index()

            assert 'monkey d luffy' in idx
            assert 'roronoa zoro' in idx
            assert len(idx['monkey d luffy']) == 1

    def test_groups_same_name(self, app):
        """Multiple cards with same normalized name are grouped."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_set('OP-02', 'Paramount War')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_card('OP-02', 'OP02-001', 'Monkey D. Luffy')  # same name, different set

            idx = _build_card_index()

            assert len(idx['monkey d luffy']) == 2


# ============================================================
# auto_match
# ============================================================


class TestAutoMatch:
    """Integration tests for auto_match()."""

    def test_empty_db_returns_success(self, app):
        """No pending products → success with zeros."""
        with app.app_context():
            result = auto_match(dry_run=True)
            assert result['success'] is True
            assert result['assigned'] == 0
            assert result['unmatched'] == 0

    def test_matches_by_name(self, app):
        """Products matched to cards by normalized name."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy', rarity='Leader')
            _seed_product('20260101', 100, 'Monkey D. Luffy', 1, id_metacard=5001)

            result = auto_match(dry_run=False)

            assert result['assigned'] == 1
            assert result['unmatched'] == 0

            mapping = OpcmProductCardMap.query.get(100)
            assert mapping is not None
            assert mapping.oppcm_opcar_id == 'OP01-001'
            assert mapping.oppcm_foil is None  # Leader = 1 slot

    def test_dry_run_does_not_write(self, app):
        """dry_run=True does not create DB rows."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_product('20260101', 100, 'Monkey D. Luffy', 1, id_metacard=5001)

            result = auto_match(dry_run=True)

            assert result['assigned'] == 1
            assert OpcmProductCardMap.query.get(100) is None

    def test_common_gets_two_slots(self, app):
        """Common cards get N and S slots for two products."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-003', 'Nami', rarity='Common')
            _seed_product('20260101', 100, 'Nami', 1, id_metacard=5001)
            _seed_product('20260101', 101, 'Nami', 1, id_metacard=5001)

            result = auto_match(dry_run=False)

            assert result['assigned'] == 2
            m1 = OpcmProductCardMap.query.get(100)
            m2 = OpcmProductCardMap.query.get(101)
            assert {m1.oppcm_foil, m2.oppcm_foil} == {'N', 'S'}

    def test_unmatched_when_more_products_than_slots(self, app):
        """Extra products beyond slot count are unmatched."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy', rarity='Leader')
            _seed_product('20260101', 100, 'Monkey D. Luffy', 1, id_metacard=5001)
            _seed_product('20260101', 101, 'Monkey D. Luffy', 1, id_metacard=5001)

            result = auto_match(dry_run=False)

            assert result['assigned'] == 1
            assert result['unmatched'] == 1

    def test_respects_existing_mappings(self, app):
        """Already mapped slots are not reused."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-003', 'Nami', rarity='Common')
            # Pre-existing mapping takes N slot
            db.session.add(
                OpcmProductCardMap(
                    oppcm_id_product=99,
                    oppcm_opset_id='OP-01',
                    oppcm_opcar_id='OP01-003',
                    oppcm_opcar_version='p0',
                    oppcm_foil='N',
                )
            )
            db.session.commit()
            _seed_product('20260101', 100, 'Nami', 1, id_metacard=5001)

            result = auto_match(dry_run=False)

            assert result['assigned'] == 1
            m = OpcmProductCardMap.query.get(100)
            assert m.oppcm_foil == 'S'  # only S slot left

    def test_ignores_ignored_products(self, app):
        """Products in OpcmIgnored are skipped."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_product('20260101', 100, 'Ignore Me', 1, id_metacard=5001)
            db.session.add(OpcmIgnored(opig_id_product=100, opig_name='Ignore Me'))
            db.session.commit()

            result = auto_match(dry_run=False)

            assert result['assigned'] == 0
            assert result['ignored_count'] == 1

    def test_no_candidates_when_name_differs(self, app):
        """Product name that doesn't match any card → no_candidates."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_product('20260101', 100, 'Totally Different Name', 1, id_metacard=5001)

            result = auto_match(dry_run=False)

            assert result['no_candidates'] == 1
            assert result['assigned'] == 0

    def test_sorts_by_price(self, app):
        """Products sorted by price ascending get cheaper slots first."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            # Two cards with same normalized name but different rarities/prices
            _seed_card('OP-01', 'OP01-001', 'Test Card', rarity='Common')
            _seed_card('OP-01', 'OP01-002', 'Test Card', rarity='Rare')

            _seed_product('20260101', 100, 'Test Card', 1, id_metacard=5001)
            _seed_price('20260101', 100, low=1.0)

            result = auto_match(dry_run=True)
            assert result['assigned'] == 1

    def test_max_groups_limits_processing(self, app):
        """max_groups limits number of metacard groups processed."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_card('OP-01', 'OP01-002', 'Roronoa Zoro')
            _seed_product('20260101', 100, 'Monkey D. Luffy', 1, id_metacard=5001)
            _seed_product('20260101', 200, 'Roronoa Zoro', 2, id_metacard=5002)

            result = auto_match(dry_run=False, max_groups=1)

            # Only first group processed
            assert result['assigned'] == 1

    def test_samples_populated(self, app):
        """Samples list contains matched product details."""
        with app.app_context():
            _seed_set('OP-01', 'Romance Dawn')
            _seed_card('OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_product('20260101', 100, 'Monkey D. Luffy', 1, id_metacard=5001)
            _seed_price('20260101', 100, low=5.5)

            result = auto_match(dry_run=False)

            assert len(result['samples']) == 1
            sample = result['samples'][0]
            assert sample['id_product'] == 100
            assert sample['rbcar_id'] == 'OP01-001'
            assert sample['price'] == 5.5
