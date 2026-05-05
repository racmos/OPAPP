"""
Collection routes module with Pydantic validation.
"""
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models import OpCollection, OpCard, OpSet
from app.schemas.validators import CollectionAdd, validate_json

collection_bp = Blueprint('collection', __name__, url_prefix='/onepiecetcg/collection')


def _qty_int(raw) -> int:
    """Convert quantity (stored as TEXT) to int safely."""
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _null_safe_eq(col, val):
    """NULL-safe equality for SQLAlchemy filters."""
    if val is None:
        return col.is_(None)
    return col == val


def _find_exact_duplicate(user, rbset_id, rbcar_id, rbcar_version, foil, selling, sell_price, condition, language):
    """Find exact duplicate row in collection (8-field NULL-safe match)."""
    return OpCollection.query.filter(
        OpCollection.opcol_user == user,
        OpCollection.opcol_opset_id == rbset_id,
        OpCollection.opcol_opcar_id == rbcar_id,
        OpCollection.opcol_opcar_version == rbcar_version,
        OpCollection.opcol_foil == foil,
        OpCollection.opcol_selling == selling,
        _null_safe_eq(OpCollection.opcol_sell_price, sell_price),
        _null_safe_eq(OpCollection.opcol_condition, condition),
        _null_safe_eq(OpCollection.opcol_language, language),
    ).first()


@collection_bp.route('')
@login_required
def collection():
    """List user's collection with filters and pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    search_set = request.args.get('search_set', '')
    search_card_id = request.args.get('search_card_id', '')
    search_card_name = request.args.get('search_card_name', '')
    search_category = request.args.get('search_category', '')
    search_color = request.args.get('search_color', '')
    search_rarity = request.args.get('search_rarity', '')

    query = db.session.query(OpCollection, OpCard).join(
        OpCard,
        (OpCollection.opcol_opset_id == OpCard.opcar_opset_id) &
        (OpCollection.opcol_opcar_id == OpCard.opcar_id) &
        (OpCollection.opcol_opcar_version == OpCard.opcar_version)
    ).filter(OpCollection.opcol_user == current_user.username)

    if search_set:
        query = query.filter(OpCollection.opcol_opset_id == search_set)
    if search_card_id:
        query = query.filter(OpCollection.opcol_opcar_id.ilike(f'%{search_card_id}%'))
    if search_card_name:
        query = query.filter(OpCard.opcar_name.ilike(f'%{search_card_name}%'))
    if search_category:
        query = query.filter(OpCard.opcar_category.ilike(f'%{search_category}%'))
    if search_color:
        query = query.filter(OpCard.opcar_color.ilike(f'%{search_color}%'))
    if search_rarity:
        query = query.filter(OpCard.opcar_rarity.ilike(f'%{search_rarity}%'))

    query = query.order_by(
        OpCollection.opcol_opset_id,
        OpCollection.opcol_opcar_id,
        OpCollection.opcol_opcar_version,
    )
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    collections_data = [
        {'collection': col, 'card': card}
        for col, card in pagination.items
    ]

    sets = OpSet.query.order_by(OpSet.opset_id).all()
    colors = sorted(set(
        c.opcar_color for c in db.session.query(OpCard.opcar_color)
        .filter(OpCard.opcar_color.isnot(None)).distinct().all()
        if c.opcar_color
    ))

    return render_template('collection.html',
                           collections_data=collections_data,
                           pagination=pagination,
                           sets=sets,
                           colors=colors,
                           per_page=per_page)


@collection_bp.route('/add', methods=['POST'])
@login_required
@validate_json(CollectionAdd)
def add_collection():
    """Add card to collection. Merges if exact duplicate exists."""
    data = request.validated_data

    card = OpCard.query.filter_by(
        opcar_opset_id=data.opcol_opset_id,
        opcar_id=data.opcol_opcar_id,
        opcar_version=data.opcol_opcar_version,
    ).first()
    if not card:
        return jsonify({'success': False, 'message': 'Card does not exist'}), 400

    selling = data.opcol_selling or 'N'

    # Check for exact duplicate
    existing = _find_exact_duplicate(
        user=current_user.username,
        rbset_id=data.opcol_opset_id,
        rbcar_id=data.opcol_opcar_id,
        rbcar_version=data.opcol_opcar_version,
        foil=data.opcol_foil,
        selling=selling,
        sell_price=data.opcol_sell_price,
        condition=data.opcol_condition,
        language=data.opcol_language,
    )

    if existing:
        existing.opcol_quantity = str(_qty_int(existing.opcol_quantity) + data.opcol_quantity)
        existing.opcol_chadat = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True, 'opcol_id': existing.opcol_id, 'merged': True})

    new_row = OpCollection(
        opcol_opset_id=data.opcol_opset_id,
        opcol_opcar_id=data.opcol_opcar_id,
        opcol_opcar_version=data.opcol_opcar_version,
        opcol_foil=data.opcol_foil,
        opcol_quantity=str(data.opcol_quantity),
        opcol_selling=selling,
        opcol_sell_price=data.opcol_sell_price,
        opcol_condition=data.opcol_condition,
        opcol_language=data.opcol_language,
        opcol_chadat=datetime.utcnow(),
        opcol_user=current_user.username,
    )
    db.session.add(new_row)
    db.session.commit()
    return jsonify({'success': True, 'opcol_id': new_row.opcol_id, 'merged': False})


@collection_bp.route('/update', methods=['POST'])
@login_required
def update_collection():
    """Update quantity/details of a collection entry."""
    data = request.get_json() or {}

    opcol_id = data.get('opcol_id')
    if not opcol_id:
        return jsonify({'success': False, 'message': 'opcol_id required'}), 400

    col = OpCollection.query.filter_by(
        opcol_id=opcol_id, opcol_user=current_user.username
    ).first_or_404()

    if 'opcol_quantity' in data:
        qty = data['opcol_quantity']
        if qty == 0 or qty == '0':
            db.session.delete(col)
            db.session.commit()
            return jsonify({'success': True, 'deleted': True})
        col.opcol_quantity = str(qty)

    if 'opcol_selling' in data:
        col.opcol_selling = data['opcol_selling']
    if 'opcol_sell_price' in data:
        col.opcol_sell_price = data['opcol_sell_price']
    if 'opcol_condition' in data:
        col.opcol_condition = data['opcol_condition']
    if 'opcol_language' in data:
        col.opcol_language = data['opcol_language']

    col.opcol_chadat = datetime.utcnow()
    db.session.commit()
    return jsonify({'success': True})


@collection_bp.route('/remove', methods=['POST'])
@login_required
def remove_collection():
    """Remove a card from the collection."""
    data = request.get_json() or {}

    opcol_id = data.get('opcol_id')
    if not opcol_id:
        return jsonify({'success': False, 'message': 'opcol_id required'}), 400

    col = OpCollection.query.filter_by(
        opcol_id=opcol_id, opcol_user=current_user.username
    ).first_or_404()

    db.session.delete(col)
    db.session.commit()
    return jsonify({'success': True})
