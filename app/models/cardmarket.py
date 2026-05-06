from datetime import datetime

from app import db


class OpcmProduct(db.Model):
    """Raw Cardmarket product data per date."""

    __tablename__ = 'opcm_products'
    __table_args__ = {'schema': 'onepiecetcg'}

    opprd_date = db.Column(db.Text, primary_key=True)  # YYYYMMDD
    opprd_id_product = db.Column(db.Integer, primary_key=True)  # idProduct from Cardmarket
    opprd_name = db.Column(db.Text, nullable=False)
    opprd_id_category = db.Column(db.Integer)
    opprd_category_name = db.Column(db.Text)
    opprd_id_expansion = db.Column(db.Integer)
    opprd_id_metacard = db.Column(db.Integer)
    opprd_date_added = db.Column(db.Text)  # from JSON
    opprd_type = db.Column(db.Text, nullable=False)  # 'single' | 'nonsingle'


class OpcmPrice(db.Model):
    """Daily price snapshots from Cardmarket."""

    __tablename__ = 'opcm_price'
    __table_args__ = {'schema': 'onepiecetcg'}

    opprc_date = db.Column(db.Text, primary_key=True)  # YYYYMMDD
    opprc_id_product = db.Column(db.Integer, primary_key=True)
    opprc_id_category = db.Column(db.Integer)
    opprc_avg = db.Column(db.Numeric)
    opprc_low = db.Column(db.Numeric)
    opprc_trend = db.Column(db.Numeric)
    opprc_avg1 = db.Column(db.Numeric)
    opprc_avg7 = db.Column(db.Numeric)
    opprc_avg30 = db.Column(db.Numeric)
    opprc_avg_foil = db.Column(db.Numeric)
    opprc_low_foil = db.Column(db.Numeric)
    opprc_trend_foil = db.Column(db.Numeric)
    opprc_avg1_foil = db.Column(db.Numeric)
    opprc_avg7_foil = db.Column(db.Numeric)
    opprc_avg30_foil = db.Column(db.Numeric)
    opprc_low_ex = db.Column(db.Numeric)  # low ex+ price tier


class OpcmCategory(db.Model):
    """Category lookup table."""

    __tablename__ = 'opcm_categories'
    __table_args__ = {'schema': 'onepiecetcg'}

    opcat_id = db.Column(db.Integer, primary_key=True)
    opcat_name = db.Column(db.Text, nullable=False)


class OpcmExpansion(db.Model):
    """Expansion lookup table.

    `opexp_opset_id` links the Cardmarket expansion to the internal set (opsets).
    NULL means not yet mapped — the UI detects this when loading
    data tables and prompts for the internal set equivalent.
    """

    __tablename__ = 'opcm_expansions'
    __table_args__ = {'schema': 'onepiecetcg'}

    opexp_id = db.Column(db.Integer, primary_key=True)
    opexp_name = db.Column(db.Text)
    opexp_opset_id = db.Column(db.Text, nullable=True)


class OpcmLoadHistory(db.Model):
    """Tracks each load operation for date validation and change detection."""

    __tablename__ = 'opcm_load_history'
    __table_args__ = {'schema': 'onepiecetcg'}

    oplh_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    oplh_date = db.Column(db.Text, nullable=False)  # YYYYMMDD
    oplh_file_type = db.Column(db.Text, nullable=False)  # 'singles' | 'nonsingles' | 'price_guide'
    oplh_hash = db.Column(db.Text, nullable=False)  # SHA-256
    oplh_rows = db.Column(db.Integer)
    oplh_status = db.Column(db.Text, default='success')  # success | error | skipped
    oplh_message = db.Column(db.Text)
    oplh_loaded_at = db.Column(db.DateTime, default=datetime.utcnow)


class OpcmProductCardMap(db.Model):
    """Maps Cardmarket idProduct to internal opcards.

    `oppcm_foil` distinguishes whether this idProduct represents the normal or
    foil version of the card. For cards without physical foil it is NULL.
    """

    __tablename__ = 'opcm_product_card_map'
    __table_args__ = {'schema': 'onepiecetcg'}

    oppcm_id_product = db.Column(db.Integer, primary_key=True)
    oppcm_opset_id = db.Column(db.Text, nullable=False)
    oppcm_opcar_id = db.Column(db.Text, nullable=False)
    oppcm_opcar_version = db.Column(db.Text, nullable=False, default='p0')
    oppcm_foil = db.Column(db.String(1), nullable=True)  # 'N' | 'S' | NULL
    oppcm_match_type = db.Column(db.Text, default='manual')  # auto | manual
    oppcm_confidence = db.Column(db.Numeric)


class OpcmIgnored(db.Model):
    """Products explicitly ignored by the user in the mappings browser.

    Identified by (idProduct, name) composite PK so that two products
    sharing the same idProduct but different names are tracked separately.
    """

    __tablename__ = 'opcm_ignored'
    __table_args__ = {'schema': 'onepiecetcg'}

    opig_id_product = db.Column(db.Integer, primary_key=True)
    opig_name = db.Column(db.Text, primary_key=True)
    opig_ignored_at = db.Column(db.DateTime, default=db.func.now())


class OpProducts(db.Model):
    """Curated product master table (future use)."""

    __tablename__ = 'opproducts'
    __table_args__ = {'schema': 'onepiecetcg'}

    oppdt_id_set = db.Column(db.Text, primary_key=True)
    oppdt_id_product = db.Column(db.Integer, primary_key=True)
    oppdt_name = db.Column(db.Text, nullable=False)
    oppdt_description = db.Column(db.Text)
    oppdt_type = db.Column(db.Text)  # single | nonsingle
    oppdt_image_url = db.Column(db.Text)
    oppdt_image = db.Column(db.Text)
