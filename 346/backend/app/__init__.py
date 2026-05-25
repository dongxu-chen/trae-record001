from flask import Flask
from flask_cors import CORS

def create_app(config_class):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    CORS(app)
    
    from app.api.routes import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app
