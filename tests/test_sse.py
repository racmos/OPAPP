"""
Tests for SSE (Server-Sent Events) endpoints.
"""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestSSEEndpoints:
    """Verify SSE endpoints stream events correctly."""

    @pytest.fixture
    def logged_client(self):
        """Logged-in test client."""
        from app import create_app, db
        from app.models import OpUser

        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        with app.app_context():
            db.create_all()
            user = OpUser(username='ssetest', email='ssetest@test.com')
            user.set_password('test123')
            db.session.add(user)
            db.session.commit()

            client = app.test_client()
            client.post(
                '/onepiecetcg/login',
                data=json.dumps({'email': 'ssetest@test.com', 'password': 'test123'}),
                content_type='application/json',
            )
            yield client
            db.drop_all()

    def test_cardmarket_load_sse_returns_event_stream(self, logged_client):
        """GET /cardmarket-load-sse returns text/event-stream."""
        mock_result = {
            'success': True,
            'date': '20260101',
            'steps': [],
            'errors': [],
            'unmatched_count': 0,
        }

        with patch('app.services.cardmarket_loader.CardmarketLoader.run', return_value=mock_result):
            resp = logged_client.get('/onepiecetcg/price/cardmarket-load-sse')
            assert resp.status_code == 200
            assert resp.mimetype == 'text/event-stream'
            assert 'X-Accel-Buffering' in resp.headers
            assert resp.headers['X-Accel-Buffering'] == 'no'

    def test_extract_op_cards_sse_returns_event_stream(self, logged_client):
        """GET /extract-op-cards-sse returns text/event-stream."""
        mock_result = {
            'success': True,
            'steps': [{'step': 'Fetch', 'status': 'SUCCESS', 'message': 'Done'}],
            'stats': {'total_scraped': 10},
        }

        with patch('app.services.onepiece_scraper.extract_op_cards', return_value=mock_result):
            resp = logged_client.get('/onepiecetcg/price/extract-op-cards-sse')
            assert resp.status_code == 200
            assert resp.mimetype == 'text/event-stream'
            assert 'X-Accel-Buffering' in resp.headers

    def test_extract_op_cards_sse_with_sets_param(self, logged_client):
        """SSE endpoint passes sets parameter to scraper."""
        mock_result = {'success': True, 'steps': [], 'stats': {}}

        with patch('app.services.onepiece_scraper.extract_op_cards', return_value=mock_result) as mock_extract:
            logged_client.get(
                '/onepiecetcg/price/extract-op-cards-sse',
                query_string={'sets': '[{"id":"OP01","code":"OP-01"}]'},
            )
            mock_extract.assert_called_once()
            call_kwargs = mock_extract.call_args.kwargs
            assert call_kwargs['filter_sets'] == [{'id': 'OP01', 'code': 'OP-01'}]

    def test_sse_requires_login(self):
        """SSE endpoints redirect when not authenticated."""
        from app import create_app

        app = create_app(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SECRET_KEY='test-secret-key',
        )
        client = app.test_client()
        resp = client.get('/onepiecetcg/price/cardmarket-load-sse')
        assert resp.status_code in (302, 401)
