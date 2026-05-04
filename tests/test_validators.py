"""
Tests for Pydantic schemas and @validate_json decorator.
"""
import json
import pytest
from pydantic import ValidationError
from flask import Flask, jsonify
from app.schemas.validators import LoginSchema, RegisterSchema, validate_json


class TestLoginSchema:
    """Unit tests for LoginSchema."""

    def test_valid_login(self):
        """LoginSchema accepts valid email and password."""
        schema = LoginSchema(email="user@test.com", password="secret123")
        assert schema.email == "user@test.com"
        assert schema.password == "secret123"

    def test_missing_email(self):
        """LoginSchema rejects missing email."""
        with pytest.raises(ValidationError):
            LoginSchema(password="secret123")

    def test_missing_password(self):
        """LoginSchema rejects missing password."""
        with pytest.raises(ValidationError):
            LoginSchema(email="user@test.com")

    def test_invalid_email_no_at(self):
        """LoginSchema rejects email without @."""
        with pytest.raises(ValidationError):
            LoginSchema(email="notanemail", password="secret123")

    def test_empty_password(self):
        """LoginSchema rejects empty password."""
        with pytest.raises(ValidationError):
            LoginSchema(email="user@test.com", password="")

    def test_strips_email_whitespace(self):
        """LoginSchema strips whitespace from email."""
        schema = LoginSchema(email="  user@test.com  ", password="secret123")
        assert schema.email == "user@test.com"


class TestRegisterSchema:
    """Unit tests for RegisterSchema."""

    def test_valid_register(self):
        """RegisterSchema accepts valid data."""
        schema = RegisterSchema(
            username="newuser",
            email="new@test.com",
            password="secret123"
        )
        assert schema.username == "newuser"
        assert schema.email == "new@test.com"
        assert schema.password == "secret123"

    def test_missing_username(self):
        """RegisterSchema rejects missing username."""
        with pytest.raises(ValidationError):
            RegisterSchema(email="new@test.com", password="secret123")

    def test_missing_email(self):
        """RegisterSchema rejects missing email."""
        with pytest.raises(ValidationError):
            RegisterSchema(username="newuser", password="secret123")

    def test_missing_password(self):
        """RegisterSchema rejects missing password."""
        with pytest.raises(ValidationError):
            RegisterSchema(username="newuser", email="new@test.com")

    def test_short_password(self):
        """RegisterSchema rejects password shorter than 6 chars."""
        with pytest.raises(ValidationError):
            RegisterSchema(
                username="newuser",
                email="new@test.com",
                password="12345"
            )

    def test_empty_username(self):
        """RegisterSchema rejects empty username."""
        with pytest.raises(ValidationError):
            RegisterSchema(
                username="",
                email="new@test.com",
                password="secret123"
            )

    def test_invalid_email_no_at(self):
        """RegisterSchema rejects email without @."""
        with pytest.raises(ValidationError):
            RegisterSchema(
                username="newuser",
                email="notanemail",
                password="secret123"
            )

    def test_strips_username_whitespace(self):
        """RegisterSchema strips whitespace from username and email."""
        schema = RegisterSchema(
            username="  newuser  ",
            email="  new@test.com  ",
            password="secret123"
        )
        assert schema.username == "newuser"
        assert schema.email == "new@test.com"


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
            return jsonify({
                'success': True,
                'email': request.validated_data.email,
            })

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
            content_type='application/json'
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
            content_type='application/json'
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
            content_type='application/x-www-form-urlencoded'
        )
        assert response.status_code == 400
        data = response.get_json()
        assert data['success'] is False
