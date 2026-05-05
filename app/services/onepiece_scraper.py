"""
One Piece Card scraper.
Fetches card data + images from https://en.onepiece-cardgame.com/cardlist/
Inserts into opcards table and saves images to app/static/images/cards/<set_id>/
"""
from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup
from flask import current_app
from app import db
from app.models import OpCard, OpSet

logger = logging.getLogger(__name__)

BASE_URL = "https://en.onepiece-cardgame.com"
CARD_LIST_URL = f"{BASE_URL}/cardlist/"

_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Connection': 'keep-alive',
}


def _get_session() -> requests.Session:
    """Create session with browser-like headers."""
    session = requests.Session()
    session.headers.update(_HEADERS)
    return session


def _parse_set_code_from_label(label: str) -> str:
    """Extract set code from a label like 'ROMANCE DAWN [OP-01]' -> 'OP-01'."""
    special = {
        'Promotion card': 'P',
        'Other Product Card': 'OPC',
    }
    if label in special:
        return special[label]
    m = re.search(r'\[([^\]]+)\]', label)
    if m:
        return m.group(1)
    return label


def _normalize_set_name(code: str, label: str) -> str:
    """Normalize special set names requested by user."""
    if code == 'P':
        return 'Promo Cards'
    if code == 'OPC':
        return 'Other / Miscellaneous'
    return label


def _derive_opset_id(card_id_prefix: str) -> str:
    """Convert card ID prefix to opset_id format.
    
    Examples:
        OP01 -> OP-01
        EB04 -> EB-04
        ST01 -> ST-01
        PRB01 -> PRB-01
        P -> P (promotion cards, no numeric part)
    """
    m = re.match(r'^([A-Za-z]+)(\d+)$', card_id_prefix)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return card_id_prefix


def _safe_int(value: str) -> Optional[int]:
    """Convert string to int, return None if empty or non-numeric."""
    if not value:
        return None
    try:
        return int(value.strip())
    except (ValueError, TypeError):
        return None


def _split_card_id_version(card_id_full: str) -> tuple[str, str]:
    """Split site card IDs into base id + version.

    Examples:
        OP07-076 -> (OP07-076, p0)
        OP07-076_p1 -> (OP07-076, p1)
        OP07-076_r1 -> (OP07-076, r1)
    """
    match = re.match(r'^(?P<base>.+?)(?:_(?P<version>[a-z]+\d+))?$', card_id_full)
    if not match:
        return card_id_full, 'p0'
    return match.group('base'), (match.group('version') or 'p0')


def _parse_card_dl(dl_element, set_id: str, value_id: str,
                   set_code_override: Optional[str] = None) -> Optional[dict]:
    """Parse a <dl class='modalCol'> element into a card dict.

    Args:
        dl_element: BeautifulSoup Tag for the <dl> element.
        set_id: The raw series dropdown value (numeric ID).
        value_id: The raw series dropdown value (e.g., '569302').
        set_code_override: If provided, use this as opset_id (e.g. 'PRB-02')
                          instead of deriving from card_id prefix.

    Returns dict with card fields, or None on failure.
    """
    card_id_full = dl_element.get('id', '').strip()
    if not card_id_full:
        return None

    base_card_id, opcar_version = _split_card_id_version(card_id_full)

    # Parse the parts of card_id: supports multiple formats
    # Format 1: "OP01-001" (letters+digits-digits) — most cards
    # Format 2: "P-044" (letters only-digits) — promotion cards
    # Format 3: "ST01-001" (letters+digits-digits) — starter decks
    m = re.match(r'^([A-Za-z]+\d*)-(\d+[a-zA-Z]*)$', base_card_id)
    if not m:
        logger.warning(f"Cannot parse card ID format: {card_id_full}")
        return None
    card_id_prefix = m.group(1)  # e.g., "OP01", "EB04", "P", "ST01"
    card_number = m.group(2)     # e.g., "001", "044"

    # Use set_code_override if provided (e.g. PRB-02 from dropdown label),
    # otherwise derive from card_id prefix (fallback for legacy/tests)
    if set_code_override:
        opset_id = set_code_override
    else:
        opset_id = _derive_opset_id(card_id_prefix)

    # Parse infoCol
    info_col = dl_element.select_one('.infoCol')
    info_spans = info_col.find_all('span') if info_col else []
    rarity = info_spans[1].get_text(strip=True) if len(info_spans) > 1 else None
    category = info_spans[2].get_text(strip=True) if len(info_spans) > 2 else None

    # Card name
    name_el = dl_element.select_one('.cardName')
    name = name_el.get_text(strip=True) if name_el else ''

    # Life vs Cost
    cost_el = dl_element.select_one('.cost')
    life = None
    cost = None
    if cost_el:
        h3 = cost_el.find('h3')
        h3_text = h3.get_text(strip=True) if h3 else ''
        # Get the text after removing the h3 text
        cost_text = cost_el.get_text(separator=' ', strip=True)
        # Remove the h3 label
        if h3:
            cost_text = cost_text.replace(h3.get_text(strip=True), '', 1).strip()
        value = _safe_int(cost_text)
        if 'Life' in h3_text:
            life = value
        elif 'Cost' in h3_text:
            cost = value

    # Attribute
    attr_el = dl_element.select_one('.attribute')
    attribute = None
    if attr_el:
        img = attr_el.find('img')
        if img:
            attribute = img.get('alt', '').strip() or None
        if not attribute:
            # Try the <i> tag
            i_el = attr_el.find('i')
            if i_el:
                attribute = i_el.get_text(strip=True) or None

    # Power
    power_el = dl_element.select_one('.power')
    power = None
    if power_el:
        power_text = power_el.get_text(separator=' ', strip=True)
        # Remove "Power" label
        h3 = power_el.find('h3')
        if h3:
            power_text = power_text.replace(h3.get_text(strip=True), '', 1).strip()
        power = _safe_int(power_text)

    # Counter
    counter_el = dl_element.select_one('.counter')
    counter = None
    if counter_el:
        counter_text = counter_el.get_text(separator=' ', strip=True)
        h3 = counter_el.find('h3')
        if h3:
            counter_text = counter_text.replace(h3.get_text(strip=True), '', 1).strip()
        # "-" means no counter
        if counter_text.strip() == '-':
            counter = None
        else:
            counter = _safe_int(counter_text)

    # Color
    color_el = dl_element.select_one('.color')
    color = None
    if color_el:
        color_text = color_el.get_text(separator=' ', strip=True)
        h3 = color_el.find('h3')
        if h3:
            color_text = color_text.replace(h3.get_text(strip=True), '', 1).strip()
        color = color_text or None

    # Block icon
    block_el = dl_element.select_one('.block')
    block_icon = None
    if block_el:
        block_text = block_el.get_text(separator=' ', strip=True)
        h3 = block_el.find('h3')
        if h3:
            label = ' '.join(h3.stripped_strings)
            block_text = re.sub(rf'^{re.escape(label)}\s*', '', block_text).strip()
        block_icon = _safe_int(block_text)

    # Type
    feature_el = dl_element.select_one('.feature')
    card_type = None
    if feature_el:
        type_text = feature_el.get_text(separator=' ', strip=True)
        h3 = feature_el.find('h3')
        if h3:
            type_text = type_text.replace(h3.get_text(strip=True), '', 1).strip()
        card_type = type_text or None

    # Effect
    text_el = dl_element.select_one('.text')
    effect = None
    if text_el:
        effect_text = text_el.get_text(separator=' ', strip=True)
        h3 = text_el.find('h3')
        if h3:
            effect_text = effect_text.replace(h3.get_text(strip=True), '', 1).strip()
        effect = effect_text or None

    # Card Set(s)
    getinfo_el = dl_element.select_one('.getInfo')
    card_set_str = None
    if getinfo_el:
        set_text = getinfo_el.get_text(separator=' ', strip=True)
        h3 = getinfo_el.find('h3')
        if h3:
            set_text = set_text.replace(h3.get_text(strip=True), '', 1).strip()
        card_set_str = set_text or None

    # Image URL
    image_filename = f"{card_id_full}.png"
    image_url = f"{BASE_URL}/images/cardlist/card/{card_id_full}.png"

    # For variant cards, the PK (opcar_opset_id + opcar_id) includes the variant suffix
    # e.g., "001" for normal, "001_p1" for variant
    return {
        'opcar_opset_id': opset_id,
        'opcar_id': base_card_id,
        'opcar_version': opcar_version,
        'opcar_name': name,
        'opcar_category': category,
        'opcar_rarity': rarity,
        'opcar_cost': cost,
        'opcar_life': life,
        'opcar_power': power,
        'opcar_counter': counter,
        'opcar_attribute': attribute,
        'opcar_type': card_type,
        'opcar_effect': effect,
        'opcar_color': color,
        'opcar_block_icon': block_icon,
        'image_url': image_url,
        'image': image_filename,
    }


def _download_image(session: requests.Session, url: str, dest_path: str) -> bool:
    """Download image to dest_path. Skip if exists."""
    if not url:
        return False
    if os.path.exists(dest_path):
        return True
    try:
        resp = session.get(url, timeout=30)
        resp.raise_for_status()
        with open(dest_path, 'wb') as f:
            f.write(resp.content)
        return True
    except Exception as e:
        logger.warning(f"Image download failed {url}: {e}")
        return False


# ──────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────

def refresh_op_sets() -> dict:
    """
    Fetch cardlist page, extract available set options from the series dropdown.
    Returns: { success, sets: [{id, label, code}, ...] }
    """
    session = _get_session()
    try:
        response = session.get(CARD_LIST_URL, timeout=30)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        select_el = soup.find('select', {'name': 'series'})
        if not select_el:
            return {'success': False, 'message': 'Cannot find series dropdown', 'sets': []}

        sets = []
        for option in select_el.find_all('option'):
            value = (option.get('value') or '').strip()
            if not value:
                continue
            label = option.get_text(strip=True)
            code = _parse_set_code_from_label(label)
            normalized_name = _normalize_set_name(code, label)

            sets.append({
                'id': value,
                'label': label,
                'code': code,
                'name': normalized_name,
            })

        return {
            'success': True,
            'sets': sets,
            'count': len(sets),
        }
    except Exception as e:
        logger.error(f"refresh_op_sets failed: {e}")
        return {'success': False, 'message': str(e), 'sets': []}


def extract_op_cards(filter_sets: list[dict] | list[str] | None = None) -> dict:
    """
    Scrape One Piece cardlist, extract cards, download images, insert/update DB.

    Args:
        filter_sets: list of dicts {id, code} from dropdown, or list of numeric
                     value IDs (legacy). Empty/None = all sets (fetched from dropdown).

    Returns:
        { success, steps: [{step, status, message}], stats: {...} }
    """
    steps = []
    stats = {
        'total_scraped': 0,
        'filtered': 0,
        'inserted': 0,
        'updated': 0,
        'skipped': 0,
        'images_downloaded': 0,
        'images_failed': 0,
        'images_existed': 0,
        'sets_created': 0,
        'errors': [],
    }

    session = _get_session()

    # Normalize filter_sets to list of {id, code} dicts
    if not filter_sets:
        steps.append({'step': '1. Fetch set list', 'status': 'RUNNING', 'message': 'Fetching available sets...'})
        try:
            refresh_result = refresh_op_sets()
            if not refresh_result['success']:
                steps[-1]['status'] = 'ERROR'
                steps[-1]['message'] = refresh_result.get('message', 'Failed to get sets')
                return {'success': False, 'steps': steps, 'stats': stats}
            filter_sets = refresh_result['sets']  # [{id, label, code}, ...]
            steps[-1]['status'] = 'SUCCESS'
            steps[-1]['message'] = f'Found {len(filter_sets)} sets'
        except Exception as e:
            steps[-1]['status'] = 'ERROR'
            steps[-1]['message'] = str(e)
            return {'success': False, 'steps': steps, 'stats': stats}
    else:
        # Normalize: if list of strings, convert to dicts (legacy support)
        if filter_sets and isinstance(filter_sets[0], str):
            filter_sets = [{'id': v, 'code': None} for v in filter_sets]
        steps.append({'step': '1. Selected sets', 'status': 'INFO', 'message': f'{len(filter_sets)} sets selected'})

    all_cards = []
    set_summaries: dict[str, dict[str, object]] = {}
    step_idx = 2

    # Step 2: Fetch cards for each set
    for set_info in filter_sets:
        value_id = set_info['id'] if isinstance(set_info, dict) else set_info
        set_code = set_info.get('code') if isinstance(set_info, dict) else None
        set_name = set_info.get('name') if isinstance(set_info, dict) else None
        step_label = f'{step_idx}. Fetch {set_code or value_id}'
        steps.append({'step': step_label, 'status': 'RUNNING', 'message': f'Fetching cards for {set_code or value_id}...'})
        try:
            # Use GET with query param (all cards returned in single page)
            resp = session.get(
                f'{CARD_LIST_URL}?series={value_id}',
                timeout=60,
            )
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            dl_elements = soup.find_all('dl', class_='modalCol')

            # If no set_code provided, try to extract from page count
            if not set_code:
                # Try to get it from the first card's ID prefix
                if dl_elements:
                    first_id = dl_elements[0].get('id', '')
                    base_id = re.sub(r'_[a-z]+\d+$', '', first_id)
                    m = re.match(r'^([A-Za-z]+\d*)-', base_id)
                    if m:
                        set_code = _derive_opset_id(m.group(1))

            set_cards = 0
            for dl in dl_elements:
                card_data = _parse_card_dl(dl, set_id=value_id, value_id=value_id, set_code_override=set_code)
                if card_data is None:
                    continue
                all_cards.append(card_data)
                set_cards += 1

            effective_code = set_code or value_id
            set_summaries[effective_code] = {
                'name': _normalize_set_name(effective_code, set_name or effective_code),
                'ncard': set_cards,
            }

            # Get expected count from page
            count_el = soup.select_one('.countCol')
            expected = count_el.get_text(strip=True) if count_el else '?'

            steps[-1]['status'] = 'SUCCESS'
            steps[-1]['message'] = f'{set_cards} cards parsed ({expected}) for {set_code or value_id}'
            stats['total_scraped'] += set_cards
        except Exception as e:
            steps[-1]['status'] = 'ERROR'
            steps[-1]['message'] = f'Error fetching {set_code or value_id}: {e}'
            stats['errors'].append(str(e))
        step_idx += 1

    if not all_cards:
        steps.append({'step': 'No cards', 'status': 'ERROR', 'message': 'No cards were scraped'})
        return {'success': False, 'steps': steps, 'stats': stats}

    # Step: Ensure sets exist
    step_label = f'{step_idx}. Ensure sets exist'
    steps.append({'step': step_label, 'status': 'RUNNING', 'message': 'Checking/creating sets...'})
    try:
        unique_sets = set()
        for c in all_cards:
            opset_id = c['opcar_opset_id']
            if opset_id not in unique_sets:
                existing = OpSet.query.filter_by(opset_id=opset_id).first()
                summary = set_summaries.get(opset_id, {})
                set_name = summary.get('name', opset_id)
                set_ncard = summary.get('ncard')
                if not existing:
                    db.session.add(OpSet(
                        opset_id=opset_id,
                        opset_name=set_name,
                        opset_ncard=set_ncard,
                    ))
                    stats['sets_created'] += 1
                else:
                    existing.opset_name = set_name
                    existing.opset_ncard = set_ncard
                unique_sets.add(opset_id)
        db.session.commit()
        steps[-1]['status'] = 'SUCCESS'
        steps[-1]['message'] = f'{len(unique_sets)} sets checked, {stats["sets_created"]} created'
    except Exception as e:
        db.session.rollback()
        steps[-1]['status'] = 'ERROR'
        steps[-1]['message'] = f'Set creation error: {e}'
        stats['errors'].append(str(e))
    step_idx += 1

    # Step: Download images
    step_label = f'{step_idx}. Download images'
    steps.append({'step': step_label, 'status': 'RUNNING', 'message': 'Downloading card images...'})
    try:
        static_dir = current_app.static_folder or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'static'
        )
        cards_img_base = os.path.join(static_dir, 'images', 'cards')

        for card_data in all_cards:
            set_folder = os.path.join(cards_img_base, card_data['opcar_opset_id'].lower())
            Path(set_folder).mkdir(parents=True, exist_ok=True)

            dest = os.path.join(set_folder, card_data['image'])
            if os.path.exists(dest):
                stats['images_existed'] += 1
            else:
                if _download_image(session, card_data['image_url'], dest):
                    stats['images_downloaded'] += 1
                else:
                    stats['images_failed'] += 1

        steps[-1]['status'] = 'SUCCESS'
        steps[-1]['message'] = (
            f"Downloaded {stats['images_downloaded']} new, "
            f"{stats['images_existed']} existed, "
            f"{stats['images_failed']} failed"
        )
    except Exception as e:
        steps[-1]['status'] = 'ERROR'
        steps[-1]['message'] = f'Image download error: {e}'
        stats['errors'].append(str(e))
    step_idx += 1

    # Step: Database insert
    step_label = f'{step_idx}. Database insert'
    steps.append({'step': step_label, 'status': 'RUNNING', 'message': 'Inserting cards into database...'})
    try:
        for card_data in all_cards:
            existing = OpCard.query.filter_by(
                opcar_opset_id=card_data['opcar_opset_id'],
                opcar_id=card_data['opcar_id'],
                opcar_version=card_data['opcar_version'],
            ).first()

            if existing:
                changed = False
                for key, val in card_data.items():
                    if key in ('opcar_opset_id', 'opcar_id', 'opcar_version'):
                        continue
                    if getattr(existing, key, None) != val:
                        setattr(existing, key, val)
                        changed = True
                if changed:
                    stats['updated'] += 1
                else:
                    stats['skipped'] += 1
            else:
                new_card = OpCard(
                    opcar_opset_id=card_data['opcar_opset_id'],
                    opcar_id=card_data['opcar_id'],
                    opcar_version=card_data['opcar_version'],
                    opcar_name=card_data['opcar_name'],
                    opcar_category=card_data['opcar_category'],
                    opcar_rarity=card_data['opcar_rarity'],
                    opcar_cost=card_data['opcar_cost'],
                    opcar_life=card_data['opcar_life'],
                    opcar_power=card_data['opcar_power'],
                    opcar_counter=card_data['opcar_counter'],
                    opcar_attribute=card_data['opcar_attribute'],
                    opcar_type=card_data['opcar_type'],
                    opcar_effect=card_data['opcar_effect'],
                    opcar_color=card_data['opcar_color'],
                    opcar_block_icon=card_data['opcar_block_icon'],
                    image_url=card_data['image_url'],
                    image=card_data['image'],
                )
                db.session.add(new_card)
                stats['inserted'] += 1

        db.session.commit()
        steps[-1]['status'] = 'SUCCESS'
        steps[-1]['message'] = (
            f"Inserted {stats['inserted']}, "
            f"updated {stats['updated']}, "
            f"unchanged {stats['skipped']}"
        )
    except Exception as e:
        db.session.rollback()
        steps[-1]['status'] = 'ERROR'
        steps[-1]['message'] = f'DB error: {e}'
        stats['errors'].append(str(e))

    return {
        'success': True,
        'steps': steps,
        'stats': stats,
    }
