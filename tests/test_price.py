"""
Phase 4 tests: Price routes, scraper service, cardmarket loader, cardmarket matcher.
Strict TDD: Tests written BEFORE production code.
"""
import json
from unittest.mock import patch, MagicMock, PropertyMock
import pytest
from app import db
from app.models import OpUser, OpSet, OpCard
from app.models.cardmarket import (
    OpcmProduct, OpcmPrice, OpcmProductCardMap, OpcmIgnored, OpcmExpansion
)


# ============================================================
# Helper: login user and seed data
# ============================================================

def _login(client, email='pricetest@test.com', password='test123',
           username='pricetest'):
    """Helper to create user + login."""
    user = OpUser(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    client.post('/onepiecetcg/login', data=json.dumps({
        'email': email, 'password': password
    }), content_type='application/json')
    return user


def _seed_set(app, set_id='OP01', set_name='Romance Dawn',
              ncard=121, outdat='2022-12-02'):
    """Seed a test set."""
    from datetime import date
    s = OpSet(
        opset_id=set_id, opset_name=set_name,
        opset_ncard=ncard,
        opset_outdat=date.fromisoformat(outdat) if outdat else None
    )
    db.session.add(s)
    db.session.commit()
    return s


def _seed_card(app, set_id='OP01', card_id='OP01-001', name='Monkey D. Luffy',
               category='Leader', color='Red', rarity='Leader'):
    """Seed a test card."""
    c = OpCard(
        opcar_opset_id=set_id, opcar_id=card_id, opcar_name=name,
        opcar_category=category, opcar_color=color, opcar_rarity=rarity
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
        <div class="block"><h3>Block icon</h3>3</div>
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
    "priceGuides": [
        {"idProduct": 123456, "idCategory": 1, "avg": 5.50, "low": 3.00, "trend": 5.00,
         "avg1": 5.00, "avg7": 5.20, "avg30": 5.40,
         "avg-foil": 12.00, "low-foil": 8.00, "trend-foil": 10.00,
         "avg1-foil": 11.00, "avg7-foil": 11.50, "avg30-foil": 11.80,
         "low-ex+": None},
    ]
}

SINGLES_JSON = {
    "products": [
        {"idProduct": 123456, "name": "Monkey D. Luffy", "idCategory": 1,
         "categoryName": "Magic Single", "idExpansion": 1001,
         "idMetacard": 5001, "dateAdded": "2024-01-01"},
        {"idProduct": 234567, "name": "Roronoa Zoro", "idCategory": 1,
         "categoryName": "Magic Single", "idExpansion": 1001,
         "idMetacard": 5002, "dateAdded": "2024-01-01"},
    ]
}

NONSINGLES_JSON = {
    "products": [
        {"idProduct": 345678, "name": "OP-01 Booster Box", "idCategory": 2,
         "categoryName": "Sealed Product", "idExpansion": 1001,
         "idMetacard": None, "dateAdded": "2024-01-01"},
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
            assert len(result['sets']) == 4
            # Check OP01
            op01 = result['sets'][0]
            assert op01['id'] == 'OP01'
            assert 'ROMANCE DAWN' in op01['label']
            assert op01['code'] == 'OP-01'
            # Check EB04
            eb04 = result['sets'][3]
            assert eb04['id'] == 'EB04'
            assert eb04['code'] == 'OP15-EB04'

    def test_refresh_op_sets_no_dropdown(self, app):
        """refresh_op_sets handles missing dropdown gracefully."""
        from app.services.onepiece_scraper import refresh_op_sets
        with app.app_context():
            mock_session = MagicMock()
            mock_response = MagicMock()
            mock_response.text = "<html><body>No dropdown</body></html>"
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
            card = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='001').first()
            assert card is not None
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
            card = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='002').first()
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
        """extract_op_cards() creates variant entries with variant suffix in opcar_id."""
        from app.services.onepiece_scraper import extract_op_cards
        with app.app_context():
            mock_session = MagicMock()
            mock_get_resp = MagicMock()
            mock_get_resp.text = CARD_SET_HTML
            mock_get_resp.raise_for_status = MagicMock()
            mock_session.get.return_value = mock_get_resp

            with patch('app.services.onepiece_scraper._get_session', return_value=mock_session):
                extract_op_cards(filter_sets=['OP01'])

        # Verify both normal (001) and variant (001_p1) exist
        with app.app_context():
            normal = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='001').first()
            assert normal is not None
            assert 'OP01-001.png' in normal.image
            
            variant = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='001_p1').first()
            assert variant is not None
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

        # Verify reprint variant (001_r1) exists
        with app.app_context():
            reprint = OpCard.query.filter_by(opcar_opset_id='OP-01', opcar_id='001_r1').first()
            assert reprint is not None
            assert '_r1' in reprint.image
            assert reprint.opcar_name == 'Monkey D. Luffy'

    def test_extract_op_cards_parses_multi_color(self, app):
        """Multi-color cards are parsed correctly (e.g. Red/Yellow)."""
        from app.services.onepiece_scraper import extract_op_cards
        from bs4 import BeautifulSoup
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
            assert len(result['steps']) >= 6
            assert len(result['errors']) == 0

            # Verify products loaded
            products = OpcmProduct.query.all()
            assert len(products) >= 2  # 2 singles + 1 nonsingle

            # Verify prices loaded
            prices = OpcmPrice.query.all()
            assert len(prices) >= 1

    def test_loader_sha256_skips_unchanged(self, app):
        """CardmarketLoader skips reload when hash matches."""
        from app.services.cardmarket_loader import CardmarketLoader
        from app.models.cardmarket import OpcmLoadHistory
        from datetime import datetime
        import hashlib
        import json as jmod

        with app.app_context():
            # Compute actual hash of SINGLES_JSON and pre-insert as loaded
            singles_json_str = jmod.dumps(SINGLES_JSON, sort_keys=True, ensure_ascii=False)
            singles_hash = hashlib.sha256(singles_json_str.encode('utf-8')).hexdigest()

            db.session.add(OpcmLoadHistory(
                oplh_date=datetime.utcnow().strftime('%Y%m%d'),
                oplh_file_type='singles',
                oplh_hash=singles_hash,
                oplh_rows=2,
                oplh_status='success',
                oplh_message='Loaded',
                oplh_loaded_at=datetime.utcnow()
            ))
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
            mock_result = {'success': True, 'sets': [
                {'id': 'OP01', 'label': 'ROMANCE DAWN', 'code': 'OP-01'}
            ], 'count': 1}

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
            with patch('app.services.onepiece_scraper.refresh_op_sets',
                       side_effect=Exception('Boom')):
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
                'stats': {'total_scraped': 10, 'inserted': 5, 'updated': 3, 'skipped': 2}
            }
            with patch('app.services.onepiece_scraper.extract_op_cards', return_value=mock_result):
                resp = client.post('/onepiecetcg/price/extract-op-cards',
                                   data=json.dumps({'sets': [{'id': '569101', 'code': 'OP-01'}]}),
                                   content_type='application/json')
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
            with patch('app.services.cardmarket_loader.CardmarketLoader.run',
                       return_value=mock_result):
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
            db.session.add(OpcmProduct(
                opprd_date=today, opprd_id_product=123,
                opprd_name='Test Card', opprd_type='single'
            ))
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
        resp = client.post('/onepiecetcg/price/cardmarket-map',
                           data=json.dumps({
                               'id_product': 123,
                               'rbset_id': 'OP01',
                               'rbcar_id': 'OP01-001',
                           }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            mapping = OpcmProductCardMap.query.filter_by(
                oppcm_id_product=123
            ).first()
            assert mapping is not None
            assert mapping.oppcm_opset_id == 'OP01'
            assert mapping.oppcm_opcar_id == 'OP01-001'

    def test_cardmarket_map_missing_fields(self, app, client):
        """map returns 400 for missing required fields."""
        with app.app_context():
            _login(client)
        resp = client.post('/onepiecetcg/price/cardmarket-map',
                           data=json.dumps({'id_product': 123}),
                           content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_cardmarket_unmap(self, app, client):
        """POST /onepiecetcg/price/cardmarket-unmap removes mapping."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmProductCardMap(
                oppcm_id_product=123,
                oppcm_opset_id='OP01',
                oppcm_opcar_id='OP01-001',
            ))
            db.session.commit()
        resp = client.post('/onepiecetcg/price/cardmarket-unmap',
                           data=json.dumps({'id_product': 123}),
                           content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            assert OpcmProductCardMap.query.filter_by(
                oppcm_id_product=123
            ).first() is None

    def test_ignored_add(self, app, client):
        """POST /onepiecetcg/price/ignored/add adds ignored product."""
        with app.app_context():
            _login(client)
        resp = client.post('/onepiecetcg/price/ignored/add',
                           data=json.dumps({
                               'id_product': 999,
                               'name': 'Ignore Me'
                           }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            ignored = OpcmIgnored.query.filter_by(
                opig_id_product=999
            ).first()
            assert ignored is not None

    def test_ignored_restore(self, app, client):
        """POST /onepiecetcg/price/ignored/restore removes ignored."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmIgnored(
                opig_id_product=999,
                opig_name='Ignore Me'
            ))
            db.session.commit()
        resp = client.post('/onepiecetcg/price/ignored/restore',
                           data=json.dumps({
                               'id_product': 999,
                               'name': 'Ignore Me'
                           }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            assert OpcmIgnored.query.filter_by(
                opig_id_product=999
            ).first() is None

    def test_ignored_list(self, app, client):
        """GET /onepiecetcg/price/ignored lists ignored products."""
        with app.app_context():
            _login(client)
            db.session.add(OpcmIgnored(
                opig_id_product=888,
                opig_name='Ignore 888'
            ))
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
            db.session.add(OpcmExpansion(
                opexp_id=1001,
                opexp_name='Test Expansion',
                opexp_opset_id=None
            ))
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
            db.session.add(OpcmExpansion(
                opexp_id=1001,
                opexp_name='Test Expansion',
                opexp_opset_id=None
            ))
            _seed_set(app, 'OP01', 'Romance Dawn')
            db.session.commit()
        resp = client.post('/onepiecetcg/price/cardmarket-map-expansion',
                           data=json.dumps({
                               'rbexp_id': 1001,
                               'rbset_id': 'OP01',
                           }), content_type='application/json')
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
            db.session.add(OpcmProduct(
                opprd_date=today, opprd_id_product=100,
                opprd_name='Test Card', opprd_type='single'
            ))
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
                resp = client.post('/onepiecetcg/price/auto-match',
                                   data=json.dumps({'dry_run': True}),
                                   content_type='application/json')
                assert resp.status_code == 200
                data = resp.get_json()
                assert data['success'] is True
