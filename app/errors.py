"""
Error handlers for the application.
"""
from flask import render_template, jsonify
from werkzeug.exceptions import HTTPException


def register_error_handlers(app):
    """Register all error handlers with the app."""

    @app.errorhandler(404)
    def not_found_error(error):
        """Handle 404 Not Found errors."""
        if request_wants_json():
            return jsonify({
                'success': False,
                'error': 'Not Found',
                'message': 'The requested resource was not found'
            }), 404
        return _render_error_template('404', error), 404

    @app.errorhandler(500)
    def internal_error(error):
        """Handle 500 Internal Server errors."""
        if request_wants_json():
            return jsonify({
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500
        return _render_error_template('500', error), 500

    @app.errorhandler(403)
    def forbidden_error(error):
        """Handle 403 Forbidden errors."""
        if request_wants_json():
            return jsonify({
                'success': False,
                'error': 'Forbidden',
                'message': 'You do not have permission to access this resource'
            }), 403
        return _render_error_template('403', error), 403

    @app.errorhandler(401)
    def unauthorized_error(error):
        """Handle 401 Unauthorized errors."""
        if request_wants_json():
            return jsonify({
                'success': False,
                'error': 'Unauthorized',
                'message': 'Authentication is required'
            }), 401
        return _render_error_template('401', error), 401

    @app.errorhandler(400)
    def bad_request_error(error):
        """Handle 400 Bad Request errors."""
        if request_wants_json():
            return jsonify({
                'success': False,
                'error': 'Bad Request',
                'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
            }), 400
        return _render_error_template('400', error), 400

    @app.errorhandler(Exception)
    def handle_exception(error):
        """Handle all other exceptions."""
        # Handle HTTP exceptions
        if isinstance(error, HTTPException):
            if request_wants_json():
                return jsonify({
                    'success': False,
                    'error': error.name,
                    'message': error.description
                }), error.code
            return _render_error_template(str(error.code), error), error.code

        # Log unexpected errors
        app.logger.error(f'Unhandled exception: {error}', exc_info=True)

        if request_wants_json():
            return jsonify({
                'success': False,
                'error': 'Internal Server Error',
                'message': 'An unexpected error occurred'
            }), 500

        return _render_error_template('500', error), 500


def _render_error_template(code, error):
    """Render error template with fallback to plain text if template is missing."""
    try:
        return render_template(f'errors/{code}.html', error=error)
    except Exception:
        # Fallback: plain text response when templates don't exist yet
        description = getattr(error, 'description', str(error)) if error else 'An error occurred'
        from flask import make_response
        resp = make_response(f'<h1>Error {code}</h1><p>{description}</p>', int(code))
        resp.headers['Content-Type'] = 'text/html; charset=utf-8'
        return resp


def request_wants_json():
    """Check if the request prefers JSON response."""
    from flask import request
    return (
        request.is_json or
        request.accept_mimetypes.accept_json or
        request.headers.get('Accept') == 'application/json'
    )
