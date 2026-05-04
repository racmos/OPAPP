-- =============================================
-- ESTRUCTURA DE BASE DE DATOS - ONE PIECE TCG MANAGER (OPAPP)
-- Base de datos: postgres
-- Esquema: onepiecetcg
-- =============================================

-- =============================================
-- TABLA: opusers (Usuarios)
-- Compatible con modelo app/models/user.py
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opusers CASCADE;

CREATE TABLE onepiecetcg.opusers (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(256),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_opusers_username ON onepiecetcg.opusers (username);
CREATE INDEX idx_opusers_email ON onepiecetcg.opusers (email);

COMMENT ON TABLE onepiecetcg.opusers IS 'Usuarios registrados en la aplicacion';
COMMENT ON COLUMN onepiecetcg.opusers.id IS 'Identificador unico del usuario';
COMMENT ON COLUMN onepiecetcg.opusers.username IS 'Nombre de usuario unico';
COMMENT ON COLUMN onepiecetcg.opusers.email IS 'Correo electronico unico';
COMMENT ON COLUMN onepiecetcg.opusers.password_hash IS 'Hash de la contrasena';
COMMENT ON COLUMN onepiecetcg.opusers.created_at IS 'Fecha de creacion del usuario';

-- =============================================
-- TABLA: opsets (Sets de cartas)
-- Compatible con modelo app/models/set.py
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opsets CASCADE;

CREATE TABLE onepiecetcg.opsets (
    opset_id VARCHAR(20) PRIMARY KEY,
    opset_name VARCHAR(200) NOT NULL,
    opset_ncard SMALLINT,
    opset_outdat DATE
);

COMMENT ON TABLE onepiecetcg.opsets IS 'Sets de expansion de cartas One Piece TCG';
COMMENT ON COLUMN onepiecetcg.opsets.opset_id IS 'Identificador unico del set (codigo)';
COMMENT ON COLUMN onepiecetcg.opsets.opset_name IS 'Nombre completo del set';
COMMENT ON COLUMN onepiecetcg.opsets.opset_ncard IS 'Numero total de cartas en el set';
COMMENT ON COLUMN onepiecetcg.opsets.opset_outdat IS 'Fecha de salida del set';

-- =============================================
-- TABLA: opcards (Cartas)
-- Compatible con modelo app/models/card.py
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcards CASCADE;

CREATE TABLE onepiecetcg.opcards (
    opcar_opset_id VARCHAR(20) NOT NULL REFERENCES onepiecetcg.opsets(opset_id),
    opcar_id VARCHAR(20) NOT NULL,
    opcar_name VARCHAR(200) NOT NULL,
    opcar_category VARCHAR(50),
    opcar_color VARCHAR(50),
    opcar_rarity VARCHAR(20),
    opcar_cost SMALLINT,
    opcar_life SMALLINT,
    opcar_power SMALLINT,
    opcar_counter SMALLINT,
    opcar_attribute TEXT,
    opcar_type TEXT,
    opcar_effect TEXT,
    opcar_block_icon SMALLINT,
    opcar_illustration_type TEXT,
    opcar_artist VARCHAR(100),
    opcar_banned VARCHAR(1) DEFAULT 'N',
    image_url TEXT,
    image TEXT,
    PRIMARY KEY (opcar_opset_id, opcar_id),
    CONSTRAINT fk_opcards_set FOREIGN KEY (opcar_opset_id) REFERENCES onepiecetcg.opsets(opset_id)
);

CREATE INDEX idx_opcards_set_id ON onepiecetcg.opcards (opcar_opset_id);
CREATE INDEX idx_opcards_name ON onepiecetcg.opcards (opcar_name);

COMMENT ON TABLE onepiecetcg.opcards IS 'Catalogo de cartas One Piece TCG';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_opset_id IS 'FK al set al que pertenece la carta';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_id IS 'Identificador unico de la carta dentro del set';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_name IS 'Nombre de la carta';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_category IS 'Categoria de carta (Leader, Character, Event, Stage, DON!!)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_color IS 'Color(es) de la carta (Red, Green, Blue, Purple, Black, Yellow)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_rarity IS 'Rareza de la carta (C, UC, R, SR, SEC, L, P)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_cost IS 'Coste DON!! de la carta';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_life IS 'Vida del Leader';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_power IS 'Poder de combate de la carta';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_counter IS 'Valor de counter de la carta';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_attribute IS 'Atributos de la carta (Slash, Strike, Special, Wisdom, Ranged)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_type IS 'Tipos de la carta (Straw Hat Crew, Navy, etc.)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_effect IS 'Texto del efecto de la carta';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_block_icon IS 'Icono de bloqueo (0/1)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_illustration_type IS 'Tipo de ilustracion (Normal, Alternate Art, Parallel, etc.)';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_artist IS 'Artista que creo la ilustracion';
COMMENT ON COLUMN onepiecetcg.opcards.opcar_banned IS 'Si la carta esta baneada (S/N)';
COMMENT ON COLUMN onepiecetcg.opcards.image_url IS 'URL de la imagen de la carta';
COMMENT ON COLUMN onepiecetcg.opcards.image IS 'Nombre del archivo de imagen';

-- =============================================
-- TABLA: opcollection (Coleccion de usuario)
-- Compatible con modelo app/models/collection.py
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcollection CASCADE;

CREATE TABLE onepiecetcg.opcollection (
    opcol_id SERIAL PRIMARY KEY,
    opcol_opset_id VARCHAR(20) NOT NULL,
    opcol_opcar_id VARCHAR(20) NOT NULL,
    opcol_foil VARCHAR(1) DEFAULT 'N',
    opcol_user VARCHAR(80) NOT NULL,
    opcol_quantity VARCHAR(20) NOT NULL,
    opcol_selling VARCHAR(1) DEFAULT 'N',
    opcol_playset INTEGER,
    opcol_sell_price NUMERIC,
    opcol_condition VARCHAR(8),
    opcol_language VARCHAR(40),
    opcol_chadat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_collection_card FOREIGN KEY (opcol_opset_id, opcol_opcar_id) 
        REFERENCES onepiecetcg.opcards(opcar_opset_id, opcar_id),
    CONSTRAINT fk_collection_user FOREIGN KEY (opcol_user) REFERENCES onepiecetcg.opusers(username)
);

CREATE INDEX idx_opcollection_user ON onepiecetcg.opcollection (opcol_user);
CREATE INDEX idx_opcollection_set_card ON onepiecetcg.opcollection (opcol_opset_id, opcol_opcar_id);

COMMENT ON TABLE onepiecetcg.opcollection IS 'Coleccion personal de cada usuario';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_id IS 'Identificador unico autoincremental';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_opset_id IS 'FK al set de la carta';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_opcar_id IS 'FK al ID de la carta';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_foil IS 'Si la carta es foil (S/N)';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_quantity IS 'Cantidad de copias de la carta';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_selling IS 'Si esta en venta (S/N)';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_playset IS 'Cantidad de playset';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_sell_price IS 'Precio de venta';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_condition IS 'Condicion de la carta';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_language IS 'Idioma de la carta';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_chadat IS 'Fecha de ultimo cambio en la coleccion';
COMMENT ON COLUMN onepiecetcg.opcollection.opcol_user IS 'FK al usuario propietario';

-- =============================================
-- TABLA: opdecks (Mazos)
-- Compatible con modelo app/models/deck.py
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opdecks CASCADE;

CREATE TABLE onepiecetcg.opdecks (
    id SERIAL PRIMARY KEY,
    opdck_user VARCHAR(80) NOT NULL,
    opdck_name VARCHAR(200) NOT NULL,
    opdck_seq SMALLINT DEFAULT 1,
    opdck_snapshot TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    opdck_description TEXT,
    opdck_mode VARCHAR(50) DEFAULT '1v1',
    opdck_format VARCHAR(50) DEFAULT 'Standard',
    opdck_max_set VARCHAR(100),
    opdck_ncards INTEGER DEFAULT 0,
    opdck_orden NUMERIC,
    opdck_cards JSONB,
    UNIQUE (opdck_user, opdck_name, opdck_seq),
    CONSTRAINT fk_deck_user FOREIGN KEY (opdck_user) REFERENCES onepiecetcg.opusers(username)
);

CREATE INDEX idx_opdecks_user ON onepiecetcg.opdecks (opdck_user);
CREATE INDEX idx_opdecks_name ON onepiecetcg.opdecks (opdck_name);
CREATE INDEX idx_opdecks_snapshot ON onepiecetcg.opdecks (opdck_snapshot);
CREATE INDEX idx_opdecks_user_name_seq ON onepiecetcg.opdecks (opdck_user, opdck_name, opdck_seq);

COMMENT ON TABLE onepiecetcg.opdecks IS 'Mazos creados por usuarios';
COMMENT ON COLUMN onepiecetcg.opdecks.id IS 'Identificador unico autoincremental del deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_user IS 'FK al usuario propietario del deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_name IS 'Nombre del deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_seq IS 'Secuencial para permitir multiples versiones del mismo deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_snapshot IS 'Fecha/hora de creacion del deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_description IS 'Descripcion del deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_mode IS 'Modo de juego (1v1, Team, etc.)';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_format IS 'Formato del deck (Standard, Expanded)';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_max_set IS 'Sets permitidos en el deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_ncards IS 'Numero total de cartas en el deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_orden IS 'Orden de visualizacion del deck';
COMMENT ON COLUMN onepiecetcg.opdecks.opdck_cards IS 'Cartas del deck en formato JSON: {"main": [...], "sideboard": [...]}';

-- =============================================
-- TABLA: opcm_products (Productos Cardmarket)
-- Compatible con modelo app/models/cardmarket.py -> OpcmProduct
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_products CASCADE;

CREATE TABLE onepiecetcg.opcm_products (
    opprd_date VARCHAR(8) NOT NULL,
    opprd_id_product INTEGER NOT NULL,
    opprd_name TEXT NOT NULL,
    opprd_id_category INTEGER,
    opprd_category_name TEXT,
    opprd_id_expansion INTEGER,
    opprd_id_metacard INTEGER,
    opprd_date_added TEXT,
    opprd_type TEXT NOT NULL,
    PRIMARY KEY (opprd_date, opprd_id_product)
);

COMMENT ON TABLE onepiecetcg.opcm_products IS 'Datos raw de productos Cardmarket por fecha';
COMMENT ON COLUMN onepiecetcg.opcm_products.opprd_date IS 'Fecha en formato YYYYMMDD';
COMMENT ON COLUMN onepiecetcg.opcm_products.opprd_id_product IS 'idProduct de Cardmarket';
COMMENT ON COLUMN onepiecetcg.opcm_products.opprd_name IS 'Nombre del producto';
COMMENT ON COLUMN onepiecetcg.opcm_products.opprd_type IS 'Tipo: single o nonsingle';

-- =============================================
-- TABLA: opcm_price (Precios Cardmarket)
-- Compatible con modelo app/models/cardmarket.py -> OpcmPrice
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_price CASCADE;

CREATE TABLE onepiecetcg.opcm_price (
    opprc_date VARCHAR(8) NOT NULL,
    opprc_id_product INTEGER NOT NULL,
    opprc_id_category INTEGER,
    opprc_avg NUMERIC,
    opprc_low NUMERIC,
    opprc_trend NUMERIC,
    opprc_avg1 NUMERIC,
    opprc_avg7 NUMERIC,
    opprc_avg30 NUMERIC,
    opprc_avg_foil NUMERIC,
    opprc_low_foil NUMERIC,
    opprc_trend_foil NUMERIC,
    opprc_avg1_foil NUMERIC,
    opprc_avg7_foil NUMERIC,
    opprc_avg30_foil NUMERIC,
    opprc_low_ex NUMERIC,
    PRIMARY KEY (opprc_date, opprc_id_product)
);

COMMENT ON TABLE onepiecetcg.opcm_price IS 'Snapshots diarios de precios Cardmarket';
COMMENT ON COLUMN onepiecetcg.opcm_price.opprc_avg IS 'Precio promedio (Sell)';
COMMENT ON COLUMN onepiecetcg.opcm_price.opprc_low IS 'Precio bajo (from)';
COMMENT ON COLUMN onepiecetcg.opcm_price.opprc_trend IS 'Precio de tendencia';
COMMENT ON COLUMN onepiecetcg.opcm_price.opprc_avg_foil IS 'Precio promedio foil';

-- =============================================
-- TABLA: opcm_categories (Categorias Cardmarket)
-- Compatible con modelo app/models/cardmarket.py -> OpcmCategory
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_categories CASCADE;

CREATE TABLE onepiecetcg.opcm_categories (
    opcat_id INTEGER PRIMARY KEY,
    opcat_name TEXT NOT NULL
);

COMMENT ON TABLE onepiecetcg.opcm_categories IS 'Tabla de lookup de categorias Cardmarket';

-- =============================================
-- TABLA: opcm_expansions (Expansiones Cardmarket)
-- Compatible con modelo app/models/cardmarket.py -> OpcmExpansion
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_expansions CASCADE;

CREATE TABLE onepiecetcg.opcm_expansions (
    opexp_id INTEGER PRIMARY KEY,
    opexp_name TEXT,
    opexp_opset_id TEXT
);

COMMENT ON TABLE onepiecetcg.opcm_expansions IS 'Tabla de lookup de expansiones Cardmarket';
COMMENT ON COLUMN onepiecetcg.opcm_expansions.opexp_opset_id IS 'FK al set interno (opsets). NULL = no mapeada aun';

-- =============================================
-- TABLA: opcm_load_history (Historial de cargas)
-- Compatible con modelo app/models/cardmarket.py -> OpcmLoadHistory
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_load_history CASCADE;

CREATE TABLE onepiecetcg.opcm_load_history (
    oplh_id SERIAL PRIMARY KEY,
    oplh_date VARCHAR(8) NOT NULL,
    oplh_file_type TEXT NOT NULL,
    oplh_hash TEXT NOT NULL,
    oplh_rows INTEGER,
    oplh_status TEXT DEFAULT 'success',
    oplh_message TEXT,
    oplh_loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE onepiecetcg.opcm_load_history IS 'Registro de cada operacion de carga Cardmarket';
COMMENT ON COLUMN onepiecetcg.opcm_load_history.oplh_hash IS 'Hash SHA-256 del contenido cargado';
COMMENT ON COLUMN onepiecetcg.opcm_load_history.oplh_status IS 'success | error | skipped';
COMMENT ON COLUMN onepiecetcg.opcm_load_history.oplh_file_type IS 'singles | nonsingles | price_guide';

-- =============================================
-- TABLA: opcm_product_card_map (Mapeo productos -> cartas)
-- Compatible con modelo app/models/cardmarket.py -> OpcmProductCardMap
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_product_card_map CASCADE;

CREATE TABLE onepiecetcg.opcm_product_card_map (
    oppcm_id_product INTEGER PRIMARY KEY,
    oppcm_opset_id TEXT NOT NULL,
    oppcm_opcar_id TEXT NOT NULL,
    oppcm_foil VARCHAR(1),
    oppcm_match_type TEXT DEFAULT 'manual',
    oppcm_confidence NUMERIC
);

COMMENT ON TABLE onepiecetcg.opcm_product_card_map IS 'Mapea idProduct Cardmarket a cartas internas';
COMMENT ON COLUMN onepiecetcg.opcm_product_card_map.oppcm_foil IS 'N=normal, S=foil, NULL=sin foil fisico';
COMMENT ON COLUMN onepiecetcg.opcm_product_card_map.oppcm_match_type IS 'auto | manual';

-- =============================================
-- TABLA: opcm_ignored (Productos ignorados)
-- Compatible con modelo app/models/cardmarket.py -> OpcmIgnored
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opcm_ignored CASCADE;

CREATE TABLE onepiecetcg.opcm_ignored (
    opig_id_product INTEGER NOT NULL,
    opig_name TEXT NOT NULL,
    opig_ignored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (opig_id_product, opig_name)
);

COMMENT ON TABLE onepiecetcg.opcm_ignored IS 'Productos explicitamente ignorados por el usuario';

-- =============================================
-- TABLA: opproducts (Productos curados)
-- Compatible con modelo app/models/cardmarket.py -> OpProducts
-- =============================================
DROP TABLE IF EXISTS onepiecetcg.opproducts CASCADE;

CREATE TABLE onepiecetcg.opproducts (
    oppdt_id_set TEXT NOT NULL,
    oppdt_id_product INTEGER NOT NULL,
    oppdt_name TEXT NOT NULL,
    oppdt_description TEXT,
    oppdt_type TEXT,
    oppdt_image_url TEXT,
    oppdt_image TEXT,
    PRIMARY KEY (oppdt_id_set, oppdt_id_product)
);

COMMENT ON TABLE onepiecetcg.opproducts IS 'Tabla maestra de productos curados (uso futuro)';

-- =============================================
-- SEED DATA: Sets de One Piece TCG
-- =============================================
INSERT INTO onepiecetcg.opsets (opset_id, opset_name, opset_ncard) VALUES
    ('PRB-01', 'Premium Booster -The Best-', 80),
    ('OP-01', 'Romance Dawn', 121),
    ('OP-02', 'Paramount War', 121),
    ('OP-03', 'Pillars of Strength', 127),
    ('OP-04', 'Kingdoms of Intrigue', 127),
    ('OP-05', 'Awakening of the New Era', 128),
    ('OP-06', 'Wings of the Captain', 125),
    ('OP-07', '500 Years in the Future', 126),
    ('OP-08', 'Two Legends', 126),
    ('OP-09', 'Emperors in the New World', 126),
    ('OP-10', 'Royal Blood', 126),
    ('OP-11', 'A Fist of Divine Speed', 126),
    ('OP-12', 'Eclipse of the Golden Dawn', 126),
    ('OP-13', 'The Three Brothers'' Bond', 126),
    ('OP-14', 'The Best #2', 126),
    ('OP-15', 'A New World Dawn', 126),
    ('ST-01', 'Straw Hat Crew', 17),
    ('ST-02', 'Worst Generation', 17),
    ('ST-03', 'The Seven Warlords of the Sea', 17),
    ('ST-04', 'Animal Kingdom Pirates', 17),
    ('ST-05', 'Film Edition', 17),
    ('ST-06', 'Navy', 17),
    ('ST-07', 'Big Mom Pirates', 17),
    ('ST-08', 'Monkey D. Luffy', 17),
    ('ST-09', 'Yamato', 17),
    ('ST-10', 'The Three Captains', 17),
    ('ST-11', 'Uta', 17),
    ('ST-12', 'Zoro & Sanji', 17),
    ('ST-13', 'The Three Brothers', 17),
    ('ST-14', 'Trafalgar Law', 17),
    ('ST-15', 'Edward Newgate', 17),
    ('ST-16', 'The Seven Warlords 2', 17),
    ('ST-17', 'Donquixote Pirates', 17),
    ('ST-18', 'Monkey D. Luffy (2)', 17),
    ('ST-19', 'Boa Hancock', 17),
    ('ST-20', 'Charlotte Katakuri', 17),
    ('ST-21', 'Captain Kid', 17),
    ('ST-22', 'Akazaya Nine', 17),
    ('ST-23', 'Donquixote Doflamingo', 17),
    ('ST-24', 'Crocodile', 17),
    ('ST-25', 'Rob Lucci', 17),
    ('ST-26', 'Portgas D. Ace', 17),
    ('ST-27', 'Gecko Moria', 17),
    ('ST-28', 'Kuro', 17),
    ('ST-29', 'Bartholomew Kuma', 17),
    ('EB-01', 'Memorial Collection', 62),
    ('EB-02', 'Anime 25th Collection', 62),
    ('EB-03', 'Anime 25th Collection Vol.2', 62),
    ('EB-04', 'Premium Card Collection 25th Edition', 62),
    ('P', 'Promo Cards', 0),
    ('Other', 'Other / Miscellaneous', 0)
ON CONFLICT (opset_id) DO NOTHING;
