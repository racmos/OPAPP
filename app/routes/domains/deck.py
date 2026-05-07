"""
Deck routes module.
"""

from datetime import datetime

from flask import Blueprint, abort, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.models import OpCard, OpDeck
from app.schemas.validators import DeckCardAction, DeckSave, validate_json

deck_bp = Blueprint('deck', __name__, url_prefix='/onepiecetcg/deck')


@deck_bp.route('')
@login_required
def deck():
    """List user's decks with optional filters."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    filter_name = (request.args.get('filter_name') or '').strip()
    filter_format = (request.args.get('filter_format') or '').strip()
    filter_mode = (request.args.get('filter_mode') or '').strip()

    query = OpDeck.query.filter(OpDeck.opdck_user == current_user.username)

    if filter_name:
        query = query.filter(OpDeck.opdck_name.ilike(f'%{filter_name}%'))
    if filter_format:
        query = query.filter(OpDeck.opdck_format == filter_format)
    if filter_mode:
        query = query.filter(OpDeck.opdck_mode == filter_mode)

    # Group by name, get latest seq
    query = query.order_by(OpDeck.opdck_name, OpDeck.opdck_seq.desc())

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    formats = ['Standard', 'Limited']
    modes = ['1v1', '2v2']

    return render_template('deck.html', decks=pagination.items, pagination=pagination, formats=formats, modes=modes)


@deck_bp.route('/view/<name>')
@login_required
def view_deck(name):
    """View deck detail by name (latest version)."""
    deck_obj = (
        OpDeck.query.filter(OpDeck.opdck_name == name, OpDeck.opdck_user == current_user.username)
        .order_by(OpDeck.opdck_seq.desc())
        .first()
    )

    if not deck_obj:
        abort(404)

    return render_template('deck_view.html', deck=deck_obj)


@deck_bp.route('/save', methods=['POST'])
@login_required
@validate_json(DeckSave)
def save_deck():
    """Save new deck or create new version."""
    data = request.validated_data

    # Build cards JSON from validated data
    total_cards = 0
    cards_json = None
    if data.opdck_cards:
        main_cards = data.opdck_cards.get('main', []) or []
        sideboard = data.opdck_cards.get('sideboard', []) or []
        for card in main_cards + sideboard:
            total_cards += card.get('qty', 0)
        cards_json = {
            'main': [{'set': c.get('set'), 'id': c.get('id'), 'qty': c.get('qty')} for c in main_cards],
            'sideboard': [{'set': c.get('set'), 'id': c.get('id'), 'qty': c.get('qty')} for c in sideboard],
        }

    next_seq = OpDeck.get_next_seq(current_user.username, data.opdck_name)

    new_deck = OpDeck(
        opdck_user=current_user.username,
        opdck_name=data.opdck_name,
        opdck_seq=next_seq,
        opdck_snapshot=datetime.utcnow(),
        opdck_description=data.opdck_description,
        opdck_mode=data.opdck_mode or '1v1',
        opdck_format=data.opdck_format or 'Standard',
        opdck_max_set=data.opdck_max_set,
        opdck_ncards=total_cards or 0,
        opdck_cards=cards_json,
    )

    db.session.add(new_deck)
    db.session.commit()

    return jsonify(
        {
            'success': True,
            'id': new_deck.id,
            'name': new_deck.opdck_name,
            'seq': new_deck.opdck_seq,
        }
    )


@deck_bp.route('/delete', methods=['POST'])
@login_required
def delete_deck():
    """Delete a deck by ID (only owner)."""
    data = request.get_json() or {}

    deck_id = data.get('id')
    if not deck_id:
        return jsonify({'success': False, 'message': 'id required'}), 400

    deck_obj = OpDeck.query.filter_by(id=deck_id, opdck_user=current_user.username).first()

    if not deck_obj:
        return jsonify({'success': False, 'message': 'Deck not found or not yours'}), 404

    db.session.delete(deck_obj)
    db.session.commit()

    return jsonify({'success': True})


@deck_bp.route('/<int:deck_id>/cards/add', methods=['POST'])
@login_required
@validate_json(DeckCardAction)
def add_deck_card(deck_id: int):
    """Add cards to a deck section."""
    data = request.validated_data

    deck_obj = OpDeck.query.get_or_404(deck_id)
    if deck_obj.opdck_user != current_user.username:
        abort(404)

    # Verify card exists
    card = OpCard.query.filter_by(opcar_opset_id=data.set_id, opcar_id=data.card_id, opcar_version='p0').first()
    if not card:
        return jsonify({'success': False, 'message': 'Card does not exist'}), 400

    try:
        deck_obj.add_card(data.section, data.set_id, data.card_id, data.quantity)
    except ValueError as e:
        deck_bp.logger.warning("Invalid add_card request for deck_id=%s by user=%s: %s", deck_id, current_user.username, str(e))
        return jsonify({'success': False, 'message': 'Invalid card operation'}), 400

    db.session.commit()
    return jsonify({'success': True})


@deck_bp.route('/<int:deck_id>/cards/remove', methods=['POST'])
@login_required
@validate_json(DeckCardAction)
def remove_deck_card(deck_id: int):
    """Remove cards from a deck section."""
    data = request.validated_data

    deck_obj = OpDeck.query.get_or_404(deck_id)
    if deck_obj.opdck_user != current_user.username:
        abort(404)

    try:
        deck_obj.remove_card(data.section, data.set_id, data.card_id, data.quantity)
    except ValueError as e:
        current_app.logger.warning("Deck card removal validation failed", exc_info=True)
        return jsonify({'success': False, 'message': 'Invalid card removal request'}), 400

    db.session.commit()
    return jsonify({'success': True})
