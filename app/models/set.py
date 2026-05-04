from app import db


class OpSet(db.Model):
    __tablename__ = 'opsets'
    __table_args__ = {"schema": "onepiecetcg"}

    opset_id = db.Column(db.Text, primary_key=True)
    opset_name = db.Column(db.Text, nullable=False)
    opset_ncard = db.Column(db.SmallInteger)
    opset_outdat = db.Column(db.Date)
