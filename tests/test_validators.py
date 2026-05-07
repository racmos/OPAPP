"""
Tests for Pydantic schemas and @validate_json decorator.
"""

import json

import pytest
from flask import Flask, jsonify
from pydantic import ValidationError

from app.schemas.validators import LoginSchema, RegisterSchema, validate_json


class TestLoginSchema:
    """Unit tests for LoginSchema."""

    def test_valid_login(self):
        """LoginSchema accepts valid email and password."""
        schema = LoginSchema(email='user@test.com', password='secret123')
        assert schema.email == 'user@test.com'
        assert schema.password == 'secret123'

    def test_missing_email(self):
        """LoginSchema rejects missing email."""
        with pytest.raises(ValidationError):
            LoginSchema(password='secret123')

    def test_missing_password(self):
        """LoginSchema rejects missing password."""
        with pytest.raises(ValidationError):
            LoginSchema(email='user@test.com')

    def test_invalid_email_no_at(self):
        """LoginSchema rejects email without @."""
        with pytest.raises(ValidationError):
            LoginSchema(email='notanemail', password='secret123')

    def test_empty_password(self):
        """LoginSchema rejects empty password."""
        with pytest.raises(ValidationError):
            LoginSchema(email='user@test.com', password='')

    def test_strips_email_whitespace(self):
        """LoginSchema strips whitespace from email."""
        schema = LoginSchema(email='  user@test.com  ', password='secret123')
        assert schema.email == 'user@test.com'


class TestRegisterSchema:
    """Unit tests for RegisterSchema."""

    def test_valid_register(self):
        """RegisterSchema accepts valid data."""
        schema = RegisterSchema(username='newuser', email='new@test.com', password='secret123')
        assert schema.username == 'newuser'
        assert schema.email == 'new@test.com'
        assert schema.password == 'secret123'

    def test_missing_username(self):
        """RegisterSchema rejects missing username."""
        with pytest.raises(ValidationError):
            RegisterSchema(email='new@test.com', password='secret123')

    def test_missing_email(self):
        """RegisterSchema rejects missing email."""
        with pytest.raises(ValidationError):
            RegisterSchema(username='newuser', password='secret123')

    def test_missing_password(self):
        """RegisterSchema rejects missing password."""
        with pytest.raises(ValidationError):
            RegisterSchema(username='newuser', email='new@test.com')

    def test_short_password(self):
        """RegisterSchema rejects password shorter than 6 chars."""
        with pytest.raises(ValidationError):
            RegisterSchema(username='newuser', email='new@test.com', password='12345')

    def test_empty_username(self):
        """RegisterSchema rejects empty username."""
        with pytest.raises(ValidationError):
            RegisterSchema(username='', email='new@test.com', password='secret123')

    def test_invalid_email_no_at(self):
        """RegisterSchema rejects email without @."""
        with pytest.raises(ValidationError):
            RegisterSchema(username='newuser', email='notanemail', password='secret123')

    def test_strips_username_whitespace(self):
        """RegisterSchema strips whitespace from username and email."""
        schema = RegisterSchema(username='  newuser  ', email='  new@test.com  ', password='secret123')
        assert schema.username == 'newuser'
        assert schema.email == 'new@test.com'


class TestProfileUpdateSchema:
    """Unit tests for ProfileUpdateSchema."""

    def test_valid_email_only(self):
        """Accepts current_password + email."""
        from app.schemas.validators import ProfileUpdateSchema

        schema = ProfileUpdateSchema(current_password='pass1234', email='test@example.com')
        assert schema.current_password == 'pass1234'
        assert schema.email == 'test@example.com'
        assert schema.new_password is None

    def test_valid_password_only(self):
        """Accepts current_password + new_password."""
        from app.schemas.validators import ProfileUpdateSchema

        schema = ProfileUpdateSchema(current_password='pass1234', new_password='newpass1234')
        assert schema.new_password == 'newpass1234'
        assert schema.email is None

    def test_valid_both_fields(self):
        """Accepts current_password + email + new_password."""
        from app.schemas.validators import ProfileUpdateSchema

        schema = ProfileUpdateSchema(current_password='pass1234', email='test@example.com', new_password='newpass1234')
        assert schema.email == 'test@example.com'
        assert schema.new_password == 'newpass1234'

    def test_rejects_missing_current_password(self):
        """Rejects when current_password is missing."""
        from app.schemas.validators import ProfileUpdateSchema

        with pytest.raises(ValidationError):
            ProfileUpdateSchema(email='test@example.com')

    def test_rejects_no_changes(self):
        """Rejects when only current_password is provided."""
        from app.schemas.validators import ProfileUpdateSchema

        with pytest.raises(ValidationError) as exc_info:
            ProfileUpdateSchema(current_password='pass1234')
        assert 'at least one' in str(exc_info.value).lower() or 'email' in str(exc_info.value).lower()

    def test_rejects_invalid_email(self):
        """Rejects invalid email format."""
        from app.schemas.validators import ProfileUpdateSchema

        with pytest.raises(ValidationError):
            ProfileUpdateSchema(current_password='pass1234', email='not-an-email')

    def test_rejects_short_current_password(self):
        """Rejects current_password shorter than 6 chars."""
        from app.schemas.validators import ProfileUpdateSchema

        with pytest.raises(ValidationError):
            ProfileUpdateSchema(current_password='short', email='test@example.com')

    def test_rejects_short_new_password(self):
        """Rejects new_password shorter than 6 chars."""
        from app.schemas.validators import ProfileUpdateSchema

        with pytest.raises(ValidationError):
            ProfileUpdateSchema(current_password='pass1234', new_password='short')


class TestDeckCardAction:
    """Unit tests for DeckCardAction schema."""

    def test_valid_payload(self):
        """Accepts valid add payload."""
        from app.schemas.validators import DeckCardAction

        schema = DeckCardAction(set_id='OP01', card_id='001', section='main', quantity=2)
        assert schema.set_id == 'OP01'
        assert schema.card_id == '001'
        assert schema.section == 'main'
        assert schema.quantity == 2

    def test_valid_sideboard(self):
        """Accepts sideboard section."""
        from app.schemas.validators import DeckCardAction

        schema = DeckCardAction(set_id='OP01', card_id='001', section='sideboard')
        assert schema.section == 'sideboard'
        assert schema.quantity == 1  # default

    def test_invalid_section(self):
        """Rejects invalid section value."""
        from app.schemas.validators import DeckCardAction

        with pytest.raises(ValidationError):
            DeckCardAction(set_id='OP01', card_id='001', section='extra')

    def test_zero_quantity(self):
        """Rejects zero quantity."""
        from app.schemas.validators import DeckCardAction

        with pytest.raises(ValidationError):
            DeckCardAction(set_id='OP01', card_id='001', section='main', quantity=0)

    def test_missing_set_id(self):
        """Rejects missing set_id."""
        from app.schemas.validators import DeckCardAction

        with pytest.raises(ValidationError):
            DeckCardAction(card_id='001', section='main')

    def test_missing_card_id(self):
        """Rejects missing card_id."""
        from app.schemas.validators import DeckCardAction

        with pytest.raises(ValidationError):
            DeckCardAction(set_id='OP01', section='main')


class TestValidateJsonDecorator:
    """Integration tests for @validate_json decorator with a mini Flask app."""

    @pytest.fixture
    def mini_app(self):
        """Create a minimal Flask app with a test endpoint using @validate_json."""
        app = Flask(__name__)

        class TestRequestSchema(LoginSchema):
            pass

        @app.route('/test-json', methods=['POST'])
        @validate_json(TestRequestSchema)
        def test_endpoint():
            data = getattr(LoginSchema, '__test_data__', None)
            # Use request.validated_data set by the decorator
            from flask import request

            return jsonify(
                {
                    'success': True,
                    'email': request.validated_data.email,
                }
            )

        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def mini_client(self, mini_app):
        """Create a test client for the mini app."""
        return mini_app.test_client()

    def test_valid_json_passes_through(self, mini_client):
        """@validate_json passes valid data to the endpoint."""
        response = mini_client.post(
            '/test-json',
            data=json.dumps({'email': 'user@test.com', 'password': 'secret123'}),
            content_type='application/json',
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data['success'] is True
        assert data['email'] == 'user@test.com'

    def test_invalid_json_returns_400(self, mini_client):
        """@validate_json returns 400 for invalid JSON."""
        response = mini_client.post(
            '/test-json',
            data=json.dumps({'password': 'secret123'}),  # missing email
            content_type='application/json',
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
        assert data['error'] in ('Validation Error', 'Bad Request')

    def test_non_json_content_type_returns_400(self, mini_client):
        """@validate_json returns 400 when Content-Type is not JSON."""
        response = mini_client.post(
            '/test-json',
            data={'email': 'user@test.com', 'password': 'secret123'},
            content_type='application/x-www-form-urlencoded',
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
