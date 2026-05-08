"""
Cards routes module.
"""

from urllib.parse import urlencode

from flask import Blueprint, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import exists, or_

from app import db
from app.models import OpCard, OpSet
from app.models.cardmarket import OpcmPrice, OpcmProductCardMap
from app.schemas.cards import OpCardCreate
from app.schemas.validators import validate_json

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

    # Find latest price date via subquery
    latest_date_sq = db.session.query(db.func.max(OpcmPrice.opprc_date)).scalar_subquery()

    # Single optimized query: join mappings → prices on latest date
    results = (
        db.session.query(
            OpcmProductCardMap.oppcm_opset_id,
            OpcmProductCardMap.oppcm_opcar_id,
            OpcmProductCardMap.oppcm_opcar_version,
            OpcmProductCardMap.oppcm_foil,
            OpcmPrice.opprc_low,
        )
        .join(
            OpcmPrice,
            db.and_(
                OpcmProductCardMap.oppcm_id_product == OpcmPrice.opprc_id_product,
                OpcmPrice.opprc_date == latest_date_sq,
            ),
        )
        .filter(
            db.tuple_(
                OpcmProductCardMap.oppcm_opset_id,
                OpcmProductCardMap.oppcm_opcar_id,
                OpcmProductCardMap.oppcm_opcar_version,
            ).in_(card_keys)
        )
        .all()
    )

    if not results:
        return {}

    # Build map: prefer non-foil (None/'N' over 'S'), keep lowest price
    key_to_price = {}
    for opset_id, card_id, version, foil, low in results:
        k = (opset_id, card_id, version)
        # Prefer non-foil mapping; if same foil, keep lowest price
        is_preferred = foil is None or foil == 'N'
        current = key_to_price.get(k)
        if current is None or (is_preferred and not (current[1] is None or current[1] == 'N')):
            key_to_price[k] = (low, foil)
        elif (is_preferred == (current[1] is None or current[1] == 'N')) and low is not None:
            if current[0] is None or low < current[0]:
                key_to_price[k] = (low, foil)

    price_map = {}
    for k, (low, _foil) in key_to_price.items():
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
    allowed_per_page = {50, 100, 250, 500, 1000}
    per_page = request.args.get('per_page', 50, type=int)
    if per_page not in allowed_per_page:
        per_page = 50

    search_name = request.args.get('search_name', '')
    search_set = request.args.get('search_set', '')

    # Color: changed from exact IN to ILIKE OR — matches "Red/Blue" when Red is selected
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
    min_block_icon = request.args.get('min_block_icon', None, type=int)
    max_block_icon = request.args.get('max_block_icon', None, type=int)

    # Toggle filters
    search_banned = request.args.get('search_banned', '')
    has_price = request.args.get('has_price', '')

    # Sort
    sort = request.args.get('sort', '')
    order = request.args.get('order', 'asc')

    query = OpCard.query

    if search_name:
        query = query.filter(OpCard.opcar_name.ilike(f'%{search_name}%'))
    if search_set:
        query = query.filter(OpCard.opcar_opset_id == search_set)

    # Color: OR of ILIKE for multi-color card matching ("Red/Blue" matches Red or Blue)
    if search_color:
        colors = [c.strip() for c in search_color.split(',') if c.strip()]
        if colors:
            color_filters = [OpCard.opcar_color.ilike(f'%{c}%') for c in colors]
            query = query.filter(or_(*color_filters))

    # Category and rarity: single-select exact match
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
    if min_block_icon is not None:
        query = query.filter(OpCard.opcar_block_icon >= min_block_icon)
    if max_block_icon is not None:
        query = query.filter(OpCard.opcar_block_icon <= max_block_icon)

    # Banned filter: show only banned (Y) when toggled on
    if search_banned == '1':
        query = query.filter(OpCard.opcar_banned == 'Y')

    # Has price filter: only cards that have a Cardmarket price mapping
    if has_price == '1':
        latest_pdate = db.session.query(db.func.max(OpcmPrice.opprc_date)).scalar()
        if latest_pdate:
            query = query.filter(
                exists().where(
                    OpcmProductCardMap.oppcm_opset_id == OpCard.opcar_opset_id,
                    OpcmProductCardMap.oppcm_opcar_id == OpCard.opcar_id,
                    OpcmProductCardMap.oppcm_opcar_version == OpCard.opcar_version,
                    OpcmPrice.opprc_id_product == OpcmProductCardMap.oppcm_id_product,
                    OpcmPrice.opprc_date == latest_pdate,
                )
            )

    # Dynamic sort
    sort_map = {
        'set': OpCard.opcar_opset_id,
        'card_id': OpCard.opcar_id,
        'name': OpCard.opcar_name,
        'color': OpCard.opcar_color,
        'rarity': OpCard.opcar_rarity,
        'cost': OpCard.opcar_cost,
        'power': OpCard.opcar_power,
        'counter': OpCard.opcar_counter,
        'type': OpCard.opcar_type,
        'block_icon': OpCard.opcar_block_icon,
    }

    if sort and sort in sort_map:
        sort_col = sort_map[sort]
        if order == 'desc':
            query = query.order_by(sort_col.desc(), OpCard.opcar_opset_id, OpCard.opcar_id)
        else:
            query = query.order_by(sort_col.asc(), OpCard.opcar_opset_id, OpCard.opcar_id)
    elif sort == 'price':
        latest_pdate = db.session.query(db.func.max(OpcmPrice.opprc_date)).scalar()
        if latest_pdate:
            price_subq = (
                db.session.query(
                    OpcmProductCardMap.oppcm_opset_id,
                    OpcmProductCardMap.oppcm_opcar_id,
                    OpcmProductCardMap.oppcm_opcar_version,
                    db.func.coalesce(db.func.min(OpcmPrice.opprc_low), 99999).label('min_price'),
                )
                .outerjoin(
                    OpcmPrice,
                    db.and_(
                        OpcmPrice.opprc_id_product == OpcmProductCardMap.oppcm_id_product,
                        OpcmPrice.opprc_date == latest_pdate,
                    ),
                )
                .group_by(
                    OpcmProductCardMap.oppcm_opset_id,
                    OpcmProductCardMap.oppcm_opcar_id,
                    OpcmProductCardMap.oppcm_opcar_version,
                )
                .subquery()
            )
            query = query.outerjoin(
                price_subq,
                db.and_(
                    price_subq.c.oppcm_opset_id == OpCard.opcar_opset_id,
                    price_subq.c.oppcm_opcar_id == OpCard.opcar_id,
                    price_subq.c.oppcm_opcar_version == OpCard.opcar_version,
                ),
            )
            if order == 'desc':
                query = query.order_by(price_subq.c.min_price.desc(), OpCard.opcar_opset_id, OpCard.opcar_id)
            else:
                query = query.order_by(price_subq.c.min_price.asc(), OpCard.opcar_opset_id, OpCard.opcar_id)
        else:
            query = query.order_by(OpCard.opcar_opset_id, OpCard.opcar_id, OpCard.opcar_version)
    else:
        query = query.order_by(OpCard.opcar_opset_id, OpCard.opcar_id, OpCard.opcar_version)

    pagination = query.paginate(page=page, per_page=per_page, error_out=False)

    sets = OpSet.query.order_by(OpSet.opset_id).all()

    # Collect unique colors, categories, and rarities for filter dropdowns/buttons
    def distinct_values(column):
        rows = db.session.query(column).filter(column.isnot(None)).distinct().all()
        return sorted([r[0] for r in rows if r[0]])

    colors = distinct_values(OpCard.opcar_color)
    categories = distinct_values(OpCard.opcar_category)
    rarities = distinct_values(OpCard.opcar_rarity)

    # Build price map for the cards on this page
    price_map = _build_price_map(pagination.items)

    view = request.args.get('view', 'grid')

    # Build query string without page param for pagination links
    query_parts = [(k, v) for k, v in request.args.items(multi=True) if k != 'page']
    query_string_no_page = urlencode(query_parts)

    return render_template(
        'cards.html',
        cards=pagination.items,
        pagination=pagination,
        sets=sets,
        colors=colors,
        categories=categories,
        rarities=rarities,
        per_page=per_page,
        view=view,
        price_map=price_map,
        query_string_no_page=query_string_no_page,
        search_name=search_name,
        search_set=search_set,
        search_color=search_color,
        search_category=search_category,
        search_rarity=search_rarity,
        search_effect=search_effect,
        search_type=search_type,
        search_banned=search_banned,
        has_price=has_price,
        sort=sort,
        order=order,
        min_cost=min_cost,
        max_cost=max_cost,
        min_power=min_power,
        max_power=max_power,
        min_counter=min_counter,
        max_counter=max_counter,
        min_block_icon=min_block_icon,
        max_block_icon=max_block_icon,
    )


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
        opcar_opset_id=data.opcar_opset_id, opcar_id=data.opcar_id, opcar_version=data.opcar_version
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

    return jsonify(
        {
            'success': True,
            'card': {
                'opcar_opset_id': card.opcar_opset_id,
                'opcar_id': card.opcar_id,
                'opcar_version': card.opcar_version,
                'opcar_name': card.opcar_name,
            },
        }
    ), 200


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
    results = (
        OpCard.query.filter(or_(OpCard.opcar_name.ilike(like), OpCard.opcar_id.ilike(like)))
        .order_by(OpCard.opcar_opset_id, OpCard.opcar_id, OpCard.opcar_version)
        .limit(limit)
        .all()
    )

    return jsonify(
        {
            'success': True,
            'cards': [
                {
                    'set_id': c.opcar_opset_id,
                    'card_id': c.opcar_id,
                    'card_version': c.opcar_version,
                    'name': c.opcar_name,
                    'rarity': c.opcar_rarity,
                    'color': c.opcar_color,
                    'category': c.opcar_category,
                    'image': c.image_src,
                }
                for c in results
            ],
        }
    )
