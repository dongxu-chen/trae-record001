import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(os.path.dirname(__file__), 'data', 'app.log'), encoding='utf-8')
    ]
)

logger = logging.getLogger(__name__)

from web import create_app, socketio
from database import init_db

app = create_app()

if __name__ == '__main__':
    logger.info("Starting Social Media Sentiment Analysis System...")
    
    init_db()
    logger.info("Database initialized")
    
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('DEBUG', 'false').lower() == 'true'
    
    logger.info(f"Server starting on {host}:{port}")
    logger.info(f"Debug mode: {debug}")
    
    socketio.run(app, host=host, port=port, debug=debug)
