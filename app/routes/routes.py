"""
Main routes module — dashboard and root redirect.
"""

from flask import Blueprint, render_template
from flask_login import login_required

main_bp = Blueprint('main', __name__, url_prefix='/onepiecetcg')


@main_bp.route('/')
@login_required
def dashboard():
    """Main dashboard page."""
    return render_template('dashboard.html')


@main_bp.route('/dashboard')
@login_required
def dashboard_alt():
    """Dashboard at /dashboard URL."""
    return render_template('dashboard.html')
