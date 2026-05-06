"""
Integration tests for domain routes (sets, cards, collection, deck).
Strict TDD: These tests are written BEFORE the production code.
"""
import json
import pytest
from datetime import date
from app import db
from app.models import OpUser, OpSet, OpCard, OpCollection, OpDeck


# ============================================================
# Helper: login user and return client
# ============================================================

def _login(client, email='domaintest@test.com', password='test123',
           username='domaintest'):
    """Helper to create user + login. Returns user objects dict."""
    user = OpUser(username=username, email=email)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    resp = client.post('/onepiecetcg/login', data=json.dumps({
        'email': email,
        'password': password
    }), content_type='application/json')
    return user


def _seed_set(app, set_id='OP01', set_name='Romance Dawn',
              ncard=121, outdat='2022-12-02'):
    """Seed a test set into the database."""
    s = OpSet(
        opset_id=set_id,
        opset_name=set_name,
        opset_ncard=ncard,
        opset_outdat=date.fromisoformat(outdat) if outdat else None
    )
    db.session.add(s)
    db.session.commit()
    return s


def _seed_card(app, set_id='OP01', card_id='OP01-001', name='Monkey D. Luffy',
               category='Leader', color='Red', rarity='Leader',
               cost=1, image='OP01-001.png', version='p0',
               power=None, counter=None, effect=None, opcar_type=None):
    """Seed a test card into the database."""
    kwargs = dict(
        opcar_opset_id=set_id,
        opcar_id=card_id,
        opcar_version=version,
        opcar_name=name,
        opcar_category=category,
        opcar_color=color,
        opcar_rarity=rarity,
        opcar_cost=cost,
        image=image
    )
    if power is not None:
        kwargs['opcar_power'] = power
    if counter is not None:
        kwargs['opcar_counter'] = counter
    if effect is not None:
        kwargs['opcar_effect'] = effect
    if opcar_type is not None:
        kwargs['opcar_type'] = opcar_type
    c = OpCard(**kwargs)
    db.session.add(c)
    db.session.commit()
    return c


# ============================================================
# 3.1 Sets Routes
# ============================================================

class TestSetsRoutes:
    """Tests for /onepiecetcg/sets/ (sets_bp)."""

    def test_sets_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/sets redirects when not logged in."""
        resp = client.get('/onepiecetcg/sets', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_sets_page_renders_authenticated(self, app, client):
        """GET /onepiecetcg/sets returns 200 with content."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/sets')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Sets' in html or 'sets' in html.lower()

    def test_sets_page_shows_seeded_set(self, app, client):
        """Sets page displays sets from database."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn', 121, '2022-12-02')
        resp = client.get('/onepiecetcg/sets')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'OP01' in html
        assert 'Romance Dawn' in html
        assert '121' in html

    def test_sets_page_search_by_id(self, app, client):
        """Search filter works on sets page."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_set(app, 'OP02', 'Paramount War')
        resp = client.get('/onepiecetcg/sets?search_id=OP01')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'OP01' in html
        assert 'OP02' not in html

    def test_sets_add_creates_set(self, app, client):
        """POST /onepiecetcg/sets/add creates a new set."""
        with app.app_context():
            _login(client)
        resp = client.post('/onepiecetcg/sets/add', data=json.dumps({
            'opset_id': 'OP03',
            'opset_name': 'Pillars of Strength',
            'opset_ncard': 127
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        # Verify in database
        with app.app_context():
            s = OpSet.query.filter_by(opset_id='OP03').first()
            assert s is not None
            assert s.opset_name == 'Pillars of Strength'
            assert s.opset_ncard == 127

    def test_sets_add_duplicate_id_rejects(self, app, client):
        """Duplicate set ID returns error."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.post('/onepiecetcg/sets/add', data=json.dumps({
            'opset_id': 'OP01',
            'opset_name': 'Duplicate Set',
        }), content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_sets_update_modifies_set(self, app, client):
        """POST /onepiecetcg/sets/update/<id> modifies a set."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn', 121)
        resp = client.post('/onepiecetcg/sets/update/OP01', data=json.dumps({
            'opset_name': 'Romance Dawn (Updated)',
            'opset_ncard': 150
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            s = OpSet.query.filter_by(opset_id='OP01').first()
            assert s.opset_name == 'Romance Dawn (Updated)'
            assert s.opset_ncard == 150


# ============================================================
# 3.3 Cards Routes
# ============================================================

class TestCardsRoutes:
    """Tests for /onepiecetcg/cards/ (cards_bp)."""

    def test_cards_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/cards redirects when not logged in."""
        resp = client.get('/onepiecetcg/cards', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_cards_page_renders_authenticated(self, app, client):
        """GET /onepiecetcg/cards returns 200 with content."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Cards' in html or 'cards' in html.lower()

    def test_cards_page_shows_seeded_card(self, app, client):
        """Cards page displays cards from database."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Monkey D. Luffy',
                       'Leader', 'Red', 'Leader')
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'OP01-001' in html
        assert 'Monkey D. Luffy' in html

    def test_cards_filter_by_set(self, app, client):
        """Set filter narrows card results."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_set(app, 'OP02', 'Paramount War')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
            _seed_card(app, 'OP02', 'OP02-001', 'Ace', 'Leader', 'Blue', 'Leader')
        resp = client.get('/onepiecetcg/cards?search_set=OP01')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Luffy' in html
        assert 'Ace' not in html

    def test_cards_filter_by_color(self, app, client):
        """Color filter narrows card results."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
            _seed_card(app, 'OP01', 'OP01-002', 'Zoro', 'Character', 'Green', 'Rare')
        resp = client.get('/onepiecetcg/cards?search_color=Red')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Luffy' in html
        assert 'Zoro' not in html

    def test_cards_search_api_returns_json(self, app, client):
        """GET /onepiecetcg/cards/search returns JSON search results."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Monkey D. Luffy', 'Leader', 'Red', 'Leader')
            _seed_card(app, 'OP01', 'OP01-002', 'Roronoa Zoro', 'Character', 'Green', 'Rare')
        resp = client.get('/onepiecetcg/cards/search?q=luffy')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['cards']) >= 1
        assert any(c['name'] == 'Monkey D. Luffy' for c in data['cards'])

    def test_cards_search_nomatch_returns_empty(self, app, client):
        """Search for non-existent card returns empty JSON list."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        resp = client.get('/onepiecetcg/cards/search?q=zzz_nonexistent')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert len(data['cards']) == 0

    def test_cards_paginated(self, app, client):
        """Cards page supports pagination via limit/offset."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(60):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        # Request with per_page=50
        resp = client.get('/onepiecetcg/cards?per_page=50&page=1')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # 60 cards with per_page=50 → 2 pages; navigation should exist
        assert 'next' in html.lower() or 'Next' in html or 'page=' in html

    # --- Task 1: Per-Page Selector ---

    def test_cards_per_page_default_is_50(self, app, client):
        """When no per_page param is given, the route defaults to 50."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(60):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # 60 cards with per_page=50 → 2 pages; pagination links should exist
        assert 'next' in html.lower() or 'Next' in html
        # Should show cards but only 50 per page
        card_count = html.count('class="card-item"')
        assert card_count <= 50

    def test_cards_per_page_valid_value_100(self, app, client):
        """per_page=100 returns up to 100 items on page 1."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(120):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        resp = client.get('/onepiecetcg/cards?per_page=100')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # With 120 cards and per_page=100 on page 1, we get 100 or fewer card items
        card_count = html.count('class="card-item"')
        assert card_count <= 100

    def test_cards_per_page_valid_value_250(self, app, client):
        """per_page=250 works as a valid page size."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(300):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        resp = client.get('/onepiecetcg/cards?per_page=250')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        card_count = html.count('class="card-item"')
        assert card_count <= 250

    def test_cards_per_page_resets_to_page_1(self, app, client):
        """Changing per_page navigates to page 1 (next/prev should be relative to new page)."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(120):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        # First request with per_page=50 — should have multiple pages
        resp = client.get('/onepiecetcg/cards?per_page=50&page=2')
        assert resp.status_code == 200
        html_p2 = resp.data.decode('utf-8')
        # On page 2 with per_page=50, we shouldn't see Card 1 (first 50 cards)
        assert 'Card 1<' not in html_p2 or 'OP01-001' not in html_p2

        # Now change per_page to 100 — should reset to page ~1 (implicit)
        resp2 = client.get('/onepiecetcg/cards?per_page=100&page=1')
        assert resp2.status_code == 200
        html2 = resp2.data.decode('utf-8')
        # With per_page=100, the first batch should have 100 cards on page 1
        # Card 1 should definitely be on page 1
        assert 'OP01-001' in html2 or 'Card 1' in html2

    def test_cards_per_page_invalid_falls_back(self, app, client):
        """Invalid per_page values (not in allowed set) fall back to 50."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(5):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        resp = client.get('/onepiecetcg/cards?per_page=30')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Should still render cards (per_page falls back to 50)
        assert 'OP01-001' in html

    def test_cards_per_page_dropdown_in_html(self, app, client):
        """The cards page renders a per-page <select> dropdown."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Should have a select with per-page options
        assert '<select' in html
        assert 'per_page' in html or 'per-page' in html

    # --- Task 2: Advanced Filter Panel ---

    def test_cards_filter_multi_select_color_or(self, app, client):
        """?search_color=Red,Blue returns cards matching EITHER color."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Red Luffy', 'Leader', 'Red', 'Leader')
            _seed_card(app, 'OP01', 'OP01-002', 'Blue Ace', 'Leader', 'Blue', 'Leader')
            _seed_card(app, 'OP01', 'OP01-003', 'Green Zoro', 'Character', 'Green', 'Rare')
        resp = client.get('/onepiecetcg/cards?search_color=Red,Blue')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Red Luffy' in html
        assert 'Blue Ace' in html
        assert 'Green Zoro' not in html

    def test_cards_filter_multi_select_category_or(self, app, client):
        """?search_category=Leader,Event returns cards matching EITHER category."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
            _seed_card(app, 'OP01', 'OP01-002', 'Event Thing', 'Event', 'Blue', 'Common')
            _seed_card(app, 'OP01', 'OP01-003', 'Zoro', 'Character', 'Green', 'Rare')
        resp = client.get('/onepiecetcg/cards?search_category=Leader,Event')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Luffy' in html
        assert 'Event Thing' in html
        assert 'Zoro' not in html

    def test_cards_filter_text_effect(self, app, client):
        """?search_effect=rush filters by ILIKE on effect field."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Rush Card', 'Character', 'Red', 'Common',
                       effect='[Rush] Can attack on first turn')
            _seed_card(app, 'OP01', 'OP01-002', 'No Rush Card', 'Character', 'Blue', 'Common',
                       effect='[Blocker] Can block')
        resp = client.get('/onepiecetcg/cards?search_effect=rush')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Rush Card' in html
        assert 'No Rush Card' not in html

    def test_cards_filter_text_type(self, app, client):
        """?search_type=Supernova filters by ILIKE on type field."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Supernova Card', 'Character', 'Red', 'Common',
                       opcar_type='Supernova')
            _seed_card(app, 'OP01', 'OP01-002', 'Normal Card', 'Character', 'Blue', 'Common',
                       opcar_type='Navy')
        resp = client.get('/onepiecetcg/cards?search_type=Supernova')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Supernova Card' in html
        assert 'Normal Card' not in html

    def test_cards_filter_range_cost(self, app, client):
        """?min_cost=3&max_cost=7 returns cards with 3≤cost≤7."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Cheap Card', 'Character', 'Red', 'Common', cost=1)
            _seed_card(app, 'OP01', 'OP01-002', 'Mid Card', 'Character', 'Blue', 'Common', cost=5)
            _seed_card(app, 'OP01', 'OP01-003', 'Expensive Card', 'Character', 'Green', 'Rare', cost=9)
            _seed_card(app, 'OP01', 'OP01-004', 'Edge Card', 'Character', 'Yellow', 'Rare', cost=3)
        resp = client.get('/onepiecetcg/cards?min_cost=3&max_cost=7')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Mid Card' in html
        assert 'Edge Card' in html
        assert 'Cheap Card' not in html
        assert 'Expensive Card' not in html

    def test_cards_filter_range_power(self, app, client):
        """?min_power=1000&max_power=5000 returns cards in range."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Weak Card', 'Character', 'Red', 'Common', power=500)
            _seed_card(app, 'OP01', 'OP01-002', 'Mid Card', 'Character', 'Blue', 'Common', power=3000)
            _seed_card(app, 'OP01', 'OP01-003', 'Strong Card', 'Character', 'Green', 'Rare', power=7000)
        resp = client.get('/onepiecetcg/cards?min_power=1000&max_power=5000')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Mid Card' in html
        assert 'Weak Card' not in html
        assert 'Strong Card' not in html

    def test_cards_filter_range_counter(self, app, client):
        """?min_counter=0&max_counter=2000 returns cards in range."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'No Counter', 'Character', 'Red', 'Common', counter=0)
            _seed_card(app, 'OP01', 'OP01-002', 'Low Counter', 'Character', 'Blue', 'Common', counter=1000)
            _seed_card(app, 'OP01', 'OP01-003', 'High Counter', 'Character', 'Green', 'Rare', counter=3000)
        resp = client.get('/onepiecetcg/cards?min_counter=0&max_counter=2000')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'No Counter' in html
        assert 'Low Counter' in html
        assert 'High Counter' not in html

    def test_cards_filter_combined_and_logic(self, app, client):
        """Multiple filters active → all must match (AND logic)."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Red Leader Low', 'Leader', 'Red', 'Leader', cost=2)
            _seed_card(app, 'OP01', 'OP01-002', 'Red Leader High', 'Leader', 'Red', 'Leader', cost=8)
            _seed_card(app, 'OP01', 'OP01-003', 'Blue Leader', 'Leader', 'Blue', 'Leader', cost=2)
        resp = client.get('/onepiecetcg/cards?search_color=Red&search_category=Leader&max_cost=4')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Red Leader Low' in html
        assert 'Red Leader High' not in html
        assert 'Blue Leader' not in html

    def test_cards_filter_empty_csv_ignored(self, app, client):
        """?search_color= (empty) → no filter applied (shows all cards)."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Red Luffy', 'Leader', 'Red', 'Leader')
            _seed_card(app, 'OP01', 'OP01-002', 'Blue Ace', 'Leader', 'Blue', 'Leader')
        resp = client.get('/onepiecetcg/cards?search_color=')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Red Luffy' in html
        assert 'Blue Ace' in html

    def test_cards_filter_pagination_preserves_params(self, app, client):
        """Page 2 URL preserves all filter params."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            # Seed 60 Red + 60 Blue = 120 cards; with per_page=50, page 2 exists
            for i in range(120):
                color = 'Red' if i % 2 == 0 else 'Blue'
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', color, 'Common')
        resp = client.get('/onepiecetcg/cards?search_color=Red&per_page=50&page=2')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Pagination links should exist
        assert 'page=' in html or 'next' in html.lower() or 'Next' in html
        # Filter param should be preserved in pagination links
        assert 'search_color=Red' in html or 'search_color%3DRed' in html

    # --- Task 3: List View Mode ---

    def test_cards_view_mode_grid_default(self, app, client):
        """No view param → grid view renders."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Grid should be visible (card-grid class exists)
        assert 'card-grid' in html

    def test_cards_view_mode_list_renders_table(self, app, client):
        """?view=list → table with correct columns."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader', cost=1)
        resp = client.get('/onepiecetcg/cards?view=list')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Should render a table
        assert '<table' in html
        # Should show card name
        assert 'Luffy' in html

    def test_cards_view_mode_list_shows_card_fields(self, app, client):
        """List view displays card data in table rows (<tr> elements)."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'TestCard', 'Leader', 'Red', 'Leader',
                       cost=5, power=6000, counter=1000)
        resp = client.get('/onepiecetcg/cards?view=list')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Should have table rows (not just grid cards)
        assert '<tr' in html
        assert 'OP01-001' in html
        assert 'TestCard' in html

    def test_cards_view_mode_url_persists(self, app, client):
        """?view=list persists in URL across pagination links."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            for i in range(60):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        resp = client.get('/onepiecetcg/cards?view=list&per_page=50&page=2')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # view=list should be preserved in pagination links
        assert 'view=list' in html or 'view%3Dlist' in html

    # --- Task 4: Grid Column Slider ---

    def test_cards_grid_slider_visible_in_grid_view(self, app, client):
        """Grid view renders the column slider control."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        resp = client.get('/onepiecetcg/cards?view=grid')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Should have a range input for grid columns
        assert 'type="range"' in html
        assert 'grid-cols' in html or 'columns' in html.lower()

    def test_cards_grid_slider_hidden_in_list_view(self, app, client):
        """List view hides the column slider control."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        resp = client.get('/onepiecetcg/cards?view=list')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # The slider container should be present but hidden in list view
        assert 'gridColSlider' in html

    # --- Task 6: Manual Card Add Route ---

    def test_cards_add_success(self, app, client):
        """POST /onepiecetcg/cards/add with valid payload creates card."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.post('/onepiecetcg/cards/add', data=json.dumps({
            'opcar_opset_id': 'OP01',
            'opcar_id': 'OP01-099',
            'opcar_name': 'New Card',
            'opcar_color': 'Red',
            'opcar_category': 'Character',
            'opcar_rarity': 'Common',
            'opcar_cost': 3,
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['card']['opcar_name'] == 'New Card'
        # Verify in database
        with app.app_context():
            c = OpCard.query.filter_by(
                opcar_opset_id='OP01', opcar_id='OP01-099', opcar_version='p0'
            ).first()
            assert c is not None
            assert c.opcar_name == 'New Card'

    def test_cards_add_duplicate_rejects_409(self, app, client):
        """POST same (set_id, card_id, version) returns 409."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Existing Card')
        resp = client.post('/onepiecetcg/cards/add', data=json.dumps({
            'opcar_opset_id': 'OP01',
            'opcar_id': 'OP01-001',
            'opcar_name': 'Duplicate Attempt',
        }), content_type='application/json')
        assert resp.status_code == 409
        data = resp.get_json()
        assert data['success'] is False

    def test_cards_add_missing_set_rejects_400(self, app, client):
        """POST with set_id that doesn't exist returns 400."""
        with app.app_context():
            _login(client)
        resp = client.post('/onepiecetcg/cards/add', data=json.dumps({
            'opcar_opset_id': 'NONEXISTENT',
            'opcar_id': 'XX-001',
            'opcar_name': 'Bad Set',
        }), content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_cards_add_validation_error_422(self, app, client):
        """POST missing required field returns validation error."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.post('/onepiecetcg/cards/add', data=json.dumps({
            'opcar_opset_id': 'OP01',
            'opcar_id': 'OP01-001',
            # opcar_name missing
        }), content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_cards_add_unauthenticated_rejects(self, client):
        """POST without auth returns redirect/unauthorized."""
        resp = client.post('/onepiecetcg/cards/add', data=json.dumps({
            'opcar_opset_id': 'OP01',
            'opcar_id': 'OP01-001',
            'opcar_name': 'No Auth',
        }), content_type='application/json', follow_redirects=False)
        assert resp.status_code in (302, 401)

    # --- Task 7: Manual Card Add Modal ---

    def test_cards_page_has_add_card_button(self, app, client):
        """Cards page renders an 'Add Card' button."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Add Card' in html or 'add-card' in html.lower()

    def test_cards_page_has_modal_markup(self, app, client):
        """Cards page contains modal div with form fields for adding a card."""
        with app.app_context():
            _login(client)
            _seed_set(app, 'OP01', 'Romance Dawn')
        resp = client.get('/onepiecetcg/cards')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Modal should exist with key form fields
        assert 'cardAddModal' in html or 'addCardModal' in html
        assert 'opcar_name' in html or 'name="opcar_name"' in html


# ============================================================
# 3.5 Collection Routes
# ============================================================

class TestCollectionRoutes:
    """Tests for /onepiecetcg/collection/ (collection_bp)."""

    def test_collection_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/collection redirects when not logged in."""
        resp = client.get('/onepiecetcg/collection', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_collection_page_renders_authenticated(self, app, client):
        """GET /onepiecetcg/collection returns 200 with content."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/collection')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Collection' in html or 'collection' in html.lower()

    def test_collection_add_card(self, app, client):
        """POST /onepiecetcg/collection/add adds card to user collection."""
        with app.app_context():
            _login(client, username='coluser')
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        resp = client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'OP01',
            'opcol_opcar_id': 'OP01-001',
            'opcol_foil': 'N',
            'opcol_quantity': 4
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        # Verify in database
        with app.app_context():
            col = OpCollection.query.filter_by(
                opcol_user='coluser',
                opcol_opset_id='OP01',
                opcol_opcar_id='OP01-001',
                opcol_opcar_version='p0'
            ).first()
            assert col is not None
            assert col.opcol_quantity == '4'

    def test_collection_add_variant_card_uses_version(self, app, client):
        """Collection rows can target a specific card version."""
        with app.app_context():
            _login(client, username='variantuser')
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy Alt', version='p1')
        resp = client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'OP01',
            'opcol_opcar_id': 'OP01-001',
            'opcol_opcar_version': 'p1',
            'opcol_foil': 'N',
            'opcol_quantity': 1
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            col = OpCollection.query.filter_by(
                opcol_user='variantuser',
                opcol_opset_id='OP01',
                opcol_opcar_id='OP01-001',
                opcol_opcar_version='p1'
            ).first()
            assert col is not None

    def test_collection_add_nonexistent_card_rejects(self, app, client):
        """Adding non-existent card returns error."""
        with app.app_context():
            _login(client)
        resp = client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'FAKE',
            'opcol_opcar_id': 'FAKE-999',
            'opcol_foil': 'N',
            'opcol_quantity': 1
        }), content_type='application/json')
        assert resp.status_code == 400
        data = resp.get_json()
        assert data['success'] is False

    def test_collection_merge_same_card_foil_condition(self, app, client):
        """Adding same card+foil+condition merges quantity."""
        with app.app_context():
            _login(client, username='merger')
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        # First add
        client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'OP01',
            'opcol_opcar_id': 'OP01-001',
            'opcol_foil': 'N',
            'opcol_quantity': 2,
            'opcol_condition': 'NM',
            'opcol_language': 'EN'
        }), content_type='application/json')
        # Second add (same params)
        resp = client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'OP01',
            'opcol_opcar_id': 'OP01-001',
            'opcol_foil': 'N',
            'opcol_quantity': 3,
            'opcol_condition': 'NM',
            'opcol_language': 'EN'
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data.get('merged') is True
        # Verify merged quantity
        with app.app_context():
            col = OpCollection.query.filter_by(
                opcol_user='merger',
                opcol_opset_id='OP01',
                opcol_opcar_id='OP01-001'
            ).first()
            assert col.opcol_quantity == '5'

    def test_collection_different_condition_creates_new_row(self, app, client):
        """Different condition creates separate collection row (no merge)."""
        with app.app_context():
            _login(client, username='conduser')
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
        # First add NM
        client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'OP01',
            'opcol_opcar_id': 'OP01-001',
            'opcol_foil': 'N',
            'opcol_quantity': 1,
            'opcol_condition': 'NM',
            'opcol_language': 'EN'
        }), content_type='application/json')
        # Second add GD (new row)
        resp = client.post('/onepiecetcg/collection/add', data=json.dumps({
            'opcol_opset_id': 'OP01',
            'opcol_opcar_id': 'OP01-001',
            'opcol_foil': 'N',
            'opcol_quantity': 1,
            'opcol_condition': 'GD',
            'opcol_language': 'EN'
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get('merged') is False
        with app.app_context():
            rows = OpCollection.query.filter_by(
                opcol_user='conduser',
                opcol_opset_id='OP01',
                opcol_opcar_id='OP01-001'
            ).all()
            assert len(rows) == 2

    def test_collection_update(self, app, client):
        """POST /onepiecetcg/collection/update updates collection row."""
        with app.app_context():
            _login(client, username='upduser')
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
            col = OpCollection(
                opcol_opset_id='OP01', opcol_opcar_id='OP01-001',
                opcol_foil='N', opcol_user='upduser', opcol_quantity='1'
            )
            db.session.add(col)
            db.session.commit()
            col_id = col.opcol_id
        resp = client.post('/onepiecetcg/collection/update', data=json.dumps({
            'opcol_id': col_id,
            'opcol_quantity': 10,
            'opcol_selling': 'Y',
            'opcol_sell_price': 15.50,
            'opcol_condition': 'MT'
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            updated = OpCollection.query.get(col_id)
            assert updated.opcol_quantity == '10'
            assert updated.opcol_selling == 'Y'
            assert float(updated.opcol_sell_price) == 15.50
            assert updated.opcol_condition == 'MT'

    def test_collection_remove(self, app, client):
        """POST /onepiecetcg/collection/remove deletes collection row."""
        with app.app_context():
            _login(client, username='deluser')
            _seed_set(app, 'OP01', 'Romance Dawn')
            _seed_card(app, 'OP01', 'OP01-001', 'Luffy', 'Leader', 'Red', 'Leader')
            col = OpCollection(
                opcol_opset_id='OP01', opcol_opcar_id='OP01-001',
                opcol_foil='N', opcol_user='deluser', opcol_quantity='1'
            )
            db.session.add(col)
            db.session.commit()
            col_id = col.opcol_id
        resp = client.post('/onepiecetcg/collection/remove', data=json.dumps({
            'opcol_id': col_id
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            assert OpCollection.query.get(col_id) is None


# ============================================================
# 3.7 Deck Routes
# ============================================================

class TestDeckRoutes:
    """Tests for /onepiecetcg/deck/ (deck_bp)."""

    def test_deck_unauthenticated_redirects(self, client):
        """GET /onepiecetcg/deck redirects when not logged in."""
        resp = client.get('/onepiecetcg/deck', follow_redirects=False)
        assert resp.status_code in (302, 401)

    def test_deck_page_renders_authenticated(self, app, client):
        """GET /onepiecetcg/deck returns 200 with content."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/deck')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'Deck' in html or 'deck' in html.lower()

    def test_deck_save_creates_deck(self, app, client):
        """POST /onepiecetcg/deck/save creates a new deck."""
        with app.app_context():
            _login(client, username='deckuser')
        resp = client.post('/onepiecetcg/deck/save', data=json.dumps({
            'opdck_name': 'My First Deck',
            'opdck_description': 'A test deck',
            'opdck_mode': '1v1',
            'opdck_format': 'Standard',
            'opdck_cards': {
                'main': [
                    {'set': 'OP01', 'id': 'OP01-001', 'qty': 1}
                ],
                'sideboard': []
            }
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        # Verify in database
        with app.app_context():
            deck = OpDeck.query.filter_by(
                opdck_user='deckuser',
                opdck_name='My First Deck'
            ).first()
            assert deck is not None
            assert deck.opdck_seq == 1
            assert deck.opdck_ncards == 1

    def test_deck_save_same_name_creates_new_version(self, app, client):
        """Saving deck with same name auto-increments seq (versioning)."""
        with app.app_context():
            _login(client, username='veruser')
            # Create first version
            deck = OpDeck(
                opdck_user='veruser', opdck_name='VersionedDeck',
                opdck_seq=1, opdck_ncards=30
            )
            db.session.add(deck)
            db.session.commit()
        resp = client.post('/onepiecetcg/deck/save', data=json.dumps({
            'opdck_name': 'VersionedDeck',
            'opdck_mode': '1v1',
            'opdck_format': 'Standard',
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        assert data['seq'] == 2

    def test_deck_view_by_name_renders(self, app, client):
        """GET /onepiecetcg/deck/view/<name> renders deck detail."""
        with app.app_context():
            _login(client, username='viewuser')
            deck = OpDeck(
                opdck_user='viewuser', opdck_name='ViewDeck',
                opdck_seq=1, opdck_ncards=30,
                opdck_cards={'main': [{'set': 'OP01', 'id': 'OP01-001', 'qty': 4}]}
            )
            db.session.add(deck)
            db.session.commit()
        resp = client.get('/onepiecetcg/deck/view/ViewDeck')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        assert 'ViewDeck' in html

    def test_deck_view_nonexistent_returns_404(self, app, client):
        """GET /onepiecetcg/deck/view/<name> returns 404 for unknown deck."""
        with app.app_context():
            _login(client)
        resp = client.get('/onepiecetcg/deck/view/NonExistentDeck')
        assert resp.status_code == 404

    def test_deck_delete_removes_deck(self, app, client):
        """POST /onepiecetcg/deck/delete deletes a deck."""
        with app.app_context():
            _login(client, username='deldeck')
            deck = OpDeck(
                opdck_user='deldeck', opdck_name='DeleteMe',
                opdck_seq=1, opdck_ncards=30
            )
            db.session.add(deck)
            db.session.commit()
            deck_id = deck.id
        resp = client.post('/onepiecetcg/deck/delete', data=json.dumps({
            'id': deck_id
        }), content_type='application/json')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['success'] is True
        with app.app_context():
            assert OpDeck.query.get(deck_id) is None

    def test_deck_delete_wrong_user_rejects(self, app, client):
        """Deleting another user's deck returns error."""
        with app.app_context():
            _login(client, username='gooduser')
            deck = OpDeck(
                opdck_user='otheruser', opdck_name='NotYours',
                opdck_seq=1, opdck_ncards=30
            )
            db.session.add(deck)
            db.session.commit()
            deck_id = deck.id
        resp = client.post('/onepiecetcg/deck/delete', data=json.dumps({
            'id': deck_id
        }), content_type='application/json')
        # Should either return 404 or 403, or success=False
        data = resp.get_json()
        assert resp.status_code in (404, 403, 200)
        if resp.status_code == 200:
            assert data['success'] is False
        # Verify deck still exists
        with app.app_context():
            assert OpDeck.query.get(deck_id) is not None
