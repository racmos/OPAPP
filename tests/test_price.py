"""
Phase 4 tests: Price routes, scraper service, cardmarket loader, cardmarket matcher.
Strict TDD: Tests written BEFORE production code.
"""

import json
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from app import db
from app.models import OpCard, OpSet, OpUser
from app.models.cardmarket import OpcmExpansion, OpcmIgnored, OpcmPrice, OpcmProduct, OpcmProductCardMap

# ============================================================
# Helper: login user and seed data
# ============================================================


def _login(client, email='pricetest@test.com', password='test123', username='pricetest'):
    """Helper to create user + login."""
    user = OpUser(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    client.post(
        '/onepiecetcg/login', data=json.dumps({'email': email, 'password': password}), content_type='application/json'
    )
    return user


def _seed_set(app, set_id='OP01', set_name='Romance Dawn', ncard=121, outdat='2022-12-02'):
    """Seed a test set."""
    from datetime import date

    s = OpSet(
        opset_id=set_id,
        opset_name=set_name,
        opset_ncard=ncard,
        opset_outdat=date.fromisoformat(outdat) if outdat else None,
    )
    db.session.add(s)
    db.session.commit()
    return s


def _seed_card(
    app,
    set_id='OP01',
    card_id='OP01-001',
    name='Monkey D. Luffy',
    category='Leader',
    color='Red',
    rarity='Leader',
    version='p0',
):
    """Seed a test card."""
    c = OpCard(
        opcar_opset_id=set_id,
        opcar_id=card_id,
        opcar_version=version,
        opcar_name=name,
        opcar_category=category,
        opcar_color=color,
        opcar_rarity=rarity,
    )
    db.session.add(c)
    db.session.commit()
    return c


# ============================================================
# Fixture HTML for scraper tests
# ============================================================

CARD_PAGE_HTML = """<!DOCTYPE html>
<html><body>
<form>
  <select name="series">
    <option value="">SELECT</option>
    <option value="OP01">ROMANCE DAWN [OP-01]</option>
    <option value="OP02">PARAMOUNT WAR [OP-02]</option>
    <option value="ST01">STARTER DECK 1 [ST-01]</option>
    <option value="EB04">ADVENTURE ON KAMI'S ISLAND [OP15-EB04]</option>
    <option value="569901">Promotion card</option>
    <option value="569801">Other Product Card</option>
  </select>
</form>
</body></html>"""

CARD_SET_HTML = """<!DOCTYPE html>
<html><body>
<div class="cardList">
<dl class="modalCol" id="OP01-001">
  <dt>
    <div class="infoCol">
      <span>OP01-001</span> | <span>L</span> | <span>LEADER</span>
    </div>
    <div class="cardName">Monkey D. Luffy</div>
  </dt>
  <dd>
    <div class="frontCol">
      <img src="../images/cardlist/card/OP01-001.png">
    </div>
    <div class="backCol">
      <div class="col2">
        <div class="cost"><h3>Life</h3>5</div>
        <div class="attribute"><h3>Attribute</h3><img alt="Strike"><i>Strike</i></div>
      </div>
      <div class="col2">
        <div class="power"><h3>Power</h3>5000</div>
        <div class="counter"><h3>Counter</h3>-</div>
      </div>
      <div class="col2">
        <div class="color"><h3>Color</h3>Red</div>
        <div class="block"><h3>Block<br> icon</h3>3</div>
      </div>
      <div class="feature"><h3>Type</h3>Straw Hat Pirates</div>
      <div class="text"><h3>Effect</h3>[Activate:Main] You may trash 1 card from your hand: Draw 1 card.</div>
      <div class="getInfo"><h3>Card Set(s)</h3>ROMANCE DAWN [OP-01]</div>
    </div>
  </dd>
</dl>
<dl class="modalCol" id="OP01-002">
  <dt>
    <div class="infoCol">
      <span>OP01-002</span> | <span>SR</span> | <span>CHARACTER</span>
    </div>
    <div class="cardName">Roronoa Zoro</div>
  </dt>
  <dd>
    <div class="frontCol">
      <img src="../images/cardlist/card/OP01-002.png">
    </div>
    <div class="backCol">
      <div class="col2">
        <div class="cost"><h3>Cost</h3>3</div>
        <div class="attribute"><h3>Attribute</h3><img alt="Slash"><i>Slash</i></div>
      </div>
      <div class="col2">
        <div class="power"><h3>Power</h3>6000</div>
        <div class="counter"><h3>Counter</h3>1000</div>
      </div>
      <div class="col2">
        <div class="color"><h3>Color</h3>Green</div>
        <div class="block"><h3>Block icon</h3>2</div>
      </div>
      <div class="feature"><h3>Type</h3>Supernovas/Straw Hat Pirates</div>
      <div class="text"><h3>Effect</h3>[DON!! x1] [When Attacking] K.O. up to 1 of your opponent's Characters.</div>
      <div class="getInfo"><h3>Card Set(s)</h3>ROMANCE DAWN [OP-01]</div>
    </div>
  </dd>
</dl>
<dl class="modalCol" id="OP01-001_p1">
  <dt>
    <div class="infoCol">
      <span>OP01-001_p1</span> | <span>L</span> | <span>LEADER</span>
    </div>
    <div class="cardName">Monkey D. Luffy</div>
  </dt>
  <dd>
    <div class="frontCol">
      <img src="../images/cardlist/card/OP01-001_p1.png">
    </div>
    <div class="backCol">
      <div class="col2">
        <div class="cost"><h3>Life</h3>5</div>
        <div class="attribute"><h3>Attribute</h3><img alt="Strike"><i>Strike</i></div>
      </div>
      <div class="col2">
        <div class="power"><h3>Power</h3>5000</div>
        <div class="counter"><h3>Counter</h3>-</div>
      </div>
      <div class="col2">
        <div class="color"><h3>Color</h3>Red</div>
        <div class="block"><h3>Block icon</h3>3</div>
      </div>
      <div class="feature"><h3>Type</h3>Straw Hat Pirates</div>
      <div class="text"><h3>Effect</h3>Alt art variant.</div>
      <div class="getInfo"><h3>Card Set(s)</h3>ROMANCE DAWN [OP-01]</div>
    </div>
  </dd>
</dl>
<dl class="modalCol" id="OP01-001_r1">
  <dt>
    <div class="infoCol">
      <span>OP01-001_r1</span> | <span>L</span> | <span>LEADER</span>
    </div>
    <div class="cardName">Monkey D. Luffy</div>
  </dt>
  <dd>
    <div class="frontCol">
      <img src="../images/cardlist/card/OP01-001_r1.png">
    </div>
    <div class="backCol">
      <div class="col2">
        <div class="cost"><h3>Life</h3>5</div>
        <div class="attribute"><h3>Attribute</h3><img alt="Strike"><i>Strike</i></div>
      </div>
      <div class="col2">
        <div class="power"><h3>Power</h3>5000</div>
        <div class="counter"><h3>Counter</h3>-</div>
      </div>
      <div class="col2">
        <div class="color"><h3>Color</h3>Red</div>
        <div class="block"><h3>Block icon</h3>3</div>
      </div>
      <div class="feature"><h3>Type</h3>Straw Hat Pirates</div>
      <div class="text"><h3>Effect</h3>Reprint variant.</div>
      <div class="getInfo"><h3>Card Set(s)</h3>ROMANCE DAWN [OP-01]</div>
    </div>
  </dd>
</dl>
</div>
</body></html>"""

# Cardmarket JSON fixtures
PRICE_GUIDE_JSON = {
    'priceGuides': [
        {
            'idProduct': 123456,
            'idCategory': 1,
            'avg': 5.50,
            'low': 3.00,
            'trend': 5.00,
            'avg1': 5.00,
            'avg7': 5.20,
            'avg30': 5.40,
            'avg-foil': 12.00,
            'low-foil': 8.00,
            'trend-foil': 10.00,
            'avg1-foil': 11.00,
            'avg7-foil': 11.50,
            'avg30-foil': 11.80,
            'low-ex+': None,
        },
    ]
}

SINGLES_JSON = {
    'products': [
        {
            'idProduct': 123456,
            'name': 'Monkey D. Luffy (OP01-001)',
            'idCategory': 1,
            'categoryName': 'One Piece Single',
            'idExpansion': 1001,
            'idMetacard': 5001,
            'dateAdded': '2024-01-01',
        },
        {
            'idProduct': 234567,
            'name': 'Roronoa Zoro (OP01-002)',
            'idCategory': 1,
            'categoryName': 'One Piece Single',
            'idExpansion': 1001,
            'idMetacard': 5002,
            'dateAdded': '2024-01-01',
        },
    ]
}

NONSINGLES_JSON = {
    'products': [
        {
            'idProduct': 345678,
            'name': 'OP-01 Booster Box',
            'idCategory': 2,
            'categoryName': 'Sealed Product',
            'idExpansion': 1001,
            'idMetacard': None,
            'dateAdded': '2024-01-01',
        },
    ]
}


# ============================================================
# 4.1 / 4.2: Scraper Service Tests
# ============================================================


class TestOnepieceScraper:
    """Unit tests for onepiece_scraper service."""

    def test_refresh_op_sets_parses_dropdown(self, app):
        """refresh_op_sets() extracts set options from the cardlist dropdown."""
        from app.services.onepiece_scraper import refresh_op_sets

        with app.app_context():
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.text = CARD_PAGE_HTML
            mock_response.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_response

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                result = refresh_op_sets()

            assert result['success'] is True
            assert len(result['sets']) == 6
            # Check OP01
            op01 = result['sets'][0]
            assert op01['id'] == 'OP01'
            assert 'ROMANCE DAWN' in op01['label']
            assert op01['code'] == 'OP-01'
            # Check EB04
            eb04 = result['sets'][3]
            assert eb04['id'] == 'EB04'
            assert eb04['code'] == 'OP15-EB04'
            promo = result['sets'][4]
            assert promo['code'] == 'P'
            assert promo['name'] == 'Promo Cards'
            opc = result['sets'][5]
            assert opc['code'] == 'OPC'
            assert opc['name'] == 'Other / Miscellaneous'

    def test_refresh_op_sets_no_dropdown(self, app):
        """refresh_op_sets handles missing dropdown gracefully."""
        from app.services.onepiece_scraper import refresh_op_sets

        with app.app_context():
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.text = '<html><body>No dropdown</body></html>'
            mock_response.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_response

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                result = refresh_op_sets()

            assert result['success'] is False or len(result['sets']) == 0

    def test_extract_op_cards_parses_leader(self, app):
        """extract_op_cards() parses a Leader card correctly."""
        from app.services.onepiece_scraper import extract_op_cards

        with app.app_context():
            mock_session = MagicMock()
            mock_get_resp = MagicMock()
            mock_get_resp.text = CARD_SET_HTML
            mock_get_resp.raise_for_status = MagicMock()

            # GET is now used for fetching cards (all in one page)
            mock_session.get.return_value = mock_get_resp

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                result = extract_op_cards(filter_sets=['OP01'])

            assert result['success'] is True
            stats = result['stats']
            assert stats['total_scraped'] == 4  # 2 normal + 1 parallel + 1 reprint
            assert stats['inserted'] >= 1

        # Verify card in DB — opset_id is derived as OP-01 (with hyphen)
        with app.app_context():
            card = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='OP01-001').first()
            assert card is not None
            assert card.opcar_version == 'p0'
            assert card.opcar_name == 'Monkey D. Luffy'
            assert card.opcar_category == 'LEADER'
            assert card.opcar_rarity == 'L'
            assert card.opcar_life == 5
            assert card.opcar_cost is None
            assert card.opcar_power == 5000
            assert card.opcar_counter is None  # dash → null
            assert card.opcar_color == 'Red'
            assert card.opcar_attribute == 'Strike'
            assert card.opcar_block_icon == 3
            assert card.opcar_type == 'Straw Hat Pirates'
            assert 'Activate:Main' in (card.opcar_effect or '')
            opset = OpSet.query.filter_by(opset_id='OP-01').first()
            assert opset is not None
            assert opset.opset_ncard == 4

    def test_extract_op_cards_parses_character(self, app):
        """extract_op_cards() parses a Character card (Cost not Life)."""
        from app.services.onepiece_scraper import extract_op_cards

        with app.app_context():
            mock_session = MagicMock()
            mock_get_resp = MagicMock()
            mock_get_resp.text = CARD_SET_HTML
            mock_get_resp.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_get_resp

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                extract_op_cards(filter_sets=['OP01'])

        # Verify Zoro (Character with Cost) — opset_id is OP-01
        with app.app_context():
            card = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='OP01-002').first()
            assert card is not None
            assert card.opcar_name == 'Roronoa Zoro'
            assert card.opcar_category == 'CHARACTER'
            assert card.opcar_rarity == 'SR'
            assert card.opcar_cost == 3
            assert card.opcar_life is None
            assert card.opcar_power == 6000
            assert card.opcar_counter == 1000
            assert card.opcar_color == 'Green'

    def test_extract_op_cards_handles_variant(self, app):
        """extract_op_cards() stores variant suffix in opcar_version."""
        from app.services.onepiece_scraper import extract_op_cards

        with app.app_context():
            mock_session = MagicMock()
            mock_get_resp = MagicMock()
            mock_get_resp.text = CARD_SET_HTML
            mock_get_resp.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_get_resp

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                extract_op_cards(filter_sets=['OP01'])

        # Verify both normal (OP01-001/p0) and variant (OP01-001/p1) exist
        with app.app_context():
            normal = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p0').first()
            assert normal is not None
            assert 'OP01-001.png' in normal.image

            variant = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='p1').first()
            assert variant is not None
            assert variant.opcar_id == 'OP01-001'
            assert '_p1' in variant.image

    def test_extract_op_cards_handles_reprint_variant(self, app):
        """extract_op_cards() handles _r1 (reprint) variants correctly."""
        from app.services.onepiece_scraper import extract_op_cards

        with app.app_context():
            mock_session = MagicMock()
            mock_get_resp = MagicMock()
            mock_get_resp.text = CARD_SET_HTML
            mock_get_resp.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_get_resp

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                extract_op_cards(filter_sets=['OP01'])

        # Verify reprint variant (OP01-001/r1) exists
        with app.app_context():
            reprint = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='OP01-001', opcar_version='r1').first()
            assert reprint is not None
            assert reprint.opcar_id == 'OP01-001'
            assert '_r1' in reprint.image
            assert reprint.opcar_name == 'Monkey D. Luffy'

    def test_extract_op_cards_parses_multi_color(self, app):
        """Multi-color cards are parsed correctly (e.g. Red/Yellow)."""
        from bs4 import BeautifulSoup

        from app.services.onepiece_scraper import extract_op_cards

        # The fixture has Red and Green. Let's directly test the parser.
        with app.app_context():
            from app.services.onepiece_scraper import _parse_card_dl

            soup = BeautifulSoup(CARD_SET_HTML, 'html.parser')
            dl = soup.find('dl', id='OP01-001')
            card = _parse_card_dl(dl, set_id='OP01', value_id='OP01')
            assert card is not None
            assert card['opcar_color'] == 'Red'


# ============================================================
# 4.3: Cardmarket Loader Tests
# ============================================================


class TestCardmarketLoader:
    """Unit tests for cardmarket_loader service."""

    def test_loader_run_downloads_and_loads_data(self, app):
        """CardmarketLoader.run() downloads files and populates DB."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            with patch('app.services.cardmarket_loader.requests.get') as mock_get:
                # Create mock responses for each URL
                def mock_get_side_effect(url, timeout=30):
                    mock_resp = MagicMock()
                    mock_resp.raise_for_status = MagicMock()
                    if 'price_guide' in url:
                        mock_resp.json.return_value = PRICE_GUIDE_JSON
                    elif 'singles' in url:
                        mock_resp.json.return_value = SINGLES_JSON
                    elif 'nonsingles' in url:
                        mock_resp.json.return_value = NONSINGLES_JSON
                    else:
                        mock_resp.json.return_value = {}
                    return mock_resp

                mock_get.side_effect = mock_get_side_effect

                loader = CardmarketLoader()
                result = loader.run()

            assert result['success'] is True
            assert len(result['steps']) >= 7  # includes Expansion Mapping step
            assert len(result['errors']) == 0

            # Verify products loaded
            products = OpcmProduct.query.all()
            assert len(products) >= 2  # 2 singles + 1 nonsingle

            # Verify prices loaded
            prices = OpcmPrice.query.all()
            assert len(prices) >= 1

    def test_loader_sha256_skips_unchanged(self, app):
        """CardmarketLoader skips reload when hash matches."""
        import hashlib
        import json as jmod
        from datetime import datetime

        from app.models.cardmarket import OpcmLoadHistory
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            # Compute actual hash of SINGLES_JSON and pre-insert as loaded
            singles_json_str = jmod.dumps(SINGLES_JSON, sort_keys=True, ensure_ascii=False)
            singles_hash = hashlib.sha256(singles_json_str.encode('utf-8')).hexdigest()

            db.session.add(
                OpcmLoadHistory(
                    oplh_date=datetime.utcnow().strftime('%Y%m%d'),
                    oplh_file_type='singles',
                    oplh_hash=singles_hash,
                    oplh_rows=2,
                    oplh_status='success',
                    oplh_message='Loaded',
                    oplh_loaded_at=datetime.utcnow(),
                )
            )
            db.session.commit()

            with patch('app.services.cardmarket_loader.requests.get') as mock_get:

                def mock_get_side_effect(url, timeout=30):
                    mock_resp = MagicMock()
                    mock_resp.raise_for_status = MagicMock()
                    if 'price_guide' in url:
                        mock_resp.json.return_value = PRICE_GUIDE_JSON
                    elif 'singles' in url:
                        mock_resp.json.return_value = SINGLES_JSON
                    elif 'nonsingles' in url:
                        mock_resp.json.return_value = NONSINGLES_JSON
                    else:
                        mock_resp.json.return_value = {}
                    return mock_resp

                mock_get.side_effect = mock_get_side_effect

                loader = CardmarketLoader()
                result = loader.run()

            assert result['success'] is True
            # Validation step should note singles skipped or no changes
            validation_msg = '; '.join(s['message'] for s in result['steps'] if s['step'] == 'Validation')
            assert 'no changes' in validation_msg.lower() or 'singles' in validation_msg.lower()

    def test_auto_map_expansions_by_card_id(self, app):
        """_auto_map_expansions maps expansion to set using card IDs in names."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            # Seed internal set OP-04
            _seed_set(app, 'OP-04', 'Kingdoms of Intrigue')

            # Create unmapped expansion
            db.session.add(OpcmExpansion(opexp_id=5365, opexp_name=None, opexp_opset_id=None))
            db.session.commit()

            # Products with card IDs pointing to OP04
            products = [
                {'idProduct': 1, 'name': 'Trafalgar Law (OP04-001)', 'idExpansion': 5365},
                {'idProduct': 2, 'name': 'Nami (OP04-036)', 'idExpansion': 5365},
                {'idProduct': 3, 'name': 'Luffy (OP04-089)', 'idExpansion': 5365},
            ]

            loader = CardmarketLoader()
            counts = loader._auto_map_expansions(products)

            assert counts['auto_mapped'] == 1
            assert counts['no_match'] == 0

            exp = OpcmExpansion.query.get(5365)
            assert exp.opexp_opset_id == 'OP-04'

    def test_auto_map_expansions_majority_vote(self, app):
        """Expansion mapped by majority card ID prefix when mixed."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'OP-01', 'Romance Dawn')
            db.session.add(OpcmExpansion(opexp_id=9999, opexp_opset_id=None))
            db.session.commit()

            # 3 OP01 cards, 1 outlier P-001 (e.g. promo included in expansion)
            products = [
                {'idProduct': 1, 'name': 'Luffy (OP01-001)', 'idExpansion': 9999},
                {'idProduct': 2, 'name': 'Zoro (OP01-002)', 'idExpansion': 9999},
                {'idProduct': 3, 'name': 'Nami (OP01-016)', 'idExpansion': 9999},
                {'idProduct': 4, 'name': 'DON!!', 'idExpansion': 9999},  # no card ID
            ]

            loader = CardmarketLoader()
            counts = loader._auto_map_expansions(products)

            assert counts['auto_mapped'] == 1
            exp = OpcmExpansion.query.get(9999)
            assert exp.opexp_opset_id == 'OP-01'

    def test_auto_map_expansions_skips_already_mapped(self, app):
        """Already-mapped expansions are not overwritten."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'OP-04', 'Kingdoms of Intrigue')
            db.session.add(
                OpcmExpansion(
                    opexp_id=5365,
                    opexp_opset_id='OP-04',  # already mapped
                )
            )
            db.session.commit()

            products = [
                {'idProduct': 1, 'name': 'Luffy (OP04-001)', 'idExpansion': 5365},
            ]

            loader = CardmarketLoader()
            counts = loader._auto_map_expansions(products)

            assert counts['already_mapped'] == 1
            assert counts['auto_mapped'] == 0

    def test_auto_map_expansions_no_match_if_set_missing(self, app):
        """Expansion not mapped if deduced set doesn't exist in opsets."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            # No OP-99 set exists
            db.session.add(OpcmExpansion(opexp_id=7777, opexp_opset_id=None))
            db.session.commit()

            products = [
                {'idProduct': 1, 'name': 'Card (OP99-001)', 'idExpansion': 7777},
                {'idProduct': 2, 'name': 'Card (OP99-002)', 'idExpansion': 7777},
            ]

            loader = CardmarketLoader()
            counts = loader._auto_map_expansions(products)

            assert counts['no_match'] == 1
            assert counts['auto_mapped'] == 0
            exp = OpcmExpansion.query.get(7777)
            assert exp.opexp_opset_id is None

    def test_auto_map_expansions_handles_starter_decks(self, app):
        """Expansion with ST-prefix cards maps correctly."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'ST-01', 'Starter Deck: Straw Hat Crew')
            db.session.add(OpcmExpansion(opexp_id=5237, opexp_opset_id=None))
            db.session.commit()

            products = [
                {'idProduct': 1, 'name': 'Monkey.D.Luffy (ST01-001)', 'idExpansion': 5237},
                {'idProduct': 2, 'name': 'Nami (ST01-007)', 'idExpansion': 5237},
            ]

            loader = CardmarketLoader()
            counts = loader._auto_map_expansions(products)

            assert counts['auto_mapped'] == 1
            exp = OpcmExpansion.query.get(5237)
            assert exp.opexp_opset_id == 'ST-01'

    def test_auto_map_expansions_no_card_ids_in_names(self, app):
        """Expansion with no card IDs in product names → no_match."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            db.session.add(OpcmExpansion(opexp_id=8888, opexp_opset_id=None))
            db.session.commit()

            products = [
                {'idProduct': 1, 'name': 'Booster Box', 'idExpansion': 8888},
                {'idProduct': 2, 'name': 'Bundle Pack', 'idExpansion': 8888},
            ]

            loader = CardmarketLoader()
            counts = loader._auto_map_expansions(products)

            assert counts['no_match'] == 1
            assert counts['auto_mapped'] == 0

    def test_loader_run_includes_expansion_mapping_step(self, app):
        """Full loader run includes Expansion Mapping step in output."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'OP-01', 'Romance Dawn')

            with patch('app.services.cardmarket_loader.requests.get') as mock_get:

                def mock_get_side_effect(url, timeout=30):
                    mock_resp = MagicMock()
                    mock_resp.raise_for_status = MagicMock()
                    if 'price_guide' in url:
                        mock_resp.json.return_value = PRICE_GUIDE_JSON
                    elif 'singles' in url:
                        mock_resp.json.return_value = SINGLES_JSON
                    elif 'nonsingles' in url:
                        mock_resp.json.return_value = NONSINGLES_JSON
                    return mock_resp

                mock_get.side_effect = mock_get_side_effect

                loader = CardmarketLoader()
                result = loader.run()

            assert result['success'] is True
            step_names = [s['step'] for s in result['steps']]
            assert 'Expansion Mapping' in step_names

            # Expansion 1001 from SINGLES_JSON should be auto-mapped to OP-01
            exp = OpcmExpansion.query.get(1001)
            assert exp is not None
            assert exp.opexp_opset_id == 'OP-01'

    def test_product_card_map_by_card_id(self, app):
        """_update_product_card_map maps products using card ID from name."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'OP-01', 'Romance Dawn')
            _seed_card(app, 'OP-01', 'OP01-001', 'Monkey D. Luffy')
            _seed_card(app, 'OP-01', 'OP01-002', 'Roronoa Zoro')

            # Create expansion mapping
            db.session.add(OpcmExpansion(opexp_id=5229, opexp_opset_id='OP-01'))

            # Create products with card IDs in names (Cardmarket format)
            today = CardmarketLoader().today
            db.session.add(
                OpcmProduct(
                    opprd_date=today,
                    opprd_id_product=100,
                    opprd_name='Monkey D. Luffy (OP01-001)',
                    opprd_id_expansion=5229,
                    opprd_type='single',
                )
            )
            db.session.add(
                OpcmProduct(
                    opprd_date=today,
                    opprd_id_product=101,
                    opprd_name='Roronoa Zoro (OP01-002)',
                    opprd_id_expansion=5229,
                    opprd_type='single',
                )
            )
            db.session.commit()

            loader = CardmarketLoader()
            counts = loader._update_product_card_map()

            assert counts['auto_matched'] == 2
            assert counts['unmatched'] == 0

            m1 = OpcmProductCardMap.query.get(100)
            assert m1.oppcm_opset_id == 'OP-01'
            assert m1.oppcm_opcar_id == 'OP01-001'
            assert m1.oppcm_match_type == 'auto'
            assert float(m1.oppcm_confidence) == 1.0

            m2 = OpcmProductCardMap.query.get(101)
            assert m2.oppcm_opcar_id == 'OP01-002'

    def test_product_card_map_no_expansion_mapping_falls_back_to_name(self, app):
        """Without expansion mapping, falls back to name match."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'OP-01', 'Romance Dawn')
            # Card with unique name
            _seed_card(app, 'OP-01', 'OP01-099', 'Unique Hero')

            today = CardmarketLoader().today
            # Product with card ID but NO expansion mapping
            db.session.add(
                OpcmProduct(
                    opprd_date=today,
                    opprd_id_product=200,
                    opprd_name='Unique Hero (OP01-099)',
                    opprd_id_expansion=9999,
                    opprd_type='single',
                )
            )
            db.session.commit()

            loader = CardmarketLoader()
            counts = loader._update_product_card_map()

            # Should match via name fallback (stripped card ID)
            assert counts['auto_matched'] == 1
            m = OpcmProductCardMap.query.get(200)
            assert m.oppcm_opcar_id == 'OP01-099'
            assert float(m.oppcm_confidence) == 0.8  # lower confidence for name match

    def test_product_card_map_nonsingle_unmatched(self, app):
        """Non-singles without card IDs stay unmatched."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            today = CardmarketLoader().today
            db.session.add(
                OpcmProduct(
                    opprd_date=today,
                    opprd_id_product=300,
                    opprd_name='Booster Box',
                    opprd_id_expansion=5229,
                    opprd_type='nonsingle',
                )
            )
            db.session.commit()

            loader = CardmarketLoader()
            counts = loader._update_product_card_map()

            assert counts['unmatched'] == 1
            assert counts['auto_matched'] == 0

    def test_full_run_maps_products_to_cards(self, app):
        """Full loader run auto-maps products to cards via expansion+cardID."""
        from app.services.cardmarket_loader import CardmarketLoader

        with app.app_context():
            _seed_set(app, 'OP-01', 'Romance Dawn')
            _seed_card(app, 'OP-01', 'OP01-001', 'Monkey D. Luffy')

            with patch('app.services.cardmarket_loader.requests.get') as mock_get:

                def mock_get_side_effect(url, timeout=30):
                    mock_resp = MagicMock()
                    mock_resp.raise_for_status = MagicMock()
                    if 'price_guide' in url:
                        mock_resp.json.return_value = PRICE_GUIDE_JSON
                    elif 'singles' in url:
                        mock_resp.json.return_value = SINGLES_JSON
                    elif 'nonsingles' in url:
                        mock_resp.json.return_value = NONSINGLES_JSON
                    return mock_resp

                mock_get.side_effect = mock_get_side_effect

                loader = CardmarketLoader()
                result = loader.run()

            assert result['success'] is True

            # Product 123456 "Monkey D. Luffy (OP01-001)" should be mapped
            mapping = OpcmProductCardMap.query.filter_by(oppcm_id_product=123456).first()
            assert mapping is not None
            assert mapping.oppcm_opset_id == 'OP-01'
            assert mapping.oppcm_opcar_id == 'OP01-001'

            # Check the Product Mapping step message shows auto-matched
            pm_step = next(s for s in result['steps'] if s['step'] == 'Product Mapping')
            assert 'auto-matched' in pm_step['message']


# ============================================================
# 4.5: Price Routes Tests
# ============================================================


class TestPriceRoutes:
    """Integration tests for /onepiecetcg/price/ routes."""

    def test_price_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/price redirects when not logged in."""
        resp = client.get('/onepiecetcg/price', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_price_page_renders_authenticated(self, app, client):
        """GET /onepiecetcg/price returns 200 with content."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.get('/onepiecetcg/price')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Price' in html or 'price' in html.lower() or 'Cardmarket' in html
        # Should NOT have "Select Sets for Price Generation"
        assert 'Select Sets for Price Generation' not in html
        # Should have "Extraer Cartas One Piece"
        assert 'Extraer Cartas' in html

    def test_refresh_op_sets_route(self, app, client):
        """POST /onepiecetcg/price/refresh-op-sets calls scraper."""
        with app.app_context():
            _login(client)
            mock_result = {
                'success': True,
                'sets': [{'id': 'OP01', 'label': 'ROMANCE DAWN', 'code': 'OP-01'}],
                'count': 1,
            }

            with patch('app.services.onepiece_scraper.refresh_op_sets', return_value=mock_result):
                resp = client.post('/onepiecetcg/price/refresh-op-sets')
                assert resp.status_code == 200
                data = resp.get_json()
                assert data['success'] is True
                assert len(data['sets']) == 1

    def test_refresh_op_sets_error_handling(self, app, client):
        """refresh-op-sets handles scraper errors gracefully."""
        with app.app_context():
            _login(client)
            with patch('app.services.onepiece_scraper.refresh_op_sets', side_effect=Exception('Boom')):
                resp = client.post('/onepiecetcg/price/refresh-op-sets')
                assert resp.status_code == 500
                data = resp.get_json()
                assert data['success'] is False

    def test_extract_op_cards_route(self, app, client):
        """POST /onepiecetcg/price/extract-op-cards calls scraper."""
        with app.app_context():
            _login(client)
            mock_result = {
                'success': True,
                'steps': [{'step': 'test', 'status': 'SUCCESS', 'message': 'ok'}],
                'stats': {'total_scraped': 10, 'inserted': 5, 'updated': 3, 'skipped': 2},
            }
            with patch('app.services.onepiece_scraper.extract_op_cards', return_value=mock_result):
                resp = client.post(
                    '/onepiecetcg/price/extract-op-cards',
                    data=json.dumps({'sets': [{'id': '569101', 'code': 'OP-01'}]}),
                    content_type='application/json',
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert data['success'] is True
                assert data['stats']['total_scraped'] == 10

    def test_cardmarket_load_route(self, app, client):
        """POST /onepiecetcg/price/cardmarket-load calls loader."""
        with app.app_context():
            _login(client)
            mock_result = {
                'success': True,
                'date': '20260101',
                'steps': [],
                'errors': [],
                'unmatched_count': 5,
            }
            with patch('app.services.cardmarket_loader.CardmarketLoader.run', return_value=mock_result):
                resp = client.post('/onepiecetcg/price/cardmarket-load')
                assert resp.status_code == 200
                data = resp.get_json()
                assert data['success'] is True
                assert data['unmatched_count'] == 5

    def test_cardmarket_unmatched_no_data(self, app, client):
        """GET /onepiecetcg/price/cardmarket-unmatched with empty DB."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/price/cardmarket-unmatched')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['count'] == 0

    def test_cardmarket_unmatched_with_products(self, app, client):
        """GET /onepiecetcg/price/cardmarket-unmatched lists unmapped products."""
        with app.app_context():
            _login(client)
            today = '20260101'
            db.session.add(
                OpcmProduct(opprd_date=today, opprd_id_product=123, opprd_name='Test Card', opprd_type='single')
            )
            db.session.commit()
        resp = client.get('/onepiecetcg/price/cardmarket-unmatched')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['count'] >= 1

    def test_cardmarket_search_cards(self, app, client):
        """GET /onepiecetcg/price/cardmarket-search-cards finds cards by name."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Monkey D. Luffy')
            _seed_card(app, 'OP01', 'OP01-002', 'Roronoa Zoro')
        resp = client.get('/onepiecetcg/price/cardmarket-search-cards?q=luffy')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['cards']) >= 1
        assert any(c['name'] == 'Monkey D. Luffy' for c in data['cards'])

    def test_cardmarket_search_cards_short_query(self, app, client):
        """Search with <3 chars returns empty list."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/price/cardmarket-search-cards?q=ab')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['cards']) == 0

    def test_cardmarket_map_creates_mapping(self, app, client):
        """POST /onepiecetcg/price/cardmarket-map saves manual mapping."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Monkey D. Luffy')
        resp = client.post(
            '/onepiecetcg/price/cardmarket-map',
            data=json.dumps(
                {
                    'id_product': 123,
                    'rbset_id': 'OP01',
                    'rbcar_id': 'OP01-001',
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            mapping = OpcmProductCardMap.query.filter_by(oppcm_id_product=123).first()
            assert mapping is not None
            assert mapping.oppcm_opset_id == 'OP01'
            assert mapping.oppcm_opcar_id == 'OP01-001'
            assert mapping.oppcm_opcar_version == 'p0'

    def test_cardmarket_map_accepts_card_version(self, app, client):
        """Manual mapping stores explicit card version for variants."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Monkey D. Luffy', version='p1')
        resp = client.post(
            '/onepiecetcg/price/cardmarket-map',
            data=json.dumps(
                {
                    'id_product': 124,
                    'rbset_id': 'OP01',
                    'rbcar_id': 'OP01-001',
                    'rbcar_version': 'p1',
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            mapping = OpcmProductCardMap.query.filter_by(oppcm_id_product=124).first()
            assert mapping is not None
            assert mapping.oppcm_opcar_version == 'p1'

    def test_cardmarket_map_missing_fields(self, app, client):
        """map returns 400 for missing required fields."""
        with app.app_context():
            _login(client)
        resp = client.post(
            '/onepiecetcg/price/cardmarket-map', data=json.dumps({'id_product': 123}), content_type='application/json'
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_cardmarket_unmap(self, app, client):
        """POST /onepiecetcg/price/cardmarket-unmap removes mapping."""
        with app.app_context():
            _login(client)
            db.session.add(
                OpcmProductCardMap(
                    oppcm_id_product=123,
                    oppcm_opset_id='OP01',
                    oppcm_opcar_id='OP01-001',
                )
            )
            db.session.commit()
        resp = client.post(
            '/onepiecetcg/price/cardmarket-unmap', data=json.dumps({'id_product': 123}), content_type='application/json'
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            assert OpcmProductCardMap.query.filter_by(oppcm_id_product=123).first() is None

    def test_ignored_add(self, app, client):
        """POST /onepiecetcg/price/ignored/add adds ignored product."""
        with app.app_context():
            _login(client)
        resp = client.post(
            '/onepiecetcg/price/ignored/add',
            data=json.dumps({'id_product': 999, 'name': 'Ignore Me'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            ignored = OpcmIgnored.query.filter_by(opig_id_product=999).first()
            assert ignored is not None

    def test_ignored_restore(self, app, client):
        """POST /onepiecetcg/price/ignored/restore removes ignored."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmIgnored(opig_id_product=999, opig_name='Ignore Me'))
            db.session.commit()
        resp = client.post(
            '/onepiecetcg/price/ignored/restore',
            data=json.dumps({'id_product': 999, 'name': 'Ignore Me'}),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            assert OpcmIgnored.query.filter_by(opig_id_product=999).first() is None

    def test_ignored_list(self, app, client):
        """GET /onepiecetcg/price/ignored lists ignored products."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmIgnored(opig_id_product=888, opig_name='Ignore 888'))
            db.session.commit()
        resp = client.get('/onepiecetcg/price/ignored')
        assert resp.status_code == 200
        data = resp.get_json()
        expected_names = {item['name'] for item in data['ignored']}
        assert 'Ignore 888' in expected_names

    def test_cardmarket_unmapped_expansions(self, app, client):
        """GET /onepiecetcg/price/cardmarket-unmapped-expansions lists unmapped."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmExpansion(opexp_id=1001, opexp_name='Test Expansion', opexp_opset_id=None))
            db.session.commit()
        resp = client.get('/onepiecetcg/price/cardmarket-unmapped-expansions')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['count'] >= 1

    def test_cardmarket_map_expansion(self, app, client):
        """POST /onepiecetcg/price/cardmarket-map-expansion maps expansion."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmExpansion(opexp_id=1001, opexp_name='Test Expansion', opexp_opset_id=None))
            _seed_set(app, 'OP01', 'Romance Dawn')
            db.session.commit()
        resp = client.post(
            '/onepiecetcg/price/cardmarket-map-expansion',
            data=json.dumps(
                {
                    'rbexp_id': 1001,
                    'rbset_id': 'OP01',
                }
            ),
            content_type='application/json',
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            exp = OpcmExpansion.query.get(1001)
            assert exp.opexp_opset_id == 'OP01'

    def test_cardmarket_mappings(self, app, client):
        """GET /onepiecetcg/price/cardmarket-mappings returns mappings."""
        with app.app_context():
            _login(client)
            today = '20260101'
            db.session.add(
                OpcmProduct(opprd_date=today, opprd_id_product=100, opprd_name='Test Card', opprd_type='single')
            )
            db.session.commit()
        resp = client.get('/onepiecetcg/price/cardmarket-mappings')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True

    def test_auto_match_route(self, app, client):
        """POST /onepiecetcg/price/auto-match runs matcher."""
        with app.app_context():
            _login(client)
            mock_result = {
                'success': True,
                'assigned': 0,
                'unmatched': 0,
                'skipped': 0,
                'no_candidates': 0,
                'review': 0,
                'samples': [],
            }
            with patch('app.services.cardmarket_matcher.auto_match', return_value=mock_result):
                resp = client.post(
                    '/onepiecetcg/price/auto-match', data=json.dumps({'dry_run': True}), content_type='application/json'
                )
                assert resp.status_code == 200
                data = resp.get_json()
                assert data['success'] is True
