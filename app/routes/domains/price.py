"""
Price routes for One Piece TCG.
Scraper, Cardmarket loader, matcher, ignored products, expansion mapping.
"""

import json
import logging

from flask import Blueprint, Response, jsonify, render_template, request
from flask_login import login_required
from sqlalchemy import func

from app import db
from app.models import OpCard, OpSet
from app.models.cardmarket import (
    OpcmExpansion,
    OpcmIgnored,
    OpcmPrice,
    OpcmProduct,
    OpcmProductCardMap,
)
from app.schemas.validators import (
    AutoMatchApply,
    IgnoredAdd,
    IgnoredRestore,
    OpExtract,
    validate_json,
)

logger = logging.getLogger(__name__)

price_bp = Blueprint('price', __name__, url_prefix='/onepiecetcg/price')


@price_bp.route('')
@login_required
def price():
    """Price generation page."""
    return render_template('price.html', sets=OpSet.query.all())


# =========================================================================
# ONE PIECE SCRAPER
# =========================================================================


@price_bp.route('/refresh-op-sets', methods=['POST'])
@login_required
def refresh_op_sets():
    """Fetch available sets from One Piece cardlist."""
    from app.services.onepiece_scraper import refresh_op_sets as _refresh

    try:
        result = _refresh()
        return jsonify(result)
    except Exception:
        logger.exception('refresh-op-sets failed')
        return jsonify({'success': False, 'message': 'Internal server error', 'sets': []}), 500


@price_bp.route('/extract-op-cards', methods=['POST'])
@login_required
@validate_json(OpExtract)
def extract_op_cards():
    """Scrape One Piece cardlist, extract cards + images, insert to DB."""
    from app.services.onepiece_scraper import extract_op_cards as _extract

    data = request.validated_data
    filter_sets = None
    if data.sets:
        filter_sets = [{'id': s.id, 'code': s.code, 'name': s.name} for s in data.sets]
    try:
        result = _extract(filter_sets=filter_sets)
        return jsonify(result)
    except Exception:
        logger.exception('extract-op-cards failed')
        return jsonify({'success': False, 'steps': [], 'stats': {}, 'errors': ['Internal server error']}), 500


# =========================================================================
# CARDMARKET LOADER
# =========================================================================


@price_bp.route('/cardmarket-load', methods=['POST'])
@login_required
def cardmarket_load():
    """Load Cardmarket data tables (price guide + products)."""
    from app.services.cardmarket_loader import CARDMARKET_URLS, CardmarketLoader

    try:
        # Security: do not allow request payload to override outbound URLs.
        # Always use server-side allowlisted Cardmarket endpoints.
        urls = dict(CARDMARKET_URLS)

        loader = CardmarketLoader()
        result = loader.run(urls=urls)
        return jsonify(result)
    except Exception:
        logger.exception('cardmarket-load failed')
        return jsonify({'success': False, 'steps': [], 'errors': ['Internal server error']}), 500


@price_bp.route('/cardmarket-load-sse', methods=['GET'])
@login_required
def cardmarket_load_sse():
    """Load Cardmarket data with Server-Sent Events progress."""
    from queue import Empty, Queue
    from threading import Thread

    from flask import current_app

    from app.services.cardmarket_loader import CARDMARKET_URLS, CardmarketLoader

    data = request.args.to_dict()
    urls = dict(CARDMARKET_URLS)
    if data.get('singles_url'):
        urls['singles'] = data['singles_url']
    if data.get('nonsingles_url'):
        urls['nonsingles'] = data['nonsingles_url']
    if data.get('price_guide_url'):
        urls['price_guide'] = data['price_guide_url']

    q = Queue()
    app = current_app._get_current_object()

    def _run_loader():
        with app.app_context():
            try:

                def on_step(step):
                    q.put(('step', step))

                loader = CardmarketLoader(progress_callback=on_step)
                result = loader.run(urls=urls)
                q.put(('complete', result))
            except Exception:
                logger.exception('cardmarket-load-sse failed')
                q.put(('error', {'message': 'Internal server error'}))

    def event_stream():
        thread = Thread(target=_run_loader)
        thread.start()
        while True:
            try:
                evt_type, evt_data = q.get(timeout=1)
            except Empty:
                if not thread.is_alive():
                    break
                continue
            yield f'event: {evt_type}\ndata: {json.dumps(evt_data)}\n\n'
            if evt_type in ('complete', 'error'):
                break
        thread.join()

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={'X-Accel-Buffering': 'no'},
    )


@price_bp.route('/extract-op-cards-sse', methods=['GET'])
@login_required
def extract_op_cards_sse():
    """Scrape One Piece cards with Server-Sent Events progress."""
    from app.services.onepiece_scraper import extract_op_cards as _extract

    # Capture request args before entering generator context
    sets_param = request.args.get('sets')
    filter_sets = json.loads(sets_param) if sets_param else None

    def event_stream():
        try:
            result = _extract(filter_sets=filter_sets)
            for step in result.get('steps', []):
                yield f'event: step\ndata: {json.dumps(step)}\n\n'
            yield f'event: complete\ndata: {json.dumps(result)}\n\n'
        except Exception:
            logger.exception('extract-op-cards-sse failed')
            yield f'event: error\ndata: {json.dumps({"message": "Internal server error"})}\n\n'

    return Response(
        event_stream(),
        mimetype='text/event-stream',
        headers={'X-Accel-Buffering': 'no'},
    )


# =========================================================================
# CARDMARKET PRODUCTS — UNMATCHED / SEARCH
# =========================================================================


@price_bp.route('/cardmarket-unmatched')
@login_required
def cardmarket_unmatched():
    """Get products not yet mapped to internal cards with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)

    latest_date = db.session.query(func.max(OpcmProduct.opprd_date)).scalar()
    if not latest_date:
        return jsonify({'success': True, 'unmatched': [], 'count': 0, 'pages': 0, 'page': 1})

    mapped_ids = db.session.query(OpcmProductCardMap.oppcm_id_product).subquery()

    ignored_pairs = set((r.opig_id_product, r.opig_name) for r in OpcmIgnored.query.all())

    # Paginated query for unmatched products
    pagination = (
        OpcmProduct.query.filter(
            OpcmProduct.opprd_date == latest_date, ~OpcmProduct.opprd_id_product.in_(db.session.query(mapped_ids))
        )
        .order_by(OpcmProduct.opprd_name, OpcmProduct.opprd_id_product)
        .paginate(page=page, per_page=per_page, error_out=False)
    )

    unmatched = [p for p in pagination.items if (p.opprd_id_product, p.opprd_name) not in ignored_pairs]

    latest_price_date = db.session.query(func.max(OpcmPrice.opprc_date)).scalar()

    price_map = {}
    if latest_price_date:
        prices = OpcmPrice.query.filter_by(opprc_date=latest_price_date).all()
        price_map = {p.opprc_id_product: float(p.opprc_low) if p.opprc_low is not None else None for p in prices}

    return jsonify(
        {
            'success': True,
            'count': len(unmatched),
            'pages': pagination.pages,
            'page': page,
            'unmatched': [
                {
                    'id_product': p.opprd_id_product,
                    'name': p.opprd_name,
                    'type': p.opprd_type,
                    'category': p.opprd_category_name,
                    'low_price': price_map.get(p.opprd_id_product),
                }
                for p in unmatched
            ],
        }
    )


@price_bp.route('/cardmarket-search-cards')
@login_required
def cardmarket_search_cards():
    """Search internal cards by name for manual mapping."""
    q = request.args.get('q', '').strip()
    if len(q) < 3:
        return jsonify({'success': True, 'cards': []})

    cards = OpCard.query.filter(OpCard.opcar_name.ilike(f'%{q}%')).order_by(OpCard.opcar_name).limit(20).all()

    return jsonify(
        {
            'success': True,
            'cards': [
                {
                    'rbset_id': c.opcar_opset_id,
                    'rbcar_id': c.opcar_id,
                    'rbcar_version': c.opcar_version,
                    'name': c.opcar_name,
                }
                for c in cards
            ],
        }
    )


# =========================================================================
# CARDMARKET MAPPING — map / unmap
# =========================================================================


@price_bp.route('/cardmarket-map', methods=['POST'])
@login_required
def cardmarket_map():
    """Save a manual product-to-card mapping."""
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    id_product = data.get('id_product')
    rbset_id = data.get('rbset_id')
    rbcar_id = data.get('rbcar_id')
    rbcar_version = (data.get('rbcar_version') or 'p0').strip()
    foil = data.get('rbpcm_foil') or data.get('foil')
    if foil not in (None, 'N', 'S', ''):
        return jsonify({'success': False, 'message': "foil must be 'N', 'S' or empty"}), 400
    if foil == '':
        foil = None

    if not all([id_product, rbset_id, rbcar_id, rbcar_version]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    card = OpCard.query.filter_by(
        opcar_opset_id=rbset_id,
        opcar_id=rbcar_id,
        opcar_version=rbcar_version,
    ).first()
    if not card:
        return jsonify({'success': False, 'message': 'Card does not exist'}), 400

    # Check for conflict: (rbset_id, rbcar_id, foil) already mapped to another product
    conflict_query = OpcmProductCardMap.query.filter(
        OpcmProductCardMap.oppcm_opset_id == rbset_id,
        OpcmProductCardMap.oppcm_opcar_id == rbcar_id,
        OpcmProductCardMap.oppcm_opcar_version == rbcar_version,
        OpcmProductCardMap.oppcm_id_product != id_product,
    )
    if foil is None:
        conflict_query = conflict_query.filter(OpcmProductCardMap.oppcm_foil.is_(None))
    else:
        conflict_query = conflict_query.filter(OpcmProductCardMap.oppcm_foil == foil)
    conflict = conflict_query.first()

    if conflict:
        return jsonify(
            {
                'success': False,
                'message': (
                    f'Card {rbset_id}-{rbcar_id}-{rbcar_version} already mapped to idProduct '
                    f'{conflict.oppcm_id_product}.'
                ),
                'conflict_id_product': conflict.oppcm_id_product,
            }
        ), 409

    existing = OpcmProductCardMap.query.filter_by(oppcm_id_product=id_product).first()

    if existing:
        existing.oppcm_opset_id = rbset_id
        existing.oppcm_opcar_id = rbcar_id
        existing.oppcm_opcar_version = rbcar_version
        existing.oppcm_foil = foil
        existing.oppcm_match_type = 'manual'
        existing.oppcm_confidence = 1.0
    else:
        db.session.add(
            OpcmProductCardMap(
                oppcm_id_product=id_product,
                oppcm_opset_id=rbset_id,
                oppcm_opcar_id=rbcar_id,
                oppcm_opcar_version=rbcar_version,
                oppcm_foil=foil,
                oppcm_match_type='manual',
                oppcm_confidence=1.0,
            )
        )

    db.session.commit()
    return jsonify({'success': True, 'message': 'Mapping saved'})


@price_bp.route('/cardmarket-unmap', methods=['POST'])
@login_required
def cardmarket_unmap():
    """Remove a mapping by id_product or (rbset_id + rbcar_id [+ foil])."""
    data = request.get_json() or {}
    id_product = data.get('id_product')
    rbset_id = (data.get('rbset_id') or '').strip()
    rbcar_id = (data.get('rbcar_id') or '').strip()
    rbcar_version = (data.get('rbcar_version') or '').strip()
    foil = data.get('foil') or data.get('rbpcm_foil')

    if id_product:
        try:
            id_product = int(id_product)
        except (TypeError, ValueError):
            return jsonify({'success': False, 'message': 'Invalid id_product'}), 400
        deleted = OpcmProductCardMap.query.filter_by(oppcm_id_product=id_product).delete()
    elif rbset_id and rbcar_id:
        q = OpcmProductCardMap.query.filter_by(
            oppcm_opset_id=rbset_id,
            oppcm_opcar_id=rbcar_id,
        )
        if rbcar_version:
            q = q.filter(OpcmProductCardMap.oppcm_opcar_version == rbcar_version)
        if foil in ('N', 'S'):
            q = q.filter(OpcmProductCardMap.oppcm_foil == foil)
        deleted = q.delete()
    else:
        return jsonify({'success': False, 'message': 'Need id_product or (rbset_id + rbcar_id)'}), 400

    db.session.commit()
    return jsonify({'success': True, 'deleted': deleted})


# =========================================================================
# CARDMARKET MAPPINGS BROWSER
# =========================================================================


@price_bp.route('/cardmarket-mappings')
@login_required
def cardmarket_mappings():
    """Unified list of mapped + unmapped from latest snapshot."""
    q_product = (request.args.get('q_product') or '').strip()
    q_card = (request.args.get('q_card') or '').strip()
    q_set = (request.args.get('q_set') or '').strip()
    only = request.args.get('only', 'all')
    include_nonsingles = request.args.get('include_nonsingles', '0') == '1'

    latest_date = db.session.query(func.max(OpcmProduct.opprd_date)).scalar()
    if not latest_date:
        return jsonify({'success': True, 'rows': [], 'count': 0, 'message': 'No data loaded'})

    latest_price_per_prod = dict(
        db.session.query(
            OpcmPrice.opprc_id_product,
            func.max(OpcmPrice.opprc_date),
        )
        .group_by(OpcmPrice.opprc_id_product)
        .all()
    )
    low_lookup = {}
    if latest_price_per_prod:
        for p in OpcmPrice.query.all():
            if latest_price_per_prod.get(p.opprc_id_product) == p.opprc_date:
                low_lookup[p.opprc_id_product] = float(p.opprc_low) if p.opprc_low is not None else None

    products_q = OpcmProduct.query.filter(OpcmProduct.opprd_date == latest_date)
    if not include_nonsingles:
        products_q = products_q.filter(OpcmProduct.opprd_type == 'single')
    if q_product:
        like = f'%{q_product}%'
        products_q = products_q.filter(
            (OpcmProduct.opprd_name.ilike(like)) | (db.cast(OpcmProduct.opprd_id_product, db.Text).ilike(like))
        )
    products = products_q.all()

    mappings = {m.oppcm_id_product: m for m in OpcmProductCardMap.query.all()}
    cards_idx = {(c.opcar_opset_id, c.opcar_id, c.opcar_version): c for c in OpCard.query.all()}

    q_card_l = q_card.lower() if q_card else ''
    q_set_l = q_set.lower() if q_set else ''

    rows = []
    for p in products:
        m = mappings.get(p.opprd_id_product)
        is_mapped = m is not None

        if only == 'mapped' and not is_mapped:
            continue
        if only == 'unmapped' and is_mapped:
            continue

        rbset_id = m.oppcm_opset_id if m else None
        rbcar_id = m.oppcm_opcar_id if m else None
        rbcar_version = m.oppcm_opcar_version if m else None
        foil_val = m.oppcm_foil if m else None
        match_type = m.oppcm_match_type if m else None
        card = cards_idx.get((rbset_id, rbcar_id, rbcar_version)) if rbset_id and rbcar_id and rbcar_version else None
        card_name = card.opcar_name if card else None

        if is_mapped and q_card_l:
            in_card = (rbcar_id or '').lower().find(q_card_l) >= 0 or (card_name or '').lower().find(q_card_l) >= 0
            if not in_card:
                continue
        if is_mapped and q_set_l:
            if (rbset_id or '').lower().find(q_set_l) < 0:
                continue

        rows.append(
            {
                'id_product': p.opprd_id_product,
                'product_name': p.opprd_name,
                'product_type': p.opprd_type,
                'low_price': low_lookup.get(p.opprd_id_product),
                'rbset_id': rbset_id,
                'rbcar_id': rbcar_id,
                'rbcar_version': rbcar_version,
                'rbcar_name': card_name,
                'rbpcm_foil': foil_val,
                'match_type': match_type,
                'mapped': is_mapped,
            }
        )

    rows.sort(
        key=lambda r: (
            (r['product_name'] or '').lower(),
            (r['rbcar_id'] or ''),
            r['id_product'],
            (r['low_price'] if r['low_price'] is not None else 9_999_999),
            (r['rbset_id'] or ''),
        )
    )

    total_products = len(products)
    total_mapped = sum(1 for p in products if p.opprd_id_product in mappings)
    total_unmapped = total_products - total_mapped

    return jsonify(
        {
            'success': True,
            'count': len(rows),
            'rows': rows,
            'stats': {
                'total_in_snapshot': total_products,
                'mapped': total_mapped,
                'unmapped': total_unmapped,
                'snapshot_date': latest_date,
            },
        }
    )


# =========================================================================
# EXPANSION MAPPING
# =========================================================================


@price_bp.route('/cardmarket-unmapped-expansions')
@login_required
def cardmarket_unmapped_expansions():
    """List expansions with NULL opset_id mapping."""
    from app.services.cardmarket_loader import CARDMARKET_URLS

    latest_date = db.session.query(func.max(OpcmProduct.opprd_date)).scalar()

    count_map = {}
    if latest_date:
        rows = (
            db.session.query(OpcmProduct.opprd_id_expansion, func.count(OpcmProduct.opprd_id_product))
            .filter(OpcmProduct.opprd_date == latest_date)
            .group_by(OpcmProduct.opprd_id_expansion)
            .all()
        )
        count_map = {r[0]: r[1] for r in rows if r[0] is not None}

    unmapped = OpcmExpansion.query.filter(OpcmExpansion.opexp_opset_id.is_(None)).order_by(OpcmExpansion.opexp_id).all()

    sets = OpSet.query.order_by(OpSet.opset_id).all()

    return jsonify(
        {
            'success': True,
            'count': len(unmapped),
            'expansions': [
                {
                    'rbexp_id': e.opexp_id,
                    'rbexp_name': e.opexp_name,
                    'products_count': count_map.get(e.opexp_id, 0),
                }
                for e in unmapped
            ],
            'existing_sets': [
                {
                    'rbset_id': s.opset_id,
                    'rbset_name': s.opset_name,
                }
                for s in sets
            ],
            'download_urls': CARDMARKET_URLS,
        }
    )


@price_bp.route('/cardmarket-map-expansion', methods=['POST'])
@login_required
def cardmarket_map_expansion():
    """Map a Cardmarket expansion to an internal set."""
    data = request.get_json() or {}
    rbexp_id = data.get('rbexp_id')
    rbset_id = (data.get('rbset_id') or '').strip()
    rbset_name = (data.get('rbset_name') or '').strip()
    rbexp_name = (data.get('rbexp_name') or '').strip() or None

    if not rbexp_id or not rbset_id:
        return jsonify({'success': False, 'message': 'rbexp_id and rbset_id required'}), 400

    exp = OpcmExpansion.query.get(rbexp_id)
    if not exp:
        return jsonify({'success': False, 'message': f'Expansion {rbexp_id} not found'}), 404

    opset = OpSet.query.get(rbset_id)
    if not opset:
        if not rbset_name:
            return jsonify(
                {'success': False, 'message': f'Set {rbset_id} does not exist. Provide rbset_name to create it.'}
            ), 400
        opset = OpSet(
            opset_id=rbset_id,
            opset_name=rbset_name,
            opset_ncard=data.get('rbset_ncard'),
        )
        db.session.add(opset)

    exp.opexp_opset_id = rbset_id
    if rbexp_name:
        exp.opexp_name = rbexp_name

    db.session.commit()
    return jsonify({'success': True})


# =========================================================================
# IGNORED PRODUCTS
# =========================================================================


@price_bp.route('/ignored/add', methods=['POST'])
@login_required
@validate_json(IgnoredAdd)
def ignored_add():
    """Add a product to the ignored list."""
    data = request.validated_data
    existing = OpcmIgnored.query.filter_by(
        opig_id_product=data.id_product,
        opig_name=data.name,
    ).first()
    if not existing:
        db.session.add(
            OpcmIgnored(
                opig_id_product=data.id_product,
                opig_name=data.name,
            )
        )
        db.session.commit()
    return jsonify({'success': True})


@price_bp.route('/ignored/restore', methods=['POST'])
@login_required
@validate_json(IgnoredRestore)
def ignored_restore():
    """Remove a product from the ignored list."""
    data = request.validated_data
    OpcmIgnored.query.filter_by(
        opig_id_product=data.id_product,
        opig_name=data.name,
    ).delete()
    db.session.commit()
    return jsonify({'success': True})


@price_bp.route('/ignored', methods=['GET'])
@login_required
def ignored_list():
    """List all ignored products."""
    rows = OpcmIgnored.query.order_by(OpcmIgnored.opig_ignored_at.desc()).all()

    price_map = {}
    if rows:
        latest_price_date = db.session.query(func.max(OpcmPrice.opprc_date)).scalar()
        if latest_price_date:
            ids = [r.opig_id_product for r in rows]
            prices = OpcmPrice.query.filter(
                OpcmPrice.opprc_date == latest_price_date,
                OpcmPrice.opprc_id_product.in_(ids),
            ).all()
            price_map = {p.opprc_id_product: float(p.opprc_low) if p.opprc_low is not None else None for p in prices}

    return jsonify(
        {
            'success': True,
            'ignored': [
                {
                    'id_product': r.opig_id_product,
                    'name': r.opig_name,
                    'low_price': price_map.get(r.opig_id_product),
                    'ignored_at': r.opig_ignored_at.isoformat() if r.opig_ignored_at else None,
                }
                for r in rows
            ],
        }
    )


# =========================================================================
# AUTO-MATCH
# =========================================================================


@price_bp.route('/auto-match', methods=['POST'])
@login_required
def auto_match_route():
    """Run the auto-matcher (dry_run optionally applied via body)."""
    from app.services.cardmarket_matcher import auto_match

    body = request.get_json(silent=True) or {}
    dry_run = bool(body.get('dry_run', False))
    max_groups = body.get('max_groups')
    try:
        max_groups = int(max_groups) if max_groups is not None else None
    except (TypeError, ValueError):
        max_groups = None
    try:
        result = auto_match(dry_run=dry_run, max_groups=max_groups)
        return jsonify(result)
    except Exception:
        logger.exception('auto-match failed')
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Internal server error'}), 500


@price_bp.route('/auto-match/apply', methods=['POST'])
@login_required
@validate_json(AutoMatchApply)
def auto_match_apply():
    """Apply a selective list of auto-match pairings."""
    data = request.validated_data
    inserted = 0
    review = 0

    for pairing in data.pairings:
        existing = OpcmProductCardMap.query.filter_by(
            oppcm_id_product=pairing.id_product,
        ).first()
        if existing:
            review += 1
            continue
        db.session.add(
            OpcmProductCardMap(
                oppcm_id_product=pairing.id_product,
                oppcm_opset_id=pairing.rbset_id,
                oppcm_opcar_id=pairing.rbcar_id,
                oppcm_opcar_version=pairing.rbcar_version,
                oppcm_foil=pairing.foil,
                oppcm_match_type='auto',
                oppcm_confidence=0.7,
            )
        )
        inserted += 1

    db.session.commit()
    return jsonify({'success': True, 'inserted': inserted, 'review': review})


# =========================================================================
# ADD ENTRY (card)
# =========================================================================


@price_bp.route('/add-entry', methods=['POST'])
@login_required
def add_entry():
    """Create or update a card entry (for manual mapping support)."""
    data = request.get_json() or {}
    rbset_id = (data.get('rbcar_rbset_id') or '').strip()
    rbcar_id = (data.get('rbcar_id') or '').strip()
    rbcar_version = (data.get('rbcar_version') or 'p0').strip()
    rbcar_name = (data.get('rbcar_name') or '').strip()

    if not rbset_id or not rbcar_id or not rbcar_name:
        return jsonify({'success': False, 'message': 'rbcar_rbset_id, rbcar_id, and rbcar_name are required'}), 400

    if not OpSet.query.get(rbset_id):
        return jsonify({'success': False, 'message': f'Set "{rbset_id}" does not exist. Create it first.'}), 400

    existing = OpCard.query.filter_by(opcar_opset_id=rbset_id, opcar_id=rbcar_id, opcar_version=rbcar_version).first()
    status = 'updated' if existing else 'created'

    if not existing:
        existing = OpCard(
            opcar_opset_id=rbset_id,
            opcar_id=rbcar_id,
            opcar_version=rbcar_version,
            opcar_name=rbcar_name,
        )
        db.session.add(existing)

    for f in (
        'opcar_category',
        'opcar_color',
        'opcar_rarity',
        'opcar_cost',
        'opcar_life',
        'opcar_power',
        'opcar_counter',
        'opcar_attribute',
        'opcar_type',
        'opcar_effect',
        'opcar_block_icon',
        'image_url',
        'image',
    ):
        if f in data:
            val = data.get(f)
            setattr(existing, f, val if val != '' else None)

    if not existing.opcar_name:
        existing.opcar_name = rbcar_name

    db.session.commit()
    return jsonify(
        {
            'success': True,
            'status': status,
            'rbset_id': rbset_id,
            'rbcar_id': rbcar_id,
            'rbcar_version': existing.opcar_version,
            'rbcar_name': existing.opcar_name,
        }
    )
