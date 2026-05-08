"""
Cardmarket data loader service for One Piece (game 18).
Downloads product catalogs and price guides from Cardmarket S3,
validates changes via SHA-256, and loads to PostgreSQL tables.
"""

import hashlib
import json
import logging
import re
from collections import Counter
from datetime import datetime
from typing import Optional

import requests

from app import db
from app.models.cardmarket import (
    OpcmCategory,
    OpcmExpansion,
    OpcmLoadHistory,
    OpcmPrice,
    OpcmProduct,
    OpcmProductCardMap,
)

logger = logging.getLogger(__name__)

CARDMARKET_URLS = {
    'price_guide': 'https://downloads.s3.cardmarket.com/productCatalog/priceGuide/price_guide_18.json',
    'singles': 'https://downloads.s3.cardmarket.com/productCatalog/productList/products_singles_18.json',
    'nonsingles': 'https://downloads.s3.cardmarket.com/productCatalog/productList/products_nonsingles_18.json',
}


class CardmarketLoader:
    """Orchestrates download, validation, and loading of Cardmarket data."""

    def __init__(self, progress_callback=None):
        self.steps = []
        self.errors = []
        self.today = datetime.utcnow().strftime('%Y%m%d')
        self.unmatched_count = 0
        self._progress_callback = progress_callback

    def run(self, urls: Optional[dict] = None) -> dict:
        """Main orchestrator. Downloads, validates, loads all 3 files.

        Returns dict: {success: bool, steps: list, errors: list}
        """
        urls = urls or CARDMARKET_URLS

        try:
            # Step 1: Download all 3 files
            self._add_step('Download', 'RUNNING', 'Downloading files from Cardmarket...')

            price_data = self._download_json(urls['price_guide'], 'price_guide')
            singles_data = self._download_json(urls['singles'], 'singles')
            nonsingles_data = self._download_json(urls['nonsingles'], 'nonsingles')

            if not all([price_data, singles_data, nonsingles_data]):
                self._update_step('Download', 'ERROR', 'Failed to download one or more files')
                return self._result(False)

            self._update_step('Download', 'SUCCESS', 'All 3 files downloaded successfully')

            # Step 2: Compute hashes for change detection
            self._add_step('Validation', 'RUNNING', 'Checking for changes...')

            price_hash = self._compute_hash(price_data)
            singles_hash = self._compute_hash(singles_data)
            nonsingles_hash = self._compute_hash(nonsingles_data)

            price_already = self._check_already_loaded('price_guide', price_hash)

            singles_should_load = not self._check_already_loaded('singles', singles_hash)
            nonsingles_should_load = not self._check_already_loaded('nonsingles', nonsingles_hash)

            validation_msg = []
            if not singles_should_load:
                validation_msg.append('Singles: no changes')
            if not nonsingles_should_load:
                validation_msg.append('Non-singles: no changes')
            validation_msg.append(f'Price guide: {"reload" if price_already else "new load"}')

            self._update_step('Validation', 'SUCCESS', '; '.join(validation_msg))

            # Step 3: Load categories & expansions
            if singles_should_load or nonsingles_should_load:
                self._add_step('Categories & Expansions', 'RUNNING', 'Loading lookup tables...')
                all_products = []
                if singles_should_load:
                    all_products.extend(singles_data.get('products', []))
                if nonsingles_should_load:
                    all_products.extend(nonsingles_data.get('products', []))

                cat_count = self._extract_categories(all_products)
                exp_count = self._extract_expansions(all_products)
                self._update_step(
                    'Categories & Expansions', 'SUCCESS', f'{cat_count} categories, {exp_count} expansions loaded'
                )

            # Step 4: Load products
            products_loaded = 0
            if singles_should_load or nonsingles_should_load:
                self._add_step('Products', 'RUNNING', 'Loading product data...')

                if singles_should_load:
                    count = self._load_products(singles_data.get('products', []), 'single')
                    products_loaded += count
                    self._record_history('singles', singles_hash, count, 'success', f'Loaded {count} singles')

                if nonsingles_should_load:
                    count = self._load_products(nonsingles_data.get('products', []), 'nonsingle')
                    products_loaded += count
                    self._record_history('nonsingles', nonsingles_hash, count, 'success', f'Loaded {count} nonsingles')

                self._update_step('Products', 'SUCCESS', f'{products_loaded} products loaded')
            else:
                self._add_step('Products', 'SKIPPED', 'No changes detected in product files')
                self._record_history('singles', singles_hash, 0, 'skipped', 'No changes')
                self._record_history('nonsingles', nonsingles_hash, 0, 'skipped', 'No changes')

            # Step 5: Auto-map expansions to internal sets
            self._add_step('Expansion Mapping', 'RUNNING', 'Auto-mapping expansions to sets by card ID analysis...')
            # Use ALL products (singles + nonsingles) for best coverage
            combined_products = singles_data.get('products', []) + nonsingles_data.get('products', [])
            exp_map = self._auto_map_expansions(combined_products)
            exp_msg = (
                f'{exp_map["auto_mapped"]} auto-mapped, '
                f'{exp_map["already_mapped"]} already mapped, '
                f'{exp_map["no_match"]} no match'
            )
            self._update_step('Expansion Mapping', 'SUCCESS', exp_msg)

            # Step 6: Load prices (always daily)
            self._add_step('Prices', 'RUNNING', 'Loading price data...')
            price_count = self._load_prices(price_data.get('priceGuides', []))
            self._record_history(
                'price_guide', price_hash, price_count, 'success', f'Loaded {price_count} price records'
            )
            self._update_step('Prices', 'SUCCESS', f'{price_count} price records loaded')

            # Step 7: Auto-map products to internal cards
            self._add_step('Product Mapping', 'RUNNING', 'Auto-mapping products to cards...')
            map_counts = self._update_product_card_map()
            self.unmatched_count = map_counts['unmatched']
            map_msg = (
                f'{map_counts["auto_matched"]} auto-matched, '
                f'{map_counts["unmatched"]} unmatched, '
                f'{map_counts["already_mapped"]} already mapped'
            )
            self._update_step('Product Mapping', 'SUCCESS', map_msg)

            db.session.commit()

            return self._result(True)

        except Exception as e:
            db.session.rollback()
            logger.error(f'Cardmarket load failed: {e}', exc_info=True)
            self.errors.append(str(e))
            return self._result(False)

    def _sanitize_for_log(self, value: object) -> str:
        """Sanitize user-influenced values before logging to prevent log injection."""
        return str(value).replace('\r', '').replace('\n', '')

    def _download_json(self, url: str, file_type: str) -> Optional[dict]:
        """Download JSON file from URL."""
        # SSRF protection: only allow Cardmarket S3 domain
        from urllib.parse import urlparse

        parsed = urlparse(url)
        if parsed.netloc != 'downloads.s3.cardmarket.com':
            safe_netloc = (parsed.netloc or '').replace('\r', '').replace('\n', '')
            logger.error('Blocked download from unauthorized host: %s', safe_netloc)
            self.errors.append(f'Download blocked for {file_type}: unauthorized host')
            return None
        try:
            resp = requests.get(url, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            safe_url = self._sanitize_for_log(url)
            logger.error('Failed to download %s from %s: %s', file_type, safe_url, e)
            self.errors.append(f'Download failed for {file_type}')
            return None

    def _compute_hash(self, data: dict) -> str:
        """Compute SHA-256 hash of JSON data for change detection."""
        json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(json_str.encode('utf-8')).hexdigest()

    def _check_already_loaded(self, file_type: str, new_hash: str) -> bool:
        """Check if this exact file was already loaded today."""
        existing = OpcmLoadHistory.query.filter_by(
            oplh_date=self.today, oplh_file_type=file_type, oplh_hash=new_hash, oplh_status='success'
        ).first()
        return existing is not None

    def _extract_categories(self, products: list) -> int:
        """Extract unique categories from products and upsert to opcm_categories."""
        categories = {}
        for p in products:
            cat_id = p.get('idCategory')
            cat_name = p.get('categoryName')
            if cat_id and cat_name:
                categories[cat_id] = cat_name

        for cat_id, cat_name in categories.items():
            existing = OpcmCategory.query.get(cat_id)
            if existing:
                existing.opcat_name = cat_name
            else:
                db.session.add(OpcmCategory(opcat_id=cat_id, opcat_name=cat_name))

        db.session.flush()
        return len(categories)

    def _extract_expansions(self, products: list) -> int:
        """Extract unique expansions from products and upsert to opcm_expansions."""
        expansions = set()
        for p in products:
            exp_id = p.get('idExpansion')
            if exp_id:
                expansions.add(exp_id)

        for exp_id in expansions:
            existing = OpcmExpansion.query.get(exp_id)
            if not existing:
                db.session.add(OpcmExpansion(opexp_id=exp_id))

        db.session.flush()
        return len(expansions)

    def _auto_map_expansions(self, all_products: list) -> dict:
        """Auto-map Cardmarket expansions to internal sets by analysing card IDs.

        Strategy: singles product names contain card IDs like ``(OP01-001)``.
        For each expansion, extract the set prefix from all its products,
        take the majority vote, convert to opset_id format (``OP-01``), and
        map if the set exists in opsets and the expansion is not yet mapped.

        Returns dict: {auto_mapped: int, already_mapped: int, no_match: int}
        """
        from app.models.set import OpSet

        counts = {'auto_mapped': 0, 'already_mapped': 0, 'no_match': 0}

        # Card ID pattern inside parentheses: (OP01-001), (ST01-001), (EB01-001), (P-001)
        card_id_re = re.compile(r'\(([A-Za-z]+\d*)-(\d+)\)')

        # Group products by expansion
        exp_products: dict[int, list[str]] = {}
        for p in all_products:
            exp_id = p.get('idExpansion')
            name = p.get('name', '')
            if exp_id and name:
                exp_products.setdefault(exp_id, []).append(name)

        # Build set of existing opset_ids for fast lookup
        existing_sets = {s.opset_id for s in OpSet.query.all()}

        for exp_id, names in exp_products.items():
            exp = OpcmExpansion.query.get(exp_id)
            if not exp:
                continue
            if exp.opexp_opset_id is not None:
                counts['already_mapped'] += 1
                continue

            # Extract set prefixes from card IDs in product names
            prefix_counts: Counter = Counter()
            for name in names:
                m = card_id_re.search(name)
                if m:
                    raw_prefix = m.group(1)  # e.g. OP01, ST01, EB04, PRB02
                    # Convert to opset_id format: OP01 -> OP-01
                    pm = re.match(r'^([A-Za-z]+)(\d+)$', raw_prefix)
                    if pm:
                        opset_id = f'{pm.group(1)}-{pm.group(2)}'
                    else:
                        opset_id = raw_prefix  # e.g. P
                    prefix_counts[opset_id] += 1

            if not prefix_counts:
                counts['no_match'] += 1
                continue

            # Take the set with most votes
            best_set, best_count = prefix_counts.most_common(1)[0]
            total = sum(prefix_counts.values())
            confidence = best_count / total if total else 0

            # Only map if the set exists in opsets
            # Accept case-insensitive match
            matched_set = None
            for sid in existing_sets:
                if sid.upper() == best_set.upper():
                    matched_set = sid
                    break

            if matched_set and confidence >= 0.5:
                exp.opexp_opset_id = matched_set
                # Also store expansion name from nonsingles product name if missing
                if not exp.opexp_name:
                    # Use the first product name as expansion name
                    exp.opexp_name = names[0] if names else None
                counts['auto_mapped'] += 1
                logger.info(
                    f'Auto-mapped expansion {exp_id} -> {matched_set} '
                    f'(confidence={confidence:.0%}, {best_count}/{total} cards)'
                )
            else:
                counts['no_match'] += 1

        db.session.flush()
        return counts

    def _load_products(self, products: list, product_type: str) -> int:
        """Load products to opcm_products. Upsert by date + idProduct."""
        count = 0
        for p in products:
            id_product = p.get('idProduct')
            if not id_product:
                continue

            existing = OpcmProduct.query.filter_by(opprd_date=self.today, opprd_id_product=id_product).first()

            if existing:
                existing.opprd_name = p.get('name', '')
                existing.opprd_id_category = p.get('idCategory')
                existing.opprd_category_name = p.get('categoryName')
                existing.opprd_id_expansion = p.get('idExpansion')
                existing.opprd_id_metacard = p.get('idMetacard')
                existing.opprd_date_added = p.get('dateAdded')
                existing.opprd_type = product_type
            else:
                db.session.add(
                    OpcmProduct(
                        opprd_date=self.today,
                        opprd_id_product=id_product,
                        opprd_name=p.get('name', ''),
                        opprd_id_category=p.get('idCategory'),
                        opprd_category_name=p.get('categoryName'),
                        opprd_id_expansion=p.get('idExpansion'),
                        opprd_id_metacard=p.get('idMetacard'),
                        opprd_date_added=p.get('dateAdded'),
                        opprd_type=product_type,
                    )
                )
            count += 1

        db.session.flush()
        return count

    def _load_prices(self, price_guides: list) -> int:
        """Load price guide to opcm_price. Insert new date rows."""
        count = 0
        for p in price_guides:
            id_product = p.get('idProduct')
            if not id_product:
                continue

            existing = OpcmPrice.query.filter_by(opprc_date=self.today, opprc_id_product=id_product).first()

            if existing:
                existing.opprc_id_category = p.get('idCategory')
                existing.opprc_avg = p.get('avg')
                existing.opprc_low = p.get('low')
                existing.opprc_trend = p.get('trend')
                existing.opprc_avg1 = p.get('avg1')
                existing.opprc_avg7 = p.get('avg7')
                existing.opprc_avg30 = p.get('avg30')
                existing.opprc_avg_foil = p.get('avg-foil')
                existing.opprc_low_foil = p.get('low-foil')
                existing.opprc_trend_foil = p.get('trend-foil')
                existing.opprc_avg1_foil = p.get('avg1-foil')
                existing.opprc_avg7_foil = p.get('avg7-foil')
                existing.opprc_avg30_foil = p.get('avg30-foil')
                existing.opprc_low_ex = p.get('low-ex+')
            else:
                db.session.add(
                    OpcmPrice(
                        opprc_date=self.today,
                        opprc_id_product=id_product,
                        opprc_id_category=p.get('idCategory'),
                        opprc_avg=p.get('avg'),
                        opprc_low=p.get('low'),
                        opprc_trend=p.get('trend'),
                        opprc_avg1=p.get('avg1'),
                        opprc_avg7=p.get('avg7'),
                        opprc_avg30=p.get('avg30'),
                        opprc_avg_foil=p.get('avg-foil'),
                        opprc_low_foil=p.get('low-foil'),
                        opprc_trend_foil=p.get('trend-foil'),
                        opprc_avg1_foil=p.get('avg1-foil'),
                        opprc_avg7_foil=p.get('avg7-foil'),
                        opprc_avg30_foil=p.get('avg30-foil'),
                        opprc_low_ex=p.get('low-ex+'),
                    )
                )
            count += 1

        db.session.flush()
        return count

    def _update_product_card_map(self) -> dict:
        """Auto-map Cardmarket products to internal opcards.

        Strategy (in order of priority):
        1. Extract card ID from product name, e.g. "Roronoa Zoro (OP01-001)"
           → card_id=OP01-001, use expansion→set mapping to find the set,
           then look up OpCard by (opset_id, opcar_id).
        2. Fallback: exact name match (only for single-match cases).

        Returns dict with counts: auto_matched, unmatched, already_mapped
        """
        from app.models.card import OpCard

        counts = {'auto_matched': 0, 'unmatched': 0, 'already_mapped': 0}

        # Card ID pattern in product names: (OP01-001), (ST01-007), (P-001)
        card_id_re = re.compile(r'\(([A-Za-z]+\d*-\d+)\)')

        # Build expansion→set lookup
        exp_to_set: dict[int, str] = {}
        for exp in OpcmExpansion.query.filter(OpcmExpansion.opexp_opset_id.isnot(None)).all():
            exp_to_set[exp.opexp_id] = exp.opexp_opset_id

        products = OpcmProduct.query.filter_by(opprd_date=self.today).all()
        if not products:
            latest = db.session.query(db.func.max(OpcmProduct.opprd_date)).scalar()
            if latest:
                products = OpcmProduct.query.filter_by(opprd_date=latest).all()

        for product in products:
            existing = OpcmProductCardMap.query.filter_by(oppcm_id_product=product.opprd_id_product).first()

            if existing:
                counts['already_mapped'] += 1
                continue

            # Strategy 1: card ID from product name + expansion→set
            m = card_id_re.search(product.opprd_name or '')
            if m:
                full_card_id = m.group(1)  # e.g. OP01-001
                opset_id = exp_to_set.get(product.opprd_id_expansion)

                if opset_id:
                    # Try exact match first (version p0)
                    card = OpCard.query.filter_by(
                        opcar_opset_id=opset_id,
                        opcar_id=full_card_id,
                        opcar_version='p0',
                    ).first()

                    if card:
                        db.session.add(
                            OpcmProductCardMap(
                                oppcm_id_product=product.opprd_id_product,
                                oppcm_opset_id=card.opcar_opset_id,
                                oppcm_opcar_id=card.opcar_id,
                                oppcm_opcar_version=card.opcar_version,
                                oppcm_match_type='auto',
                                oppcm_confidence=1.0,
                            )
                        )
                        counts['auto_matched'] += 1
                        continue

            # Strategy 2: fallback — exact name match (strip card ID suffix)
            clean_name = card_id_re.sub('', product.opprd_name or '').strip()
            if clean_name:
                matches = OpCard.query.filter(db.func.lower(OpCard.opcar_name) == clean_name.lower()).all()

                if len(matches) == 1:
                    db.session.add(
                        OpcmProductCardMap(
                            oppcm_id_product=product.opprd_id_product,
                            oppcm_opset_id=matches[0].opcar_opset_id,
                            oppcm_opcar_id=matches[0].opcar_id,
                            oppcm_opcar_version=matches[0].opcar_version,
                            oppcm_match_type='auto',
                            oppcm_confidence=0.8,
                        )
                    )
                    counts['auto_matched'] += 1
                    continue

            counts['unmatched'] += 1

        db.session.flush()
        return counts

    def _record_history(self, file_type: str, hash_val: str, rows: int, status: str, message: str):
        """Record load operation in opcm_load_history."""
        db.session.add(
            OpcmLoadHistory(
                oplh_date=self.today,
                oplh_file_type=file_type,
                oplh_hash=hash_val,
                oplh_rows=rows,
                oplh_status=status,
                oplh_message=message,
                oplh_loaded_at=datetime.utcnow(),
            )
        )
        db.session.flush()

    def _add_step(self, step: str, status: str, message: str):
        """Add a new step to the progress tracker."""
        item = {'step': step, 'status': status, 'message': message}
        self.steps.append(item)
        if self._progress_callback:
            self._progress_callback(item)

    def _update_step(self, step: str, status: str, message: str):
        """Update the last step matching the given name."""
        for s in reversed(self.steps):
            if s['step'] == step:
                s['status'] = status
                s['message'] = message
                if self._progress_callback:
                    self._progress_callback(s)
                break

    def _result(self, success: bool) -> dict:
        """Build result dict."""
        return {
            'success': success,
            'date': self.today,
            'steps': self.steps,
            'errors': self.errors,
            'unmatched_count': self.unmatched_count,
        }
