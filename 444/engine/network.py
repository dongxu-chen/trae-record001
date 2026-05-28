from typing import List, Dict, Tuple, Optional
import numpy as np
import networkx as nx
from models.data_models import DetectionResult, FollowerRiskLevel


class NetworkAnalyzer:
    def __init__(self):
        self.graph = nx.Graph()
        self._fake_nodes = set()
        self._genuine_nodes = set()
        self._node_clustering = {}
        self._simplified = True

    def build_graph(
        self,
        target_user: str,
        followers: List[dict],
        detection_results: List[DetectionResult],
        interactions: Optional[List[dict]] = None,
    ):
        self.graph.clear()
        self._fake_nodes.clear()
        self._genuine_nodes.clear()
        self._node_clustering.clear()

        self.graph.add_node(target_user, type="target", risk="genuine")

        for follower, result in zip(followers, detection_results):
            node_id = follower.get("user_id", "")
            self.graph.add_node(
                node_id,
                type="follower",
                username=follower.get("username", ""),
                risk=result.risk_level.value,
                fake_prob=result.fake_probability,
            )

            if result.risk_level in (FollowerRiskLevel.FAKE, FollowerRiskLevel.LIKELY_FAKE):
                self._fake_nodes.add(node_id)
            else:
                self._genuine_nodes.add(node_id)

            self.graph.add_edge(node_id, target_user)

        if interactions:
            for interaction in interactions:
                source = interaction.get("source_user_id", "")
                target = interaction.get("target_user_id", "")
                if source in self.graph and target in self.graph:
                    self.graph.add_edge(source, target)

    def add_simulated_interactions(self, followers: List[dict], detection_results: List[DetectionResult]):
        fake_ids = list(self._fake_nodes)
        genuine_ids = list(self._genuine_nodes)

        n_fake = len(fake_ids)
        n_genuine = len(genuine_ids)

        if n_fake > 5:
            fake_cluster_size = min(15, n_fake // 4)
            fake_cluster = np.random.choice(fake_ids, size=fake_cluster_size, replace=False)
            for i in range(len(fake_cluster)):
                for j in range(i + 1, len(fake_cluster)):
                    self.graph.add_edge(fake_cluster[i], fake_cluster[j])

        if n_genuine > 5:
            genuine_cluster_size = min(10, n_genuine // 5)
            genuine_cluster = np.random.choice(genuine_ids, size=genuine_cluster_size, replace=False)
            for i in range(len(genuine_cluster)):
                for j in range(i + 1, len(genuine_cluster)):
                    if np.random.random() < 0.3:
                        self.graph.add_edge(genuine_cluster[i], genuine_cluster[j])

    def compute_clustering_coefficients(self) -> Dict[str, float]:
        if self.graph.number_of_nodes() == 0:
            return {}
        self._node_clustering = nx.clustering(self.graph)
        return self._node_clustering

    def get_node_clustering(self, node_id: str) -> float:
        if not self._node_clustering:
            self.compute_clustering_coefficients()
        return self._node_clustering.get(node_id, 0.0)

    def get_network_stats(self) -> dict:
        if self.graph.number_of_nodes() == 0:
            return {
                "nodes": 0,
                "edges": 0,
                "density": 0,
                "fake_node_count": 0,
                "genuine_node_count": 0,
                "fake_genuine_ratio": 0,
                "avg_clustering": 0,
                "fake_avg_clustering": 0,
                "genuine_avg_clustering": 0,
            }

        n_nodes = self.graph.number_of_nodes()
        n_edges = self.graph.number_of_edges()
        density = nx.density(self.graph)

        if not self._node_clustering:
            self.compute_clustering_coefficients()

        avg_clustering = float(np.mean(list(self._node_clustering.values()))) if self._node_clustering else 0.0

        fake_clustering = [self._node_clustering.get(n, 0.0) for n in self._fake_nodes if n in self._node_clustering]
        genuine_clustering = [self._node_clustering.get(n, 0.0) for n in self._genuine_nodes if n in self._node_clustering]

        fake_avg_clustering = float(np.mean(fake_clustering)) if fake_clustering else 0.0
        genuine_avg_clustering = float(np.mean(genuine_clustering)) if genuine_clustering else 0.0

        return {
            "nodes": n_nodes,
            "edges": n_edges,
            "density": density,
            "fake_node_count": len(self._fake_nodes),
            "genuine_node_count": len(self._genuine_nodes),
            "fake_genuine_ratio": len(self._fake_nodes) / max(len(self._genuine_nodes), 1),
            "avg_clustering": avg_clustering,
            "fake_avg_clustering": fake_avg_clustering,
            "genuine_avg_clustering": genuine_avg_clustering,
        }

    def get_clustering_bucket_stats(self) -> Dict[str, Dict[str, float]]:
        if not self._node_clustering:
            self.compute_clustering_coefficients()

        fake_vals = []
        genuine_vals = []
        suspicious_vals = []
        likely_fake_vals = []

        for node_id, clus in self._node_clustering.items():
            if node_id in self.graph:
                risk = self.graph.nodes[node_id].get("risk", "genuine")
                if risk == "fake":
                    fake_vals.append(clus)
                elif risk == "likely_fake":
                    likely_fake_vals.append(clus)
                elif risk == "suspicious":
                    suspicious_vals.append(clus)
                else:
                    genuine_vals.append(clus)

        return {
            "fake": {
                "count": len(fake_vals),
                "avg": float(np.mean(fake_vals)) if fake_vals else 0.0,
                "median": float(np.median(fake_vals)) if fake_vals else 0.0,
                "p75": float(np.percentile(fake_vals, 75)) if fake_vals else 0.0,
            },
            "likely_fake": {
                "count": len(likely_fake_vals),
                "avg": float(np.mean(likely_fake_vals)) if likely_fake_vals else 0.0,
                "median": float(np.median(likely_fake_vals)) if likely_fake_vals else 0.0,
                "p75": float(np.percentile(likely_fake_vals, 75)) if likely_fake_vals else 0.0,
            },
            "suspicious": {
                "count": len(suspicious_vals),
                "avg": float(np.mean(suspicious_vals)) if suspicious_vals else 0.0,
                "median": float(np.median(suspicious_vals)) if suspicious_vals else 0.0,
                "p75": float(np.percentile(suspicious_vals, 75)) if suspicious_vals else 0.0,
            },
            "genuine": {
                "count": len(genuine_vals),
                "avg": float(np.mean(genuine_vals)) if genuine_vals else 0.0,
                "median": float(np.median(genuine_vals)) if genuine_vals else 0.0,
                "p75": float(np.percentile(genuine_vals, 75)) if genuine_vals else 0.0,
            },
        }

    def get_node_positions(self) -> Dict[str, Tuple[float, float]]:
        if self.graph.number_of_nodes() == 0:
            return {}

        try:
            if self.graph.number_of_nodes() < 500:
                pos = nx.spring_layout(self.graph, seed=42, k=3.0 / np.sqrt(self.graph.number_of_nodes()), iterations=30)
            else:
                pos = nx.fruchterman_reingold_layout(self.graph, seed=42)
        except Exception:
            pos = nx.random_layout(self.graph, seed=42)

        return {node: (float(x), float(y)) for node, (x, y) in pos.items()}

    def detect_fake_groups(self, min_group_size: int = 5) -> List[dict]:
        if len(self._fake_nodes) < min_group_size:
            return []

        fake_subgraph = self.graph.subgraph(list(self._fake_nodes))

        if fake_subgraph.number_of_nodes() < min_group_size:
            return []

        groups = []

        try:
            core_numbers = nx.core_number(fake_subgraph)
            for k in sorted(set(core_numbers.values()), reverse=True):
                if k >= 2:
                    k_core_nodes = [n for n, c in core_numbers.items() if c >= k]
                    if len(k_core_nodes) >= min_group_size:
                        k_core_subgraph = fake_subgraph.subgraph(k_core_nodes)
                        components = list(nx.connected_components(k_core_subgraph))
                        for comp in components:
                            if len(comp) >= min_group_size:
                                density = nx.density(k_core_subgraph.subgraph(comp))
                                avg_degree = np.mean([d for n, d in k_core_subgraph.subgraph(comp).degree()])
                                groups.append({
                                    "group_id": f"k{k}_group_{len(groups)}",
                                    "core_level": k,
                                    "nodes": list(comp),
                                    "size": len(comp),
                                    "density": density,
                                    "avg_degree": avg_degree,
                                    "fake_ratio": 1.0,
                                })
                    break
        except Exception:
            pass

        if not groups:
            try:
                components = list(nx.connected_components(fake_subgraph))
                for i, comp in enumerate(components):
                    if len(comp) >= min_group_size:
                        comp_subgraph = fake_subgraph.subgraph(comp)
                        density = nx.density(comp_subgraph)
                        avg_degree = np.mean([d for n, d in comp_subgraph.degree()])
                        groups.append({
                            "group_id": f"conn_group_{i}",
                            "core_level": 1,
                            "nodes": list(comp),
                            "size": len(comp),
                            "density": density,
                            "avg_degree": avg_degree,
                            "fake_ratio": 1.0,
                        })
            except Exception:
                pass

        return sorted(groups, key=lambda x: x["size"], reverse=True)

    def get_group_metrics(self, groups: List[dict]) -> dict:
        if not groups:
            return {
                "total_groups": 0,
                "largest_group_size": 0,
                "avg_group_size": 0,
                "total_grouped_nodes": 0,
                "grouped_ratio": 0,
            }

        sizes = [g["size"] for g in groups]
        total_grouped = sum(sizes)

        return {
            "total_groups": len(groups),
            "largest_group_size": max(sizes) if sizes else 0,
            "avg_group_size": float(np.mean(sizes)) if sizes else 0,
            "total_grouped_nodes": total_grouped,
            "grouped_ratio": total_grouped / max(len(self._fake_nodes), 1),
        }

    def get_node_group_membership(self, groups: List[dict]) -> Dict[str, List[str]]:
        membership = {}
        for group in groups:
            for node in group["nodes"]:
                if node not in membership:
                    membership[node] = []
                membership[node].append(group["group_id"])
        return membership
