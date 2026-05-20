import numpy as np
import sys
import os
from datetime import datetime, timedelta
import networkx as nx
from heapq import heappush, heappop

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NUM_ROADS, CONGESTION_MAX, PRED_HORIZONS
from models.graph_builder import build_adjacency_matrix


class PathPlanner:
    def __init__(self, num_roads=NUM_ROADS):
        self.num_roads = num_roads
        self.adj_matrix = build_adjacency_matrix(num_roads)
        self.graph = nx.from_numpy_array(self.adj_matrix, create_using=nx.DiGraph)
        self._set_edge_weights()

    def _set_edge_weights(self, congestion_data=None):
        for u, v in self.graph.edges():
            base_weight = 1.0
            if congestion_data is not None:
                congestion_factor = 1.0 + (congestion_data[u] + congestion_data[v]) / (2 * CONGESTION_MAX) * 3.0
                weight = base_weight * congestion_factor
            else:
                weight = base_weight
            self.graph[u][v]["weight"] = weight

    def update_congestion(self, congestion_data):
        self._set_edge_weights(congestion_data)

    def find_shortest_path(self, start, end, algorithm="dijkstra"):
        try:
            if algorithm == "dijkstra":
                path = nx.dijkstra_path(self.graph, start, end, weight="weight")
                length = nx.dijkstra_path_length(self.graph, start, end, weight="weight")
            elif algorithm == "astar":
                path = nx.astar_path(self.graph, start, end, weight="weight")
                length = nx.astar_path_length(self.graph, start, end, weight="weight")
            else:
                path = nx.shortest_path(self.graph, start, end, weight="weight")
                length = nx.shortest_path_length(self.graph, start, end, weight="weight")
            return path, length
        except nx.NetworkXNoPath:
            return None, float("inf")

    def find_optimal_path(self, start, end, predictions, current_time, time_horizon_idx=0):
        if predictions is None:
            return self.find_shortest_path(start, end)

        best_path = None
        best_score = float("inf")
        best_congestion = 0.0

        base_path, base_length = self.find_shortest_path(start, end)
        if base_path is None:
            return None, None

        base_congestion = self._calculate_path_congestion(base_path, predictions, time_horizon_idx)
        base_score = base_length * (1.0 + base_congestion / CONGESTION_MAX)

        candidate_paths = self._generate_candidate_paths(start, end, max_candidates=5)

        for path in candidate_paths:
            path_congestion = self._calculate_path_congestion(path, predictions, time_horizon_idx)
            path_length = len(path) - 1
            path_score = path_length * (1.0 + path_congestion / CONGESTION_MAX)

            if path_score < best_score:
                best_score = path_score
                best_path = path
                best_congestion = path_congestion

        if best_path is None:
            best_path = base_path
            best_congestion = base_congestion

        return best_path, best_congestion

    def _generate_candidate_paths(self, start, end, max_candidates=5):
        candidates = []
        try:
            paths = list(nx.all_simple_paths(self.graph, start, end, cutoff=10))
            for path in paths[:max_candidates]:
                candidates.append(path)
        except:
            pass
        return candidates

    def _calculate_path_congestion(self, path, predictions, horizon_idx):
        if predictions is None or len(path) == 0:
            return 0.0

        total_congestion = 0.0
        count = 0

        for node in path:
            if node < len(predictions):
                total_congestion += predictions[node, horizon_idx]
                count += 1

        return total_congestion / max(count, 1) if count > 0 else 0.0

    def plan_multi_horizon(self, start, end, predictions, current_time):
        results = []

        for h_idx, horizon in enumerate(PRED_HORIZONS):
            path, avg_congestion = self.find_optimal_path(start, end, predictions, current_time, h_idx)

            if path is not None:
                estimated_time = self._estimate_travel_time(path, avg_congestion)
                results.append({
                    "horizon": horizon,
                    "path": path,
                    "avg_congestion": avg_congestion,
                    "estimated_time": estimated_time,
                    "congestion_level": self._get_congestion_level(avg_congestion)
                })

        return results

    def _estimate_travel_time(self, path, avg_congestion):
        base_time = (len(path) - 1) * 2.0
        congestion_factor = 1.0 + avg_congestion / CONGESTION_MAX * 2.0
        return base_time * congestion_factor

    def _get_congestion_level(self, congestion):
        if congestion < 2:
            return "顺畅"
        elif congestion < 4:
            return "轻微"
        elif congestion < 6:
            return "中度"
        elif congestion < 8:
            return "严重"
        else:
            return "极度严重"

    def generate_route_guidance(self, start, end, predictions, current_time):
        multi_horizon = self.plan_multi_horizon(start, end, predictions, current_time)

        guidance = f"""
路线规划报告
{'='*50}
起点: 路段 {start}
终点: 路段 {end}
规划时间: {current_time.strftime('%Y-%m-%d %H:%M')}

推荐路线 (15分钟预测):
{self._format_route(multi_horizon[0]) if len(multi_horizon) > 0 else '无可用路线'}

备选方案:
"""
        for i, result in enumerate(multi_horizon[1:], 1):
            guidance += f"\n{i}. {PRED_HORIZONS[i]}分钟预测: {self._format_route(result, brief=True)}"

        guidance += f"\n\n建议: {self._generate_advice(multi_horizon)}"

        return guidance, multi_horizon

    def _format_route(self, result, brief=False):
        if result is None:
            return "无可用路线"

        path_str = " → ".join([f"路段{node}" for node in result["path"]])
        if brief:
            return f"{path_str} | 拥堵: {result['congestion_level']} | 预计: {result['estimated_time']:.1f}分钟"
        return f"""
  路线: {path_str}
  平均拥堵指数: {result['avg_congestion']:.2f} ({result['congestion_level']})
  预计行驶时间: {result['estimated_time']:.1f} 分钟
  经过路段数: {len(result['path']) - 1}
"""

    def _generate_advice(self, results):
        if not results:
            return "当前无可用路线建议"

        best = min(results, key=lambda x: x["estimated_time"])
        worst = max(results, key=lambda x: x["avg_congestion"])

        advice = []
        if best["avg_congestion"] < 4:
            advice.append(f"推荐选择 {best['horizon']}分钟 预测的路线，路况{best['congestion_level']}")
        else:
            advice.append(f"建议错峰出行，当前预测路况{best['congestion_level']}")

        if worst["avg_congestion"] > 7:
            advice.append(f"注意：{worst['horizon']}分钟后拥堵可能加剧")

        return "；".join(advice)

    def find_alternative_routes(self, start, end, blocked_roads, predictions, horizon_idx=0):
        original_edges = list(self.graph.edges())

        for road in blocked_roads:
            edges_to_remove = []
            for u, v in self.graph.edges():
                if u == road or v == road:
                    edges_to_remove.append((u, v))
            self.graph.remove_edges_from(edges_to_remove)

        try:
            path, length = self.find_shortest_path(start, end)
            avg_congestion = self._calculate_path_congestion(path, predictions, horizon_idx) if path else 0
        except:
            path, length, avg_congestion = None, float("inf"), 0

        self.graph.add_edges_from(original_edges)
        self._set_edge_weights(predictions[:, horizon_idx] if predictions is not None else None)

        return path, avg_congestion


if __name__ == "__main__":
    planner = PathPlanner()

    predictions = np.random.uniform(0, 8, (NUM_ROADS, 3))
    current_time = datetime(2024, 1, 1, 8, 0)

    guidance, results = planner.generate_route_guidance(0, 15, predictions, current_time)
    print(guidance)

    print("\n" + "=" * 50)
    print("测试封路绕行:")
    blocked = [5, 6]
    alt_path, alt_congestion = planner.find_alternative_routes(0, 15, blocked, predictions)
    print(f"绕行路线: {alt_path}")
    print(f"平均拥堵: {alt_congestion:.2f}")
