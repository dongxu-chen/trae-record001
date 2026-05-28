import sys
sys.path.insert(0, '.')

from wsgiref.simple_server import make_server
from web import create_app

app = create_app()

if __name__ == '__main__':
    print("Starting server on http://0.0.0.0:5000")
    print("Press Ctrl+C to stop")
    httpd = make_server('0.0.0.0', 5000, app)
    httpd.serve_forever()
