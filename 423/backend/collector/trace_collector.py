import requests
import time
from datetime import datetime, timedelta
from config import Config


class TraceCollector:
    def __init__(self):
        config = Config()
        self.query_endpoint = config.get(
            "jaeger.query_endpoint",
            "http://localhost:16686/api/traces"
        )
        self.collector_endpoint = config.get(
            "jaeger.collector_endpoint",
            "http://localhost:14268/api/traces"
        )

    def fetch_traces(self, service=None, limit=100, lookback="1h",
                     tags=None):
        params = {
            "limit": limit,
            "lookback": lookback,
        }
        if service:
            params["service"] = service
        if tags:
            params["tags"] = tags

        try:
            resp = requests.get(
                self.query_endpoint,
                params=params,
                timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"[TraceCollector] Failed to fetch traces: {e}")
            return []

    def fetch_services(self):
        services_endpoint = self.query_endpoint.replace(
            "/api/traces", "/api/services"
        )
        try:
            resp = requests.get(services_endpoint, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"[TraceCollector] Failed to fetch services: {e}")
            return []

    def fetch_service_operations(self, service):
        ops_endpoint = self.query_endpoint.replace(
            "/api/traces", f"/api/services/{service}/operations"
        )
        try:
            resp = requests.get(ops_endpoint, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", [])
        except requests.exceptions.RequestException as e:
            print(f"[TraceCollector] Failed to fetch operations: {e}")
            return []

    def submit_trace(self, trace_data):
        try:
            resp = requests.post(
                self.collector_endpoint,
                json=trace_data,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            resp.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"[TraceCollector] Failed to submit trace: {e}")
            return False

    def parse_traces_to_topology(self, traces):
        edges = {}
        nodes = {}
        async_edges = {}

        for trace in traces:
            spans = trace.get("spans", [])
            span_map = {}
            for span in spans:
                span_map[span["spanID"]] = span

            for span in spans:
                service_name = None
                for process_key, process in trace.get("processes", {}).items():
                    if process_key == span.get("processID"):
                        service_name = process.get("serviceName")
                        break

                if not service_name:
                    continue

                operation = span.get("operationName", "unknown")
                duration = span.get("duration", 0)
                tags = {t["key"]: t["value"] for t in span.get("tags", [])}
                is_error = tags.get("error", False) or any(
                    log.get("fields", [{}])[0].get("value") == "error"
                    for log in span.get("logs", [])
                )

                api_version = tags.get("api.version") or tags.get("http.route") or tags.get("grpc.service")
                queue_name = tags.get("messaging.destination") or tags.get("kafka.topic") or tags.get("rabbitmq.queue")
                message_operation = tags.get("messaging.operation") or tags.get("span.kind")
                call_type = tags.get("call.type", "sync")

                if service_name not in nodes:
                    nodes[service_name] = {
                        "name": service_name,
                        "call_count": 0,
                        "error_count": 0,
                        "total_latency": 0,
                    }
                nodes[service_name]["call_count"] += 1
                nodes[service_name]["total_latency"] += duration
                if is_error:
                    nodes[service_name]["error_count"] += 1

                if queue_name and message_operation:
                    async_key = (service_name, queue_name, message_operation)
                    if async_key not in async_edges:
                        async_edges[async_key] = {
                            "service": service_name,
                            "queue": queue_name,
                            "operation": message_operation,
                            "call_count": 0,
                            "error_count": 0,
                            "total_latency": 0,
                            "api_version": api_version,
                        }
                    async_edges[async_key]["call_count"] += 1
                    async_edges[async_key]["total_latency"] += duration
                    if is_error:
                        async_edges[async_key]["error_count"] += 1
                    continue

                references = span.get("references", [])
                for ref in references:
                    if ref.get("refType") == "CHILD_OF":
                        parent_span = span_map.get(ref["spanID"])
                        if parent_span:
                            parent_service = None
                            for pk, proc in trace.get("processes", {}).items():
                                if pk == parent_span.get("processID"):
                                    parent_service = proc.get("serviceName")
                                    break

                            if parent_service and parent_service != service_name:
                                edge_key = (parent_service, service_name)
                                if edge_key not in edges:
                                    edges[edge_key] = {
                                        "source": parent_service,
                                        "target": service_name,
                                        "call_count": 0,
                                        "error_count": 0,
                                        "total_latency": 0,
                                        "max_latency": 0,
                                        "min_latency": float("inf"),
                                        "call_type": call_type,
                                        "api_version": api_version,
                                        "operation": operation,
                                    }
                                edges[edge_key]["call_count"] += 1
                                edges[edge_key]["total_latency"] += duration
                                edges[edge_key]["max_latency"] = max(
                                    edges[edge_key]["max_latency"], duration
                                )
                                edges[edge_key]["min_latency"] = min(
                                    edges[edge_key]["min_latency"], duration
                                )
                                if is_error:
                                    edges[edge_key]["error_count"] += 1

        return {
            "nodes": list(nodes.values()),
            "edges": [
                {**e, "min_latency": 0 if e["min_latency"] == float("inf")
                 else e["min_latency"]}
                for e in edges.values()
            ],
            "async_edges": list(async_edges.values()),
        }

    def collect_and_store(self, neo4j_store, service=None,
                          lookback="1h", limit=100):
        traces = self.fetch_traces(
            service=service, limit=limit, lookback=lookback
        )
        if not traces:
            return {"nodes": 0, "edges": 0, "async_edges": 0}

        topology = self.parse_traces_to_topology(traces)

        for node in topology["nodes"]:
            neo4j_store.upsert_service(
                name=node["name"],
                service_type="detected",
            )

        for edge in topology["edges"]:
            neo4j_store.upsert_service(
                name=edge["source"], service_type="detected"
            )
            neo4j_store.upsert_service(
                name=edge["target"], service_type="detected"
            )
            neo4j_store.upsert_call_edge(
                source=edge["source"],
                target=edge["target"],
                call_count=edge["call_count"],
                error_count=edge["error_count"],
                total_latency=edge["total_latency"],
                max_latency=edge["max_latency"],
                min_latency=edge["min_latency"],
                call_type=edge.get("call_type", "sync"),
                api_version=edge.get("api_version"),
                operation_name=edge.get("operation"),
            )

        for async_edge in topology.get("async_edges", []):
            neo4j_store.upsert_message_queue(async_edge["queue"])
            if async_edge["operation"] in ("send", "produce", "publisher"):
                neo4j_store.upsert_produce_edge(
                    service_name=async_edge["service"],
                    queue_name=async_edge["queue"],
                    count=async_edge["call_count"],
                    error_count=async_edge["error_count"],
                    api_version=async_edge.get("api_version"),
                    operation_name=async_edge["operation"],
                )
            elif async_edge["operation"] in ("receive", "consume", "subscriber"):
                neo4j_store.upsert_consume_edge(
                    queue_name=async_edge["queue"],
                    service_name=async_edge["service"],
                    count=async_edge["call_count"],
                    error_count=async_edge["error_count"],
                    api_version=async_edge.get("api_version"),
                    operation_name=async_edge["operation"],
                    latency=async_edge.get("total_latency", 0) / max(async_edge["call_count"], 1),
                )

        return {
            "nodes": len(topology["nodes"]),
            "edges": len(topology["edges"]),
            "async_edges": len(topology.get("async_edges", [])),
        }
