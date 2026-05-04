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
               cost=1, image='OP01-001.png'):
    """Seed a test card into the database."""
    c = OpCard(
        opcar_opset_id=set_id,
        opcar_id=card_id,
        opcar_name=name,
        opcar_category=category,
        opcar_color=color,
        opcar_rarity=rarity,
        opcar_cost=cost,
        image=image
    )
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
            for i in range(5):
                _seed_card(app, 'OP01', f'OP01-{i+1:03d}',
                           f'Card {i+1}', 'Character', 'Red', 'Common')
        # Request with per_page=2
        resp = client.get('/onepiecetcg/cards?per_page=2&page=1')
        assert resp.status_code == 200
        html = resp.data.decode('utf-8')
        # Should show pagination navigation
        assert 'page' in html.lower() or 'prev' in html.lower() or 'next' in html.lower()


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
                opcol_opcar_id='OP01-001'
            ).first()
            assert col is not None
            assert col.opcol_quantity == '4'

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
