from flask import Blueprint, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from pydantic import ValidationError

from app import db, limiter
from app.models import OpUser
from app.schemas.validators import LoginSchema, RegisterSchema

auth_bp = Blueprint('auth', __name__, url_prefix='/onepiecetcg')


@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('login.html')

    # POST — validate JSON body with Pydantic
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Content-Type must be application/json'}), 400

    try:
        data = LoginSchema(**request.get_json())
    except ValidationError as e:
        return jsonify({'success': False, 'message': 'Invalid request data', 'details': str(e)}), 400

    user = OpUser.query.filter_by(email=data.email).first()
    if user is None or not user.check_password(data.password):
        return jsonify({'success': False, 'message': 'Invalid email or password'}), 401

    login_user(user)
    return jsonify({'success': True, 'redirect': url_for('main.dashboard')}), 200


@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('10 per minute', methods=['POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    if request.method == 'GET':
        return render_template('register.html')

    # POST — validate JSON body with Pydantic
    if not request.is_json:
        return jsonify({'success': False, 'message': 'Content-Type must be application/json'}), 400

    try:
        data = RegisterSchema(**request.get_json())
    except ValidationError as e:
        return jsonify({'success': False, 'message': 'Invalid request data', 'details': str(e)}), 400

    if OpUser.query.filter_by(username=data.username).first():
        return jsonify({'success': False, 'message': 'Username already exists'}), 400

    if OpUser.query.filter_by(email=data.email).first():
        return jsonify({'success': False, 'message': 'Email already registered'}), 400

    user = OpUser(username=data.username, email=data.email)
    user.set_password(data.password)
    db.session.add(user)
    db.session.commit()

    return jsonify(
        {'success': True, 'message': 'Registration successful! Please login.', 'redirect': url_for('auth.login')}
    ), 200


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
