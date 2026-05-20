import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.app import create_app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
