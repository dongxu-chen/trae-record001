from flask import Flask
from flask_cors import CORS
from app.routes import api_bp
from app.redis_client import init_redis


def create_app():
    app = Flask(__name__)
    CORS(app)
    
    app.register_blueprint(api_bp, url_prefix='/api')
    
    init_redis(app)
    
    return app
