import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from storage.neo4j_store import Neo4jStore
from collector.trace_collector import TraceCollector
from analysis.topology_analyzer import TopologyAnalyzer
from analysis.fault_analyzer import FaultAnalyzer
from config import Config

app = Flask(__name__, static_folder="../frontend", static_url_path="")
CORS(app)

config = Config()
neo4j_store = Neo4jStore()
trace_collector = TraceCollector()
topology_analyzer = TopologyAnalyzer(neo4j_store)
fault_analyzer = FaultAnalyzer(neo4j_store)


@app.route("/")
def index():
    return send_from_directory("../frontend", "index.html")


@app.route("/api/topology", methods=["GET"])
def get_topology():
    time_window = request.args.get("time_window", 60, type=int)
    topology = neo4j_store.get_topology(time_window)
    return jsonify(topology)


@app.route("/api/topology/analysis", methods=["GET"])
def get_topology_analysis():
    time_window = request.args.get("time_window", 60, type=int)
    summary = topology_analyzer.get_topology_summary(time_window)
    return jsonify(summary)


@app.route("/api/topology/layers", methods=["GET"])
def get_service_layers():
    time_window = request.args.get("time_window", 60, type=int)
    topology = neo4j_store.get_topology(time_window)
    layers = topology_analyzer.determine_layers(topology)
    return jsonify(layers)


@app.route("/api/topology/critical-paths", methods=["GET"])
def get_critical_paths():
    time_window = request.args.get("time_window", 60, type=int)
    topology = neo4j_store.get_topology(time_window)
    paths = topology_analyzer.identify_critical_paths(topology)
    return jsonify(paths)


@app.route("/api/topology/metrics", methods=["GET"])
def get_dependency_metrics():
    time_window = request.args.get("time_window", 60, type=int)
    topology = neo4j_store.get_topology(time_window)
    metrics = topology_analyzer.compute_dependency_metrics(topology)
    return jsonify(metrics)


@app.route("/api/topology/anomalies", methods=["GET"])
def get_anomalies():
    time_window = request.args.get("time_window", 60, type=int)
    topology = neo4j_store.get_topology(time_window)
    anomalies = fault_analyzer.detect_anomalies(topology)
    return jsonify(anomalies)


@app.route("/api/fault/impact/<service_name>", methods=["GET"])
def get_fault_impact(service_name):
    depth = request.args.get("depth", 5, type=int)
    impact = neo4j_store.get_fault_impact(service_name, depth)
    return jsonify(impact)


@app.route("/api/fault/impact-tree/<service_name>", methods=["GET"])
def get_fault_impact_tree(service_name):
    depth = request.args.get("depth", 5, type=int)
    tree = fault_analyzer.get_fault_impact_tree(service_name, depth)
    return jsonify(tree)


@app.route("/api/fault/broadcast-risk", methods=["GET"])
def get_broadcast_risk():
    time_window = request.args.get("time_window", 60, type=int)
    topology = neo4j_store.get_topology(time_window)
    risk = fault_analyzer.get_fault_broadcast_risk(topology)
    return jsonify(risk)


@app.route("/api/fault/cascading-paths/<service_name>", methods=["GET"])
def get_cascading_paths(service_name):
    time_window = request.args.get("time_window", 60, type=int)
    max_depth = request.args.get("max_depth", 3, type=int)
    topology = neo4j_store.get_topology(time_window)
    paths = fault_analyzer.get_cascading_failure_paths(
        topology, service_name, max_depth
    )
    return jsonify(paths)


@app.route("/api/topology/snapshot", methods=["POST"])
def create_snapshot():
    snapshot_id = neo4j_store.snapshot_topology()
    return jsonify({"snapshot_id": snapshot_id})


@app.route("/api/topology/snapshots", methods=["GET"])
def list_snapshots():
    limit = request.args.get("limit", 10, type=int)
    snapshots = neo4j_store.get_snapshots(limit)
    return jsonify(snapshots)


@app.route("/api/topology/diff", methods=["GET"])
def get_topology_diff():
    snapshot_a = request.args.get("snapshot_a")
    snapshot_b = request.args.get("snapshot_b")
    if not snapshot_a or not snapshot_b:
        return jsonify({"error": "Both snapshot_a and snapshot_b are required"}), 400
    diff = neo4j_store.get_topology_diff(snapshot_a, snapshot_b)
    return jsonify(diff)


@app.route("/api/collect/import", methods=["POST"])
def import_traces():
    data = request.get_json()
    service = data.get("service")
    lookback = data.get("lookback", "1h")
    limit = data.get("limit", 100)

    result = trace_collector.collect_and_store(
        neo4j_store, service=service,
        lookback=lookback, limit=limit
    )
    return jsonify(result)


@app.route("/api/services/list", methods=["GET"])
def list_services():
    services = trace_collector.fetch_services()
    return jsonify({"services": services})


@app.route("/api/services/operations/<service>", methods=["GET"])
def get_service_operations(service):
    operations = trace_collector.fetch_service_operations(service)
    return jsonify({"service": service, "operations": operations})


@app.route("/api/version/impact", methods=["GET"])
def get_version_impact():
    service = request.args.get("service")
    old_version = request.args.get("old_version", "1.0.0")
    new_version = request.args.get("new_version", "2.0.0")
    if not service:
        return jsonify({"error": "service is required"}), 400
    impact = neo4j_store.get_version_impact_analysis(service, old_version, new_version)
    return jsonify(impact)


@app.route("/api/api/register", methods=["POST"])
def register_api_endpoint():
    data = request.get_json()
    service = data.get("service")
    path = data.get("path")
    method = data.get("method", "GET")
    version = data.get("version", "1.0.0")
    deprecated = data.get("deprecated", False)
    breaking_change = data.get("breaking_change", False)
    change_description = data.get("change_description")

    if not service or not path:
        return jsonify({"error": "service and path are required"}), 400

    api_id = neo4j_store.upsert_api_endpoint(
        service_name=service,
        path=path,
        method=method,
        version=version,
        deprecated=deprecated,
        breaking_change=breaking_change,
        change_description=change_description
    )
    return jsonify({"api_id": api_id})


@app.route("/api/request/paths", methods=["GET"])
def get_request_paths():
    source = request.args.get("source")
    target = request.args.get("target")
    max_paths = request.args.get("max_paths", 5, type=int)
    max_depth = request.args.get("max_depth", 6, type=int)

    if not source:
        return jsonify({"error": "source is required"}), 400

    paths = neo4j_store.get_request_paths(source, target, max_paths, max_depth)
    return jsonify({"paths": paths})


@app.route("/api/health", methods=["GET"])
def health_check():
    try:
        topology = neo4j_store.get_topology(60)
        services = trace_collector.fetch_services()
        return jsonify({
            "status": "healthy",
            "neo4j_connected": True,
            "jaeger_connected": len(services) > 0,
            "services_tracked": len(topology["services"]),
        })
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
        }), 500


@app.route("/api/clear", methods=["POST"])
def clear_data():
    neo4j_store.clear_all()
    return jsonify({"status": "cleared"})


if __name__ == "__main__":
    host = config.get("flask.host", "0.0.0.0")
    port = config.get("flask.port", 5000)
    app.run(host=host, port=port, debug=True)
