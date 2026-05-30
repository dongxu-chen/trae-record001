from flask import Flask
from flask_cors import CORS

from app.api.routes import api_bp
from app.config import Config


def create_app() -> Flask:
    app = Flask(__name__)
    
    CORS(app)
    
    app.register_blueprint(api_bp)
    
    @app.route("/")
    def root():
        return {
            "service": "Data Lineage Parser API",
            "version": "1.0.0",
            "endpoints": {
                "POST /api/parse": "Parse SQL without saving to Neo4j",
                "POST /api/lineage": "Parse SQL and save lineage to Neo4j",
                "GET /api/lineage/table/{table_name}": "Get table lineage",
                "GET /api/lineage/column/{column_name}": "Get column lineage",
                "GET /api/tables": "Get all tables",
                "GET /api/tables/{table_name}/columns": "Get table columns",
                "GET /api/graph": "Get full graph",
                "DELETE /api/database": "Clear database",
                "GET /api/health": "Health check",
            },
        }
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=True)
