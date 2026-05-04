"""
Cardmarket auto-matcher for One Piece.

Assigns unmapped Cardmarket products to internal opcards by name matching
and (set, card_id, foil) slot expansion.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Optional

from sqlalchemy import func

from app import db
from app.models import OpCard
from app.models.cardmarket import (
    OpcmProduct, OpcmPrice, OpcmExpansion, OpcmProductCardMap, OpcmIgnored,
)


_NOISE_RE = re.compile(
    r'\b(foil|showcase|signed|plated|promo|extended|alt(?:ernate)?\s+art|'
    r'borderless|full[\s-]*art|prerelease|prelaunch|launch|'
    r'v\.?\s*\d+|version\s*\d+)\b',
    re.IGNORECASE,
)

_PUNCT_RE = re.compile(r'[^a-zA-Z0-9 ]+')
_WS_RE = re.compile(r'\s+')


def normalize_name(name: Optional[str]) -> str:
    """Normalize a name for comparison: lowercase, no variant suffixes,
    no punctuation, collapsed whitespace."""
    if not name:
        return ''
    n = _NOISE_RE.sub(' ', name)
    n = _PUNCT_RE.sub(' ', n)
    n = re.sub(r'\b\d+[a-z]?\b', ' ', n)
    n = _WS_RE.sub(' ', n).strip().lower()
    return n


_RARITY_RANK = {'common': 0, 'uncommon': 0, 'rare': 1, 'super rare': 2, 'secret rare': 2.5}


def card_rank_key(card: OpCard):
    """Sort key for expected price (ascending)."""
    rarity = (card.opcar_rarity or '').lower()
    opset_id = card.opcar_opset_id or ''
    opcar_id = card.opcar_id or ''
    is_promo_set = opset_id.endswith('X') or opset_id.startswith('PR')

    base = _RARITY_RANK.get(rarity, 3) * 1.0

    suffix_bonus = 0.0
    suffix_match = re.match(r'^\d+([a-z]+)$', opcar_id)
    if suffix_match:
        suffix = suffix_match.group(1)
        if 'a' in suffix:
            suffix_bonus += 0.30
        if 's' in suffix:
            suffix_bonus += 0.55

    set_bonus = 0.0
    if is_promo_set:
        if rarity in ('super rare', 'secret rare'):
            set_bonus = 1.50
        elif rarity == 'rare':
            set_bonus = 0.20
        else:
            set_bonus = 0.10

    return (base + suffix_bonus + set_bonus, opset_id, opcar_id)


def _get_latest_prices() -> dict[int, float]:
    """Return {id_product: sort_price} from latest price date."""
    latest_per_prod = dict(
        db.session.query(
            OpcmPrice.opprc_id_product,
            func.max(OpcmPrice.opprc_date),
        ).group_by(OpcmPrice.opprc_id_product).all()
    )
    if not latest_per_prod:
        return {}

    prices = {}
    rows = OpcmPrice.query.all()
    for p in rows:
        if latest_per_prod.get(p.opprc_id_product) != p.opprc_date:
            continue
        v = (
            p.opprc_low
            or p.opprc_low_foil
            or p.opprc_avg7
            or p.opprc_avg7_foil
            or 0
        )
        prices[p.opprc_id_product] = float(v) if v is not None else 0.0
    return prices


def _get_expansion_to_set_map() -> dict[int, str]:
    return dict(
        db.session.query(
            OpcmExpansion.opexp_id, OpcmExpansion.opexp_opset_id
        ).filter(OpcmExpansion.opexp_opset_id.isnot(None)).all()
    )


def _group_products_by_metacard(ignored: set | None = None):
    """Group unmapped products by idMetacard from latest date."""
    latest_date = db.session.query(func.max(OpcmProduct.opprd_date)).scalar()
    if not latest_date:
        return {}, 0, 0

    mapped_ids = {r[0] for r in db.session.query(OpcmProductCardMap.oppcm_id_product).all()}
    ignored = ignored or set()

    products = OpcmProduct.query.filter(
        OpcmProduct.opprd_date == latest_date,
        OpcmProduct.opprd_type == 'single',
    ).all()

    groups = defaultdict(list)
    skipped_no_metacard = 0
    ignored_count = 0
    for p in products:
        if p.opprd_id_product in mapped_ids:
            continue
        if (p.opprd_id_product, p.opprd_name) in ignored:
            ignored_count += 1
            continue
        if not p.opprd_id_metacard:
            skipped_no_metacard += 1
            continue
        groups[p.opprd_id_metacard].append(p)
    return groups, skipped_no_metacard, ignored_count


def _build_card_index() -> dict[str, list[OpCard]]:
    """Index normalized_name → [OpCard, ...]."""
    cards = OpCard.query.all()
    idx = defaultdict(list)
    for c in cards:
        idx[normalize_name(c.opcar_name)].append(c)
    return idx


def _expand_slots(card: OpCard, taken: Optional[set] = None) -> list[tuple[OpCard, Optional[str]]]:
    """Generate (card, foil) slots for a candidate card.

    Common/Uncommon → 2 slots ('N' and 'S'). Others → 1 slot (None).
    """
    rarity = (card.opcar_rarity or '').lower()
    card_type = (card.opcar_category or '').lower()

    if rarity in ('c', 'uc', 'common', 'uncommon'):
        raw_slots = [(card, 'N'), (card, 'S')]
    else:
        raw_slots = [(card, None)]

    if taken is None:
        return raw_slots

    return [
        s for s in raw_slots
        if (card.opcar_opset_id, card.opcar_id, s[1]) not in taken
    ]


def auto_match(dry_run: bool = False, max_groups: Optional[int] = None) -> dict:
    """Run the auto-matcher. dry_run=True does not write to DB.

    Returns dict with: assigned, unmatched, skipped, no_candidates, review,
    samples, success.
    """
    ignored: set[tuple] = {
        (r.opig_id_product, r.opig_name)
        for r in OpcmIgnored.query.all()
    }

    groups, skipped_no_metacard, ignored_count = _group_products_by_metacard(ignored=ignored)
    if not groups:
        return {
            'success': True,
            'assigned': 0,
            'unmatched': 0,
            'skipped': skipped_no_metacard,
            'no_candidates': 0,
            'review': 0,
            'ignored_count': ignored_count,
            'samples': [],
            'message': 'No pending products to map',
        }

    prices = _get_latest_prices()
    cards_by_norm = _build_card_index()
    exp_to_set = _get_expansion_to_set_map()

    taken: set[tuple] = set(
        db.session.query(
            OpcmProductCardMap.oppcm_opset_id,
            OpcmProductCardMap.oppcm_opcar_id,
            OpcmProductCardMap.oppcm_foil,
        ).all()
    )

    assigned = 0
    unmatched = 0
    no_candidates = 0
    review = 0
    samples = []

    items = list(groups.items())
    if max_groups:
        items = items[:max_groups]

    for metacard_id, prods in items:
        norm_candidates = {normalize_name(p.opprd_name) for p in prods if p.opprd_name}
        norm_candidates.discard('')
        candidates: list[OpCard] = []
        for n in norm_candidates:
            candidates.extend(cards_by_norm.get(n, []))
        seen = set()
        candidates = [c for c in candidates
                      if (c.opcar_opset_id, c.opcar_id) not in seen
                      and not seen.add((c.opcar_opset_id, c.opcar_id))]

        if not candidates:
            no_candidates += len(prods)
            continue

        candidates.sort(key=card_rank_key)
        slots: list[tuple[OpCard, Optional[str]]] = []
        for c in candidates:
            slots.extend(_expand_slots(c, taken=taken))

        prods_sorted = sorted(
            prods,
            key=lambda p: (prices.get(p.opprd_id_product, 0.0), p.opprd_id_product),
        )

        for prod, slot in zip(prods_sorted, slots):
            card, foil = slot

            if not dry_run:
                existing_map = OpcmProductCardMap.query.filter_by(
                    oppcm_opset_id=card.opcar_opset_id,
                    oppcm_opcar_id=card.opcar_id,
                    oppcm_foil=foil,
                ).first()
                if existing_map and existing_map.oppcm_id_product != prod.opprd_id_product:
                    review += 1
                    continue
                if existing_map and existing_map.oppcm_id_product == prod.opprd_id_product:
                    continue

                m = OpcmProductCardMap(
                    oppcm_id_product=prod.opprd_id_product,
                    oppcm_opset_id=card.opcar_opset_id,
                    oppcm_opcar_id=card.opcar_id,
                    oppcm_foil=foil,
                    oppcm_match_type='auto',
                    oppcm_confidence=0.7,
                )
                db.session.add(m)
            assigned += 1
            samples.append({
                'id_product': prod.opprd_id_product,
                'product_name': prod.opprd_name,
                'price': prices.get(prod.opprd_id_product, 0.0),
                'rbset_id': card.opcar_opset_id,
                'rbcar_id': card.opcar_id,
                'rbcar_name': card.opcar_name,
                'rbpcm_foil': foil,
                'rbcar_rarity': card.opcar_rarity,
            })

        extra = max(0, len(prods_sorted) - len(slots))
        unmatched += extra

    if not dry_run:
        db.session.commit()

    return {
        'success': True,
        'assigned': assigned,
        'unmatched': unmatched,
        'skipped': skipped_no_metacard,
        'no_candidates': no_candidates,
        'review': review,
        'ignored_count': ignored_count,
        'samples': samples,
    }
