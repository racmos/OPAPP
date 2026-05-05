"""
Cards routes module.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import or_
from app import db
from app.models import OpSet, OpCard

cards_bp = Blueprint('cards', __name__, url_prefix='/onepiecetcg/cards')


@cards_bp.route('')
@login_required
def cards():
    """List all cards with filters and pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)

    search_name = request.args.get('search_name', '')
    search_set = request.args.get('search_set', '')
    search_color = request.args.get('search_color', '')
    search_category = request.args.get('search_category', '')
    search_rarity = request.args.get('search_rarity', '')

    query = OpCard.query

    if search_name:
        query = query.filter(OpCard.opcar_name.ilike(f'%{search_name}%'))
    if search_set:
        query = query.filter(OpCard.opcar_opset_id == search_set)
    if search_color:
        query = query.filter(OpCard.opcar_color.ilike(f'%{search_color}%'))
    if search_category:
        query = query.filter(OpCard.opcar_category.ilike(f'%{search_category}%'))
    if search_rarity:
        query = query.filter(OpCard.opcar_rarity.ilike(f'%{search_rarity}%'))

    query = query.order_by(OpCard.opcar_opset_id, OpCard.opcar_id, OpCard.opcar_version)
    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    sets = OpSet.query.order_by(OpSet.opset_id).all()

    # Collect unique colors, categories, and rarities for filter dropdowns
    def distinct_values(column):
        rows = db.session.query(column).filter(column.isnot(None)).distinct().all()
        return sorted([r[0] for r in rows if r[0]])

    colors = distinct_values(OpCard.opcar_color)
    categories = distinct_values(OpCard.opcar_category)
    rarities = distinct_values(OpCard.opcar_rarity)

    return render_template('cards.html',
                           cards=pagination.items,
                           pagination=pagination,
                           sets=sets,
                           colors=colors,
                           categories=categories,
                           rarities=rarities,
                           per_page=per_page)


@cards_bp.route('/search')
@login_required
def search_cards():
    """Search API: returns JSON results for autocomplete/ajax calls."""
    q = request.args.get('q', '').strip()
    limit = request.args.get('limit', 20, type=int)
    limit = min(max(limit, 1), 100)

    if not q:
        return jsonify({'success': True, 'cards': []})

    like = f'%{q}%'
    results = OpCard.query.filter(
        or_(
            OpCard.opcar_name.ilike(like),
            OpCard.opcar_id.ilike(like)
        )
    ).order_by(OpCard.opcar_opset_id, OpCard.opcar_id, OpCard.opcar_version).limit(limit).all()

    return jsonify({
        'success': True,
        'cards': [{
            'set_id': c.opcar_opset_id,
            'card_id': c.opcar_id,
            'card_version': c.opcar_version,
            'name': c.opcar_name,
            'rarity': c.opcar_rarity,
            'color': c.opcar_color,
            'category': c.opcar_category,
            'image': c.image_src,
        } for c in results],
    })
