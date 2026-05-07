# OPAPP — One Piece TCG Card Manager
## Project Specification (SPEC.md)

> **Version**: 1.0  
> **Date**: 2026-05-07  
> **Repository**: https://github.com/racmos/OPAPP  
> **Branch**: `main`

---

## 1. Overview

OPAPP is a **web-based card manager for the One Piece Trading Card Game (TCG)**. It allows collectors to browse cards, manage their personal collection, build decks, and track market prices via Cardmarket integration.

The application is a **Flask monolith** with domain-oriented blueprints, SQLAlchemy ORM, and Jinja2 templates. It was cloned and adapted from the RBAPP (Riftbound Manager) architecture.

---

## 2. Technology Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.12+ |
| Framework | Flask | 3.1.0 |
| ORM | SQLAlchemy + Flask-SQLAlchemy | 2.0.36 / 3.1.1 |
| Validation | Pydantic | 2.10.5 |
| Auth | Flask-Login | 0.6.3 |
| Database (prod) | PostgreSQL + psycopg | 3.2.13 |
| Database (test) | SQLite in-memory | — |
| Scraping | BeautifulSoup4 + requests | 4.12.3 / 2.32.3 |
| Server | Gunicorn | 23.0.0 |
| Tests | pytest + pytest-flask + pytest-cov | 8.3.4 |
| CSS/JS | Vanilla (custom dark theme) | — |

---

## 3. Architecture

### 3.1 Pattern
- **Monolithic Flask application** with factory pattern (`create_app()`)
- **Blueprint-per-domain**: each major feature has its own blueprint
- **Service layer** for external integrations (scrapers, Cardmarket loaders)
- **Schema layer** for request validation (Pydantic)

### 3.2 Project Structure

```
OPAPP/
├── app/
│   ├── __init__.py              # Flask factory + blueprint registration
│   ├── errors.py                # Global error handlers
│   ├── models/                  # SQLAlchemy models
│   │   ├── user.py              # OpUser (Flask-Login)
│   │   ├── set.py               # OpSet
│   │   ├── card.py              # OpCard
│   │   ├── collection.py        # OpCollection
│   │   ├── deck.py              # OpDeck
│   │   └── cardmarket.py        # Cardmarket-related models
│   ├── routes/
│   │   ├── auth.py              # Auth blueprint
│   │   ├── routes.py            # Main/dashboard blueprint
│   │   └── domains/             # Feature blueprints
│   │       ├── sets.py
│   │       ├── cards.py
│   │       ├── collection.py
│   │       ├── deck.py
│   │       ├── price.py
│   │       └── profile.py
│   ├── schemas/                 # Pydantic validators
│   │   ├── cards.py
│   │   └── validators.py
│   ├── services/                # Business logic / integrations
│   │   ├── onepiece_scraper.py  # Official site scraper
│   │   ├── cardmarket_loader.py # Cardmarket data loader
│   │   └── cardmarket_matcher.py# Product-to-card matching
│   ├── templates/               # Jinja2 HTML templates
│   └── static/                  # CSS, images, JS
├── tests/                       # pytest suite
├── migrations/                  # SQL migrations
├── config.py                    # Flask configuration
├── run.py                       # Development entry point
├── wsgi.py                      # Production WSGI entry
├── requirements.txt
└── pytest.ini
```

### 3.3 URL Prefix
All application routes are mounted under **`/onepiecetcg/`** (configured via NGINX reverse proxy + Flask `url_prefix`).

### 3.4 Database Schema
- **Schema name**: `onepiecetcg`
- **Naming convention**: `snake_case` with table prefix (e.g., `opcar_name`, `opcol_quantity`)
- **Primary DB**: PostgreSQL (production)
- **Test DB**: SQLite in-memory (automatic schema attachment shim for `onepiecetcg`)

---

## 4. Domain Models

### 4.1 Core Entities

| Model | Table | Purpose |
|-------|-------|---------|
| `OpUser` | `opusers` | Registered users (Flask-Login) |
| `OpSet` | `opsets` | Card sets/expansions |
| `OpCard` | `opcards` | Individual cards (PK: set_id + card_id + version) |
| `OpCollection` | `opcollection` | User's owned cards with quantity/condition/foil |
| `OpDeck` | `opdecks` | User-built decks (JSON card lists) |

### 4.2 Cardmarket Integration

| Model | Table | Purpose |
|-------|-------|---------|
| `OpcmProduct` | `opcm_products` | Raw Cardmarket product catalog |
| `OpcmPrice` | `opcm_price` | Daily price snapshots |
| `OpcmCategory` | `opcm_categories` | Category lookup |
| `OpcmExpansion` | `opcm_expansions` | Expansion-to-set mapping |
| `OpcmLoadHistory` | `opcm_load_history` | Load operation audit log |
| `OpcmProductCardMap` | `opcm_product_card_map` | idProduct → internal card mapping |
| `OpcmIgnored` | `opcm_ignored` | User-ignored products |
| `OpProducts` | `opproducts` | Curated product master (future) |

### 4.3 Card Model Details (`OpCard`)

- **PK**: `(opcar_opset_id, opcar_id, opcar_version)` — composite key supports variants (p0, p1, p2)
- **Fields**: name, category, color, rarity, cost, life, power, counter, attribute, type, effect, block_icon, banned, image
- **Image path**: `/onepiecetcg/static/images/cards/<set_folder>/<filename>`

### 4.4 Collection Model Details (`OpCollection`)

- **Synthetic PK**: `opcol_id` (auto-increment)
- Tracks: set, card, version, foil (Y/N), user, quantity, condition, language, sell_price, selling flag
- Supports multiple rows per card for different conditions/languages

### 4.5 Deck Model Details (`OpDeck`)

- **PK**: auto-increment `id`
- **Unique constraint**: `(user, name, seq)` — supports versioned decks
- **Cards stored as JSON**: `{"main": [...], "sideboard": [...]}`
- Metadata: description, mode (1v1), format (Standard), max_set, ncards

---

## 5. Features

### 5.1 Authentication
- User registration, login, logout
- Password hashing with Werkzeug
- Flask-Login session management
- `@login_required` on all app routes

### 5.2 Sets Management
- Browse all One Piece TCG sets
- Set detail page with card listing

### 5.3 Cards Management
- Browse/search/filter cards by set, color, category, rarity, cost, power
- Card detail view with image
- **Manual card creation** (admin/scraper fallback)
- Variant support (p0, p1, p2)

### 5.4 Collection Management
- Add cards to personal collection
- Track quantity, condition, language, foil status
- Mark cards for sale with price

### 5.5 Deck Builder
- Create, edit, delete decks
- Versioned decks (sequential `seq` number)
- Main deck + sideboard support
- Card quantity enforcement

### 5.6 Price Tracking (Cardmarket Integration)
- **One Piece scraper**: Fetches official card data + images from `en.onepiece-cardgame.com/cardlist/`
- **Cardmarket loader**: Downloads daily price guides and product catalogs (game ID 18)
- **Price tables**: Browse Cardmarket prices per card
- **Product-to-card mapping**: Manual and auto-matching of Cardmarket products to internal cards

### 5.7 User Profile
- View and manage user account

---

## 6. External Integrations

### 6.1 One Piece Official Site
- **URL**: `https://en.onepiece-cardgame.com/cardlist/`
- **Purpose**: Scrape card data (ID, name, rarity, stats, images) and download card images
- **Technology**: BeautifulSoup4 + requests with browser-like headers
- **Output**: Inserts into `opcards` / `opsets`; saves images to `app/static/images/cards/<set>/`

### 6.2 Cardmarket
- **Game ID**: 18 (One Piece TCG)
- **URLs**:
  - Price guide: `price_guide_18.json`
  - Singles: `products_singles_18.json`
  - Non-singles: `products_nonsingles_18.json`
- **Purpose**: Load product catalog, daily prices, categories, expansions
- **Features**:
  - SHA-256 change detection (skip unchanged files)
  - Load history tracking
  - Product-to-card mapping with confidence scoring
  - Ignored products filtering

---

## 7. API & Routing

### 7.1 Blueprints

| Blueprint | URL Prefix | File |
|-----------|-----------|------|
| `main` | `/onepiecetcg/` | `routes/routes.py` |
| `auth` | `/onepiecetcg/` | `routes/auth.py` |
| `sets` | `/onepiecetcg/sets` | `routes/domains/sets.py` |
| `cards` | `/onepiecetcg/cards` | `routes/domains/cards.py` |
| `collection` | `/onepiecetcg/collection` | `routes/domains/collection.py` |
| `deck` | `/onepiecetcg/decks` | `routes/domains/deck.py` |
| `price` | `/onepiecetcg/price` | `routes/domains/price.py` |
| `profile` | `/onepiecetcg/profile` | `routes/domains/profile.py` |

### 7.2 Validation
- All POST endpoints use `@validate_json(Schema)` decorator
- Validated data accessed via `request.validated_data`
- Schemas defined in `app/schemas/` using Pydantic

### 7.3 Response Format
```json
{
  "success": true,
  "data": { ... }
}
```

---

## 8. Testing

### 8.1 Test Stack
- **Runner**: pytest
- **Coverage**: pytest-cov (`--cov=app`)
- **Flask**: pytest-flask
- **Command**: `pytest -vv --tb=long --cov=app`

### 8.2 Test Files

| File | Coverage |
|------|----------|
| `test_app_factory.py` | Flask factory / blueprint registration |
| `test_config.py` | Configuration loading |
| `test_errors.py` | Error handlers |
| `test_models.py` | SQLAlchemy models |
| `test_routes_auth.py` | Authentication routes |
| `test_routes_domains.py` | Domain blueprint routes |
| `test_routes_main.py` | Main/dashboard routes |
| `test_schemas_cards.py` | Pydantic card schemas |
| `test_validators.py` | Custom validators |
| `test_price.py` | Price/cardmarket logic |

### 8.3 TDD Mode
- **Strict TDD**: enabled
- Test-first development for all changes
- RED → GREEN → REFACTOR per task

---

## 9. Deployment

### 9.1 Development
```bash
source .venv/bin/activate
python run.py
# → http://192.168.1.40:5001/onepiecetcg/
```

### 9.2 Production
- **WSGI**: `wsgi.py` with Gunicorn
- **Reverse Proxy**: NGINX with `X-Forwarded-*` headers
- **Database**: PostgreSQL with `onepiecetcg` schema
- **Migrations**: Run `migrations/001_init.sql` to create schema and tables

### 9.3 Environment Variables
| Variable | Purpose | Default |
|----------|---------|---------|
| `SECRET_KEY` | Flask secret key | `you-will-never-guess` |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql+psycopg://postgres:abcd1234@192.168.1.33:5432/postgres` |

---

## 10. UI/UX

### 10.1 Theme
- **Style**: Dark theme (navy/black base, red accent, gold highlights)
- **Background**: Custom image (`static/images/background.jpg`)
- **Framework**: Vanilla CSS (no Bootstrap/Tailwind)

### 10.2 Key Pages
- Login / Register
- Dashboard
- Sets list / Set detail
- Cards list (with filters, sorting, views)
- Card detail
- Collection manager
- Deck builder / Deck list
- Price tables / Cardmarket data
- User profile

---

## 11. Data Flows

### 11.1 Card Scraping Flow
```
User clicks "Extraer Cartas One Piece"
    → onepiece_scraper.fetch_set_list()
    → BeautifulSoup parses HTML
    → Extract card data + image URLs
    → Insert/Update opcards + opsets
    → Download images → static/images/cards/<set>/
    → Return summary
```

### 11.2 Cardmarket Load Flow
```
User triggers "Cardmarket Data Tables"
    → cardmarket_loader.run()
    → Download 3 JSON files (price_guide, singles, nonsingles)
    → SHA-256 hash check (skip if unchanged)
    → Parse and insert into opcm_* tables
    → Log to opcm_load_history
    → Return load report
```

### 11.3 Product-to-Card Mapping Flow
```
User browses unmatched Cardmarket products
    → Display products without oppcm_opset_id/opcar_id mapping
    → User selects internal card
    → Insert/update opcm_product_card_map
    → Future price lookups use mapping
```

---

## 12. Key Conventions & Rules

### 12.1 Code Conventions
- **Models**: Class name `OpXxx`, table `opxxxs`, columns `opxxx_field_name`
- **Blueprints**: `xxx_bp` naming, file `xxx.py`
- **Services**: Class-based or module-level functions with logging
- **Tests**: `test_*.py` naming, descriptive test names

### 12.2 Database Conventions
- PostgreSQL schema: `onepiecetcg`
- SQLite test shim: auto-attaches `:memory:` as `onepiecetcg`
- Custom SQLite function: `regexp_replace()` for PostgreSQL compatibility

### 12.3 Card Naming
- **Card ID format**: `<SET>-<NUMBER>` (e.g., `OP01-001`, `EB04-001`)
- **Set ID format**: `<PREFIX>-<NUMBER>` (e.g., `OP-01`, `EB-04`, `ST-01`)
- **Image folders**: lowercase set prefix (e.g., `op01/`, `eb04/`)
- **Variants**: `_p1`, `_p2` suffix in image filename

---

## 13. Changelog

| Date | Change | Commit |
|------|--------|--------|
| 2026-05-04 | Initial setup complete — 66 files, 161 tests passing | — |
| 2026-05-05 | Price lookup fixes, product-to-card mapping improvements | `c7f3cde` |
| 2026-05-06 | Cardmarket price display in cards tab | `5c6b996` |
| 2026-05-06 | Cards advanced features: filters, views, slider, manual add | `5ae5720` |
| 2026-05-07 | Cards page bug fixes + color/category/rarity buttons, sort, filters | `c8526c7` |

---

## 14. Future Work (Roadmap)

- [ ] Automated scheduled Cardmarket price updates
- [ ] Advanced deck statistics and export
- [ ] Trade/sale listing between users
- [ ] Mobile-responsive UI improvements
- [ ] Multi-language support

---

*Generated from project source + Engram persistent memory.*
