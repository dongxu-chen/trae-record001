from flask import Blueprint, request, jsonify
from typing import Dict, Any

from app.parsers.sql_lineage_parser import SQLLineageParser
from app.services.neo4j_service import Neo4jService
from app.config import Config

api_bp = Blueprint("api", __name__, url_prefix="/api")


def get_neo4j_service() -> Neo4jService:
    return Neo4jService(
        uri=Config.NEO4J_URI,
        user=Config.NEO4J_USER,
        password=Config.NEO4J_PASSWORD,
    )


@api_bp.route("/parse", methods=["POST"])
def parse_sql():
    try:
        data = request.get_json()
        sql = data.get("sql", "")
        database = data.get("database")
        schema = data.get("schema")

        if not sql:
            return jsonify({"error": "SQL is required"}), 400

        parser = SQLLineageParser(default_database=database, default_schema=schema)
        result = parser.parse(sql)

        return jsonify(result.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lineage", methods=["POST"])
def parse_and_save_lineage():
    try:
        data = request.get_json()
        sql = data.get("sql", "")
        database = data.get("database")
        schema = data.get("schema")

        if not sql:
            return jsonify({"error": "SQL is required"}), 400

        parser = SQLLineageParser(default_database=database, default_schema=schema)
        result = parser.parse(sql)

        neo4j = get_neo4j_service()
        neo4j.save_lineage(result)
        neo4j.close()

        return jsonify(result.model_dump())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lineage/table/<path:table_name>", methods=["GET"])
def get_table_lineage(table_name: str):
    try:
        depth = int(request.args.get("depth", 3))
        collapse = request.args.get("collapse", "true").lower() == "true"
        
        neo4j = get_neo4j_service()
        result = neo4j.get_table_lineage(table_name, depth, collapse)
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lineage/column/<path:column_name>", methods=["GET"])
def get_column_lineage(column_name: str):
    try:
        depth = int(request.args.get("depth", 3))
        collapse = request.args.get("collapse", "true").lower() == "true"
        
        neo4j = get_neo4j_service()
        result = neo4j.get_column_lineage(column_name, depth, collapse)
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lineage/column/<path:column_name>/mapping-chains", methods=["GET"])
def get_column_mapping_chains(column_name: str):
    try:
        neo4j = get_neo4j_service()
        chains = neo4j.get_mapping_chains(column_name)
        neo4j.close()

        return jsonify({"mapping_chains": chains})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/lineage/expand", methods=["POST"])
def expand_aggregated_edge():
    try:
        data = request.get_json()
        source = data.get("source")
        target = data.get("target")

        if not source or not target:
            return jsonify({"error": "source and target are required"}), 400

        neo4j = get_neo4j_service()
        result = neo4j.expand_aggregated_edge(source, target)
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/tables", methods=["GET"])
def get_all_tables():
    try:
        neo4j = get_neo4j_service()
        tables = neo4j.get_all_tables()
        neo4j.close()

        return jsonify({"tables": tables})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/tables/<path:table_name>/columns", methods=["GET"])
def get_table_columns(table_name: str):
    try:
        neo4j = get_neo4j_service()
        columns = neo4j.get_table_columns(table_name)
        neo4j.close()

        return jsonify({"columns": columns})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/graph", methods=["GET"])
def get_full_graph():
    try:
        collapse = request.args.get("collapse", "true").lower() == "true"
        
        neo4j = get_neo4j_service()
        graph = neo4j.get_full_graph(collapse)
        neo4j.close()

        return jsonify(graph)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/database", methods=["DELETE"])
def clear_database():
    try:
        neo4j = get_neo4j_service()
        neo4j.clear_database()
        neo4j.close()

        return jsonify({"message": "Database cleared successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "data-lineage-api"})


@api_bp.route("/impact/<path:table_name>", methods=["GET"])
def analyze_impact(table_name: str):
    try:
        max_depth = int(request.args.get("depth", 10))
        
        neo4j = get_neo4j_service()
        result = neo4j.analyze_impact(table_name, max_depth)
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/data-dictionary", methods=["GET"])
def get_data_dictionary():
    try:
        neo4j = get_neo4j_service()
        result = neo4j.generate_data_dictionary()
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/document", methods=["GET"])
def get_lineage_document():
    try:
        title = request.args.get("title", "数据血缘文档")
        
        neo4j = get_neo4j_service()
        result = neo4j.generate_lineage_document(title)
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/document/markdown", methods=["GET"])
def get_markdown_document():
    try:
        title = request.args.get("title", "数据血缘文档")
        
        neo4j = get_neo4j_service()
        markdown = neo4j.generate_markdown_document(title)
        neo4j.close()

        return markdown, 200, {"Content-Type": "text/markdown; charset=utf-8"}
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/anomalies", methods=["GET"])
def detect_anomalies():
    try:
        neo4j = get_neo4j_service()
        result = neo4j.detect_anomalies()
        neo4j.close()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
