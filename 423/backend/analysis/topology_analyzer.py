from collections import defaultdict, deque


class TopologyAnalyzer:
    def __init__(self, neo4j_store):
        self.store = neo4j_store

    def determine_layers(self, topology):
        nodes = {n["name"]: n for n in topology["nodes"]}
        edges = topology["edges"]

        incoming = defaultdict(int)
        outgoing = defaultdict(int)
        adj = defaultdict(set)
        reverse_adj = defaultdict(set)

        for edge in edges:
            src = edge["source"]
            tgt = edge["target"]
            adj[src].add(tgt)
            reverse_adj[tgt].add(src)
            outgoing[src] += 1
            incoming[tgt] += 1

        layers = {}
        queue = deque()

        for node in nodes:
            if incoming[node] == 0:
                layers[node] = 0
                queue.append(node)

        while queue:
            current = queue.popleft()
            current_layer = layers[current]
            for neighbor in adj[current]:
                incoming[neighbor] -= 1
                if incoming[neighbor] == 0:
                    layers[neighbor] = current_layer + 1
                    queue.append(neighbor)

        max_layer = max(layers.values()) if layers else 0
        for node in nodes:
            if node not in layers:
                layers[node] = max_layer + 1

        layer_counts = defaultdict(int)
        for node, layer in layers.items():
            layer_counts[layer] += 1

        return {
            "layers": layers,
            "layer_counts": dict(layer_counts),
            "max_layer": max_layer,
            "entry_points": [n for n, l in layers.items() if l == 0],
            "leaf_services": [n for n in nodes
                              if outgoing.get(n, 0) == 0],
        }

    def identify_critical_paths(self, topology):
        nodes = {n["name"]: n for n in topology["nodes"]}
        edges = topology["edges"]

        adj = defaultdict(list)
        for edge in edges:
            adj[edge["source"]].append({
                "target": edge["target"],
                "call_count": edge["call_count"],
                "error_rate": edge["error_rate"],
                "avg_latency": edge["avg_latency"],
            })

        def dfs_paths(node, path, visited):
            if node in visited:
                return []
            visited.add(node)
            path.append(node)

            neighbors = adj.get(node, [])
            if not neighbors:
                return [list(path)]

            all_paths = []
            for neighbor_info in neighbors:
                neighbor = neighbor_info["target"]
                if neighbor not in visited:
                    sub_paths = dfs_paths(neighbor, path, visited)
                    all_paths.extend(sub_paths)

            path.pop()
            visited.remove(node)
            return all_paths if all_paths else [list(path)]

        entry_points = [
            n["name"] for n in nodes.values()
            if n["name"] not in [e["target"] for e in edges]
        ]

        all_paths = []
        for entry in entry_points:
            paths = dfs_paths(entry, [], set())
            all_paths.extend(paths)

        critical_paths = []
        for path in all_paths:
            total_calls = 0
            total_errors = 0
            max_latency = 0
            for i in range(len(path) - 1):
                for edge in edges:
                    if (edge["source"] == path[i] and
                            edge["target"] == path[i + 1]):
                        total_calls += edge["call_count"]
                        total_errors += edge["error_count"]
                        max_latency = max(
                            max_latency, edge["avg_latency"]
                        )
            critical_paths.append({
                "path": path,
                "total_calls": total_calls,
                "total_errors": total_errors,
                "error_rate": (
                    total_errors / total_calls if total_calls > 0 else 0
                ),
                "max_latency": max_latency,
            })

        critical_paths.sort(
            key=lambda x: (x["error_rate"], x["max_latency"]),
            reverse=True
        )

        return critical_paths[:10]

    def compute_dependency_metrics(self, topology):
        nodes = {n["name"]: n for n in topology["nodes"]}
        edges = topology["edges"]

        incoming_count = defaultdict(int)
        outgoing_count = defaultdict(int)
        for edge in edges:
            outgoing_count[edge["source"]] += 1
            incoming_count[edge["target"]] += 1

        metrics = {}
        for name, node in nodes.items():
            fan_in = incoming_count.get(name, 0)
            fan_out = outgoing_count.get(name, 0)

            metrics[name] = {
                "fan_in": fan_in,
                "fan_out": fan_out,
                "is_hub": fan_in >= 3 or fan_out >= 3,
                "is_entry_point": fan_in == 0,
                "is_leaf": fan_out == 0,
            }

        return metrics

    def get_topology_summary(self, time_window_minutes=60):
        topology = self.store.get_topology(time_window_minutes)
        layer_info = self.determine_layers(topology)
        metrics = self.compute_dependency_metrics(topology)

        total_calls = sum(e["call_count"] for e in topology["edges"])
        total_errors = sum(e["error_count"] for e in topology["edges"])
        total_latency = sum(e["total_latency"] for e in topology["edges"])

        return {
            "services_count": len(topology["services"]),
            "edges_count": len(topology["edges"]),
            "total_calls": total_calls,
            "total_errors": total_errors,
            "overall_error_rate": (
                total_errors / total_calls if total_calls > 0 else 0
            ),
            "avg_latency_ms": (
                total_latency / total_calls if total_calls > 0 else 0
            ),
            "layer_info": layer_info,
            "metrics": metrics,
            "time_window_minutes": time_window_minutes,
        }
