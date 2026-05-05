"""
Cards routes module.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import or_
from app import db
from app.models import OpSet, OpCard
from app.models.cardmarket import OpcmProductCardMap, OpcmPrice

cards_bp = Blueprint('cards', __name__, url_prefix='/onepiecetcg/cards')


def _build_price_map(card_items):
    """Build a dict mapping (opset_id, card_id, version) → price info
    for all cards on the current page.

    Returns: {(opset_id, card_id, version): '€1.23'} or empty dict if no data.
    """
    if not card_items:
        return {}

    # Collect card identifiers from this page
    card_keys = [(c.opcar_opset_id, c.opcar_id, c.opcar_version) for c in card_items]

    # Find mappings to Cardmarket products for these cards
    mappings = OpcmProductCardMap.query.filter(
        db.tuple_(OpcmProductCardMap.oppcm_opset_id,
                  OpcmProductCardMap.oppcm_opcar_id,
                  OpcmProductCardMap.oppcm_opcar_version).in_(card_keys)
    ).all()

    if not mappings:
        return {}

    # Get product IDs, prioritizing non-foil (outer join: prefer N or NULL over S)
    product_ids = list({m.oppcm_id_product for m in mappings})

    # Find latest price date
    latest_date = db.session.query(db.func.max(OpcmPrice.opprc_date)).scalar()
    if not latest_date:
        return {}

    # Get prices for these products on the latest date
    prices = OpcmPrice.query.filter(
        OpcmPrice.opprc_date == latest_date,
        OpcmPrice.opprc_id_product.in_(product_ids)
    ).all()

    product_price = {}
    for p in prices:
        # Prefer non-foil price; foil stored in same product sometimes
        if p.opprc_id_product not in product_price:
            product_price[p.opprc_id_product] = p.opprc_low
        # Always keep the lowest price if multiple rows
        elif product_price[p.opprc_id_product] is not None and p.opprc_low is not None:
            if p.opprc_low < product_price[p.opprc_id_product]:
                product_price[p.opprc_id_product] = p.opprc_low

    # Build mapping key → price
    key_to_product = {}
    for m in mappings:
        k = (m.oppcm_opset_id, m.oppcm_opcar_id, m.oppcm_opcar_version)
        if k not in key_to_product or m.oppcm_foil is None or m.oppcm_foil == 'N':
            # Prefer non-foil mapping
            key_to_product[k] = m.oppcm_id_product

    price_map = {}
    for k, pid in key_to_product.items():
        low = product_price.get(pid)
        if low is not None:
            try:
                price_map[k] = f'€{float(low):.2f}'
            except (ValueError, TypeError):
                price_map[k] = f'€{low}'

    return price_map


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

    # Build price map for the cards on this page
    price_map = _build_price_map(pagination.items)

    return render_template('cards.html',
                           cards=pagination.items,
                           pagination=pagination,
                           sets=sets,
                           colors=colors,
                           categories=categories,
                           rarities=rarities,
                           per_page=per_page,
                           price_map=price_map)


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
