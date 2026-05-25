import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

HOSTS_FILE = os.getenv('HOSTS_FILE', os.path.join(BASE_DIR, 'data', 'hosts.json'))
AUDIT_LOG_FILE = os.getenv('AUDIT_LOG_FILE', os.path.join(BASE_DIR, 'data', 'audit.log'))
TEMPLATES_DIR = os.getenv('TEMPLATES_DIR', os.path.join(BASE_DIR, 'templates'))
ROLLBACK_DIR = os.getenv('ROLLBACK_DIR', os.path.join(BASE_DIR, 'data', 'rollback'))

SSH_TIMEOUT = int(os.getenv('SSH_TIMEOUT', '30'))
SSH_RETRY = int(os.getenv('SSH_RETRY', '3'))
CONCURRENT_LIMIT = int(os.getenv('CONCURRENT_LIMIT', '10'))

BATCH_CONCURRENCY = int(os.getenv('BATCH_CONCURRENCY', '5'))
HOST_CONCURRENCY = int(os.getenv('HOST_CONCURRENCY', '2'))

WEB_HOST = os.getenv('WEB_HOST', '0.0.0.0')
WEB_PORT = int(os.getenv('WEB_PORT', '5000'))
WEB_SECRET_KEY = os.getenv('WEB_SECRET_KEY', 'your-secret-key-here')

for directory in [os.path.dirname(HOSTS_FILE), TEMPLATES_DIR, ROLLBACK_DIR]:
    os.makedirs(directory, exist_ok=True)
