"""
Profile routes module with Pydantic validation.
"""

from flask import Blueprint, render_template
from flask_login import current_user, login_required

profile_bp = Blueprint('profile', __name__, url_prefix='/onepiecetcg/profile')


class ProfileUpdateSchema:
    """Minimal schema for profile update — will be expanded in Phase 3."""

    pass


@profile_bp.route('')
@login_required
def profile():
    """User profile page."""
    return render_template('profile.html', user=current_user)
