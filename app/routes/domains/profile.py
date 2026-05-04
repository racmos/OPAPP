"""
Profile routes module with Pydantic validation.
"""
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from pydantic import ValidationError
from app import db
from app.schemas.validators import validate_json

profile_bp = Blueprint('profile', __name__, url_prefix='/onepiecetcg/profile')


class ProfileUpdateSchema:
    """Minimal schema for profile update — will be expanded in Phase 3."""
    pass


@profile_bp.route('')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html', user=current_user)
