from collections import defaultdict
from config import Config


class FaultAnalyzer:
    def __init__(self, neo4j_store):
        self.store = neo4j_store
        config = Config()
        self.error_rate_threshold = config.get(
            "analysis.error_rate_threshold", 0.05
        )
        self.latency_threshold_ms = config.get(
            "analysis.latency_threshold_ms", 500
        )

    def detect_anomalies(self, topology):
        anomalies = []

        for edge in topology["edges"]:
            if edge["error_rate"] > self.error_rate_threshold:
                anomalies.append({
                    "type": "high_error_rate",
                    "severity": "high",
                    "source": edge["source"],
                    "target": edge["target"],
                    "error_rate": edge["error_rate"],
                    "call_count": edge["call_count"],
                    "error_count": edge["error_count"],
                    "message": (
                        f"{edge['source']} -> {edge['target']} "
                        f"错误率: {edge['error_rate']:.2%} "
                        f"(阈值: {self.error_rate_threshold:.2%})"
                    ),
                })

            if edge["avg_latency"] > self.latency_threshold_ms:
                anomalies.append({
                    "type": "high_latency",
                    "severity": "medium",
                    "source": edge["source"],
                    "target": edge["target"],
                    "avg_latency": edge["avg_latency"],
                    "max_latency": edge["max_latency"],
                    "message": (
                        f"{edge['source']} -> {edge['target']} "
                        f"平均延迟: {edge['avg_latency']:.0f}μs "
                        f"(阈值: {self.latency_threshold_ms}μs)"
                    ),
                })

        for node in topology["nodes"]:
            if node["error_count"] > 0 and node["call_count"] > 0:
                node_error_rate = node["error_count"] / node["call_count"]
                if node_error_rate > self.error_rate_threshold:
                    anomalies.append({
                        "type": "service_high_error",
                        "severity": "critical",
                        "service": node["name"],
                        "error_rate": node_error_rate,
                        "call_count": node["call_count"],
                        "error_count": node["error_count"],
                        "message": (
                            f"服务 {node['name']} 错误率: "
                            f"{node_error_rate:.2%}"
                        ),
                    })

        anomalies.sort(key=lambda x: (
            {"critical": 0, "high": 1, "medium": 2, "low": 3}
            .get(x["severity"], 4)
        ))

        return anomalies

    def get_fault_impact_tree(self, service_name, depth=5):
        impact_data = self.store.get_fault_impact(service_name, depth)

        downstream = impact_data["downstream_impact"]
        upstream = impact_data["upstream_dependencies"]

        tree = {
            "name": service_name,
            "type": "fault_source",
            "downstream": [],
            "upstream": [],
        }

        downstream_by_hop = defaultdict(list)
        for item in downstream:
            downstream_by_hop[item["hop_count"]].append(item)

        current_level = [tree]
        for hop in sorted(downstream_by_hop.keys()):
            next_level = []
            for parent in current_level:
                for item in downstream_by_hop[hop]:
                    child = {
                        "name": item["name"],
                        "layer": item["layer"],
                        "hop_count": item["hop_count"],
                        "total_calls": item["total_calls"],
                        "total_errors": item["total_errors"],
                        "impact_score": item["impact_score"],
                        "downstream": [],
                    }
                    parent["downstream"].append(child)
                    next_level.append(child)
            current_level = next_level

        upstream_by_hop = defaultdict(list)
        for item in upstream:
            upstream_by_hop[item["hop_count"]].append(item)

        current_up = [tree]
        for hop in sorted(upstream_by_hop.keys()):
            next_up = []
            for child in current_up:
                for item in upstream_by_hop[hop]:
                    parent_node = {
                        "name": item["name"],
                        "layer": item["layer"],
                        "hop_count": item["hop_count"],
                        "upstream": [],
                    }
                    child["upstream"].append(parent_node)
                    next_up.append(parent_node)
            current_up = next_up

        return tree

    def get_fault_broadcast_risk(self, topology):
        services = topology["services"]
        edges = topology["edges"]

        out_edges = defaultdict(list)
        for edge in edges:
            out_edges[edge["source"]].append(edge)

        risk_scores = {}
        for service in services:
            fan_out = len(out_edges.get(service, []))
            total_calls = sum(
                e["call_count"] for e in out_edges.get(service, [])
            )
            total_errors = sum(
                e["error_count"] for e in out_edges.get(service, [])
            )
            error_rate = (
                total_errors / total_calls if total_calls > 0 else 0
            )

            broadcast_risk = fan_out * (1 + error_rate)
            risk_scores[service] = {
                "fan_out": fan_out,
                "total_calls": total_calls,
                "total_errors": total_errors,
                "error_rate": error_rate,
                "broadcast_risk": broadcast_risk,
                "risk_level": (
                    "high" if broadcast_risk > 5
                    else "medium" if broadcast_risk > 2
                    else "low"
                ),
            }

        return {
            "risk_scores": risk_scores,
            "high_risk_services": [
                s for s, r in risk_scores.items()
                if r["risk_level"] == "high"
            ],
        }

    def get_cascading_failure_paths(self, topology, start_service,
                                     max_depth=3):
        edges = topology["edges"]
        adj = defaultdict(list)
        for edge in edges:
            adj[edge["source"]].append(edge)

        paths = []
        visited = set()

        def dfs(current, path, errors, calls):
            if len(path) > max_depth:
                paths.append({
                    "path": list(path),
                    "total_errors": errors,
                    "total_calls": calls,
                    "error_rate": errors / calls if calls > 0 else 0,
                })
                return

            neighbors = adj.get(current, [])
            for neighbor in neighbors:
                target = neighbor["target"]
                if target not in visited:
                    visited.add(target)
                    path.append(target)
                    dfs(
                        target, path,
                        errors + neighbor["error_count"],
                        calls + neighbor["call_count"],
                    )
                    path.pop()
                    visited.remove(target)

            if not neighbors:
                paths.append({
                    "path": list(path),
                    "total_errors": errors,
                    "total_calls": calls,
                    "error_rate": errors / calls if calls > 0 else 0,
                })

        visited.add(start_service)
        dfs(start_service, [start_service], 0, 0)

        paths.sort(key=lambda x: x["error_rate"], reverse=True)
        return paths[:10]
