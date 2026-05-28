import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

from web import create_app
from database import init_db

app = create_app()

if __name__ == '__main__':
    logger.info("Starting Social Media Sentiment Analysis System...")
    
    init_db()
    logger.info("Database initialized")
    
    host = '0.0.0.0'
    port = 5000
    
    logger.info(f"Server starting on http://{host}:{port}")
    
    try:
        from web import socketio
        logger.info("Using SocketIO server")
        socketio.run(app, host=host, port=port, debug=False)
    except Exception as e:
        logger.warning(f"SocketIO not available, using Flask server: {e}")
        app.run(host=host, port=port, debug=False)
