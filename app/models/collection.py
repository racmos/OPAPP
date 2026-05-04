from app import db
from datetime import datetime


class OpCollection(db.Model):
    __tablename__ = 'opcollection'
    __table_args__ = {"schema": "onepiecetcg"}

    # Synthetic PK. Allows multiple rows for the same (set, card, foil, user)
    # that differ in condition / language / sell price.
    opcol_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    opcol_opset_id = db.Column(db.Text, nullable=False)
    opcol_opcar_id = db.Column(db.Text, nullable=False)
    opcol_foil = db.Column(db.Text, nullable=False, default='N')
    opcol_user = db.Column(db.String(64), nullable=False)
    opcol_quantity = db.Column(db.Text, nullable=False)
    opcol_selling = db.Column(db.Text, default='N')
    opcol_playset = db.Column(db.Integer, nullable=True)
    opcol_sell_price = db.Column(db.Numeric, nullable=True)
    opcol_condition = db.Column(db.String(8), nullable=True)
    opcol_language = db.Column(db.String(40), nullable=True)
    opcol_chadat = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
