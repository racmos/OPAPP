"""
Sets routes module with Pydantic validation.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
from app import db
from app.models import OpSet
from app.schemas.validators import SetCreate, SetUpdate, validate_json

sets_bp = Blueprint('sets', __name__, url_prefix='/onepiecetcg/sets')


@sets_bp.route('')
@login_required
def sets():
    """List all sets with search."""
    search_id = request.args.get('search_id', '')
    search_name = request.args.get('search_name', '')

    query = OpSet.query
    if search_id:
        query = query.filter(OpSet.opset_id.ilike(f'%{search_id}%'))
    if search_name:
        query = query.filter(OpSet.opset_name.ilike(f'%{search_name}%'))

    sets_list = query.order_by(OpSet.opset_id).all()
    return render_template('sets.html', sets=sets_list)


@sets_bp.route('/add', methods=['POST'])
@login_required
@validate_json(SetCreate)
def add_set():
    """Add a new set."""
    data = request.validated_data

    if OpSet.query.filter_by(opset_id=data.opset_id).first():
        return jsonify({'success': False, 'message': 'Set ID already exists'}), 400

    if OpSet.query.filter_by(opset_name=data.opset_name).first():
        return jsonify({'success': False, 'message': 'Set name already exists'}), 400

    from datetime import date as date_type
    outdat = None
    if data.opset_outdat:
        try:
            outdat = date_type.fromisoformat(data.opset_outdat)
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid date format (use YYYY-MM-DD)'}), 400

    new_set = OpSet(
        opset_id=data.opset_id,
        opset_name=data.opset_name,
        opset_ncard=data.opset_ncard,
        opset_outdat=outdat
    )

    db.session.add(new_set)
    db.session.commit()

    return jsonify({'success': True})


@sets_bp.route('/update/<set_id>', methods=['POST'])
@login_required
@validate_json(SetUpdate)
def update_set(set_id):
    """Update an existing set."""
    data = request.validated_data
    opset = OpSet.query.filter_by(opset_id=set_id).first_or_404()

    if data.opset_name is not None:
        existing = OpSet.query.filter(
            OpSet.opset_name == data.opset_name,
            OpSet.opset_id != set_id
        ).first()
        if existing:
            return jsonify({'success': False, 'message': 'Set name already exists'}), 400
        opset.opset_name = data.opset_name

    if data.opset_ncard is not None:
        opset.opset_ncard = data.opset_ncard

    if data.opset_outdat is not None:
        from datetime import date as date_type
        try:
            opset.opset_outdat = date_type.fromisoformat(data.opset_outdat) if data.opset_outdat else None
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': 'Invalid date format (use YYYY-MM-DD)'}), 400

    db.session.commit()

    return jsonify({'success': True})
