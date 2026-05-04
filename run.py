from app import create_app, db

app = create_app()

# Simple middleware for local development that sets SCRIPT_NAME
class PrefixMiddleware:
    def __init__(self, app, prefix):
        self.app = app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        path = environ.get('PATH_INFO', '')
        if path.startswith(self.prefix):
            environ['SCRIPT_NAME'] = self.prefix
            environ['PATH_INFO'] = path[len(self.prefix):] or '/'
            return self.app(environ, start_response)
        # If path does not start with prefix, return 404 (avoids mixing routes)
        start_response('404 Not Found', [('Content-Type', 'text/plain')])
        return [b'Not Found']

# Only for local testing — not for production
#app.wsgi_app = PrefixMiddleware(app.wsgi_app, '/onepiecetcg')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
