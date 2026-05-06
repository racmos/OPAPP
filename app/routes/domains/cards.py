"""
Cards routes module.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from sqlalchemy import or_
from app import db
from app.models import OpSet, OpCard
from app.models.cardmarket import OpcmProductCardMap, OpcmPrice
from app.schemas.validators import validate_json
from app.schemas.cards import OpCardCreate

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
    ALLOWED_PER_PAGE = {50, 100, 250, 500, 1000}
    per_page = request.args.get('per_page', 50, type=int)
    if per_page not in ALLOWED_PER_PAGE:
        per_page = 50

    search_name = request.args.get('search_name', '')
    search_set = request.args.get('search_set', '')

    # Multi-select CSV filters (comma-separated values → OR logic)
    search_color = request.args.get('search_color', '')
    search_category = request.args.get('search_category', '')
    search_rarity = request.args.get('search_rarity', '')

    # Text search filters
    search_effect = request.args.get('search_effect', '')
    search_type = request.args.get('search_type', '')

    # Range filters
    min_cost = request.args.get('min_cost', None, type=int)
    max_cost = request.args.get('max_cost', None, type=int)
    min_power = request.args.get('min_power', None, type=int)
    max_power = request.args.get('max_power', None, type=int)
    min_counter = request.args.get('min_counter', None, type=int)
    max_counter = request.args.get('max_counter', None, type=int)

    query = OpCard.query

    if search_name:
        query = query.filter(OpCard.opcar_name.ilike(f'%{search_name}%'))
    if search_set:
        query = query.filter(OpCard.opcar_opset_id == search_set)

    # Multi-select OR logic: comma-separated values parsed per field
    if search_color:
        colors = [c.strip() for c in search_color.split(',') if c.strip()]
        if colors:
            query = query.filter(OpCard.opcar_color.in_(colors))
    if search_category:
        categories = [c.strip() for c in search_category.split(',') if c.strip()]
        if categories:
            query = query.filter(OpCard.opcar_category.in_(categories))
    if search_rarity:
        rarities = [r.strip() for r in search_rarity.split(',') if r.strip()]
        if rarities:
            query = query.filter(OpCard.opcar_rarity.in_(rarities))

    # Text search filters (ILIKE partial match)
    if search_effect:
        query = query.filter(OpCard.opcar_effect.ilike(f'%{search_effect}%'))
    if search_type:
        query = query.filter(OpCard.opcar_type.ilike(f'%{search_type}%'))

    # Range filters (min <= value <= max)
    if min_cost is not None:
        query = query.filter(OpCard.opcar_cost >= min_cost)
    if max_cost is not None:
        query = query.filter(OpCard.opcar_cost <= max_cost)
    if min_power is not None:
        query = query.filter(OpCard.opcar_power >= min_power)
    if max_power is not None:
        query = query.filter(OpCard.opcar_power <= max_power)
    if min_counter is not None:
        query = query.filter(OpCard.opcar_counter >= min_counter)
    if max_counter is not None:
        query = query.filter(OpCard.opcar_counter <= max_counter)

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

    view = request.args.get('view', 'grid')

    return render_template('cards.html',
                           cards=pagination.items,
                           pagination=pagination,
                           sets=sets,
                           colors=colors,
                           categories=categories,
                           rarities=rarities,
                           per_page=per_page,
                           view=view,
                           price_map=price_map,
                           search_color=search_color,
                           search_category=search_category,
                           search_rarity=search_rarity,
                           search_effect=search_effect,
                           search_type=search_type,
                           min_cost=min_cost,
                           max_cost=max_cost,
                           min_power=min_power,
                           max_power=max_power,
                           min_counter=min_counter,
                           max_counter=max_counter)


@cards_bp.route('/add', methods=['POST'])
@login_required
@validate_json(OpCardCreate)
def add_card():
    """Add a new card manually (JSON POST)."""
    data = request.validated_data

    # Check set exists
    opset = OpSet.query.filter_by(opset_id=data.opcar_opset_id).first()
    if not opset:
        return jsonify({'success': False, 'error': 'Set not found'}), 400

    # Check duplicate
    existing = OpCard.query.filter_by(
        opcar_opset_id=data.opcar_opset_id,
        opcar_id=data.opcar_id,
        opcar_version=data.opcar_version
    ).first()
    if existing:
        return jsonify({'success': False, 'error': 'Card already exists'}), 409

    # Create card
    card = OpCard(
        opcar_opset_id=data.opcar_opset_id,
        opcar_id=data.opcar_id,
        opcar_version=data.opcar_version,
        opcar_name=data.opcar_name,
        opcar_category=data.opcar_category,
        opcar_color=data.opcar_color,
        opcar_rarity=data.opcar_rarity,
        opcar_cost=data.opcar_cost,
        opcar_life=data.opcar_life,
        opcar_power=data.opcar_power,
        opcar_counter=data.opcar_counter,
        opcar_attribute=data.opcar_attribute,
        opcar_type=data.opcar_type,
        opcar_effect=data.opcar_effect,
        image=data.image_src,
        opcar_banned=data.opcar_banned,
        opcar_block_icon=data.opcar_block_icon,
    )
    db.session.add(card)
    db.session.commit()

    return jsonify({
        'success': True,
        'card': {
            'opcar_opset_id': card.opcar_opset_id,
            'opcar_id': card.opcar_id,
            'opcar_version': card.opcar_version,
            'opcar_name': card.opcar_name,
        }
    }), 200


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
