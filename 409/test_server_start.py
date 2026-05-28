import sys
import threading
import time
import requests

sys.path.insert(0, '.')

from web import create_app
from wsgiref.simple_server import make_server

app = create_app()
server = make_server('127.0.0.1', 5001, app)

def run_server():
    print("Server thread starting...")
    try:
        server.serve_forever()
    except Exception as e:
        print(f"Server error: {e}")

# Start server in thread
thread = threading.Thread(target=run_server, daemon=True)
thread.start()

print("Waiting for server to start...")
time.sleep(2)

print("Testing health endpoint...")
try:
    response = requests.get('http://127.0.0.1:5001/api/health')
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    print("✅ Server test passed!")
except Exception as e:
    print(f"❌ Server test failed: {e}")

print("Stopping server...")
server.shutdown()
print("Done")
