"""
Profile routes module with Pydantic validation.
"""

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app import db
from app.schemas.validators import ProfileUpdateSchema, validate_json

profile_bp = Blueprint('profile', __name__, url_prefix='/onepiecetcg/profile')


@profile_bp.route('')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html', user=current_user)


@profile_bp.route('/update', methods=['POST'])
@login_required
@validate_json(ProfileUpdateSchema)
def update_profile():
    """Update user email and/or password."""
    data = request.validated_data

    if not current_user.check_password(data.current_password):
        return jsonify({'success': False, 'message': 'Invalid current password'}), 403

    if data.email:
        current_user.email = data.email
    if data.new_password:
        current_user.set_password(data.new_password)

    db.session.commit()

    return jsonify({'success': True, 'message': 'Profile updated successfully'})
