from app import db


def _image_folder(image_filename):
    """Extract the set folder from the image filename.

    Image filenames follow patterns like:
      - OP01-001.png      (dash-separated card ID)
      - EB04-001_p1.jpg   (variant suffix)
      - p_001.png          (underscore-separated, RBAPP legacy)

    Returns the lowercase set prefix used as the folder name.
    """
    if not image_filename:
        return ''
    import re
    # Strip known variant suffixes (_p1, _p2, _p3) before processing
    base = re.sub(r'_p\d+(?=\.)', '', image_filename)
    # Try dash-separated One Piece convention: OP01-001.png → OP01
    name_no_ext = base.rsplit('.', 1)[0] if '.' in base else base
    if '-' in name_no_ext:
        set_prefix = name_no_ext.split('-', 1)[0]
        return set_prefix.lower()
    # Fallback: underscore-separated RBAPP legacy convention
    parts = name_no_ext.rsplit('_', 1)
    return parts[0].lower() if len(parts) == 2 else name_no_ext.lower()


class OpCard(db.Model):
    __tablename__ = 'opcards'
    __table_args__ = {"schema": "onepiecetcg"}

    opcar_opset_id = db.Column(db.Text, primary_key=True)
    opcar_id = db.Column(db.Text, primary_key=True)
    opcar_version = db.Column(db.Text, primary_key=True, default='p0')
    opcar_name = db.Column(db.Text, nullable=False)
    opcar_category = db.Column(db.Text)
    opcar_color = db.Column(db.Text)
    opcar_rarity = db.Column(db.Text)
    opcar_cost = db.Column(db.SmallInteger)
    opcar_life = db.Column(db.SmallInteger)
    opcar_power = db.Column(db.SmallInteger)
    opcar_counter = db.Column(db.SmallInteger)
    opcar_attribute = db.Column(db.Text)
    opcar_type = db.Column(db.Text)
    opcar_effect = db.Column(db.Text)
    opcar_block_icon = db.Column(db.SmallInteger)
    opcar_banned = db.Column(db.Text)
    image_url = db.Column(db.Text)
    image = db.Column(db.Text)

    def __init__(self, **kwargs):
        kwargs.setdefault('opcar_version', 'p0')
        super().__init__(**kwargs)

    @property
    def image_src(self):
        """Full image URL path derived from selected set ownership folder."""
        if not self.image:
            return None
        folder = (self.opcar_opset_id or '').lower()
        return f"/onepiecetcg/static/images/cards/{folder}/{self.image}"
