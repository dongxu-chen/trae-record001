import numpy as np
import sys
import os
from datetime import datetime, timedelta
import networkx as nx

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import NUM_ROADS, CONGESTION_MAX
from models.graph_builder import build_adjacency_matrix, build_directed_road_network


class TrafficEvent:
    def __init__(self, event_type, road_id, start_time, duration_minutes, severity=1, affected_lanes=1):
        self.event_type = event_type
        self.road_id = road_id
        self.start_time = start_time
        self.duration_minutes = duration_minutes
        self.severity = severity
        self.affected_lanes = affected_lanes
        self.end_time = start_time + timedelta(minutes=duration_minutes)

    def is_active(self, current_time):
        return self.start_time <= current_time <= self.end_time

    def get_congestion_impact(self):
        base_impact = {
            "accident": 3.0,
            "road_closure": 8.0,
            "construction": 2.5,
            "special_event": 2.0,
            "weather": 1.5,
        }
        return min(CONGESTION_MAX, base_impact.get(self.event_type, 2.0) * self.severity)


class EventSimulator:
    def __init__(self, num_roads=NUM_ROADS):
        self.num_roads = num_roads
        self.adj_matrix = build_adjacency_matrix(num_roads)
        self.graph = nx.from_numpy_array(self.adj_matrix, create_using=nx.DiGraph)
        self.events = []

    def add_event(self, event):
        self.events.append(event)
        return event

    def add_events(self, events):
        self.events.extend(events)

    def clear_events(self):
        self.events = []

    def get_active_events(self, current_time):
        return [e for e in self.events if e.is_active(current_time)]

    def get_affected_roads(self, current_time):
        active_events = self.get_active_events(current_time)
        affected = {}
        for event in active_events:
            impact = event.get_congestion_impact()
            affected[event.road_id] = max(affected.get(event.road_id, 0), impact)
        return affected

    def simulate_impact_propagation(self, current_time, base_congestion, max_distance=3):
        affected_roads = self.get_affected_roads(current_time)
        impact_map = np.zeros(self.num_roads)

        for road_id, direct_impact in affected_roads.items():
            impact_map[road_id] = direct_impact

            for distance in range(1, max_distance + 1):
                decay_factor = 1.0 / (distance + 1)
                neighbors = self._get_neighbors_at_distance(road_id, distance)
                for neighbor in neighbors:
                    propagated_impact = direct_impact * decay_factor * 0.7
                    if propagated_impact > impact_map[neighbor]:
                        impact_map[neighbor] = propagated_impact

        simulated_congestion = base_congestion.copy()
        for i in range(self.num_roads):
            if impact_map[i] > 0:
                simulated_congestion[i] = min(CONGESTION_MAX, simulated_congestion[i] + impact_map[i])

        return simulated_congestion, impact_map

    def _get_neighbors_at_distance(self, node, distance):
        try:
            lengths = nx.single_source_shortest_path_length(self.graph, node, cutoff=distance)
            return [n for n, d in lengths.items() if d == distance]
        except:
            return []

    def predict_impact_range(self, event, base_congestion):
        impact_history = []
        time_points = []
        current = event.start_time

        while current <= event.end_time:
            simulated, impact = self.simulate_impact_propagation(current, base_congestion)
            impact_history.append({
                "time": current,
                "congestion": simulated,
                "impact_map": impact,
                "affected_count": np.sum(impact > 0.5)
            })
            time_points.append(current)
            current += timedelta(minutes=5)

        max_affected = max([h["affected_count"] for h in impact_history]) if impact_history else 0
        peak_time = impact_history[np.argmax([h["affected_count"] for h in impact_history])]["time"] if impact_history else None

        return {
            "event": event,
            "impact_history": impact_history,
            "max_affected_roads": max_affected,
            "peak_time": peak_time,
            "estimated_recovery_time": event.end_time + timedelta(minutes=30)
        }

    def generate_event_report(self, event, base_congestion):
        prediction = self.predict_impact_range(event, base_congestion)

        report = f"""
交通事件影响分析报告
{'='*50}
事件类型: {event.event_type}
事件位置: 路段 {event.road_id}
开始时间: {event.start_time.strftime('%Y-%m-%d %H:%M')}
预计结束: {event.end_time.strftime('%Y-%m-%d %H:%M')}
持续时间: {event.duration_minutes} 分钟
严重程度: {event.severity} 级

影响分析:
- 最大影响路段数: {prediction['max_affected_roads']} 条
- 影响峰值时间: {prediction['peak_time'].strftime('%Y-%m-%d %H:%M') if prediction['peak_time'] else '未知'}
- 预计完全恢复: {prediction['estimated_recovery_time'].strftime('%Y-%m-%d %H:%M')}

建议:
{self._generate_recommendations(event, prediction)}
"""
        return report, prediction

    def _generate_recommendations(self, event, prediction):
        recommendations = []
        if event.event_type == "road_closure":
            recommendations.append(f"⚠️  路段 {event.road_id} 完全封闭，请提前规划绕行路线")
        elif event.event_type == "accident":
            recommendations.append(f"⚠️  路段 {event.road_id} 发生事故，请减速慢行或绕行")
        elif event.event_type == "construction":
            recommendations.append(f"⚠️  路段 {event.road_id} 施工中，请提前出行")

        if prediction["max_affected_roads"] > 5:
            recommendations.append(f"📢 预计影响范围较大，建议避开该区域")

        recommendations.append(f"🕐 预计 {event.duration_minutes} 分钟后恢复正常")
        return "\n".join(recommendations)


if __name__ == "__main__":
    simulator = EventSimulator()

    base_congestion = np.random.uniform(0, 4, NUM_ROADS)

    event1 = TrafficEvent(
        event_type="accident",
        road_id=5,
        start_time=datetime(2024, 1, 1, 8, 0),
        duration_minutes=60,
        severity=2
    )

    simulator.add_event(event1)

    report, prediction = simulator.generate_event_report(event1, base_congestion)
    print(report)
