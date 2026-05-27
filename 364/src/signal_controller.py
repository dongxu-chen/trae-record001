import simpy
import numpy as np
from collections import defaultdict


class SignalController:
    def __init__(self, env, signal_config, roads_data):
        self.env = env
        self.signal_config = signal_config
        self.roads_data = roads_data
        self.signals = {}
        self.queue_history = defaultdict(list)
        self.waiting_times = defaultdict(list)
        self._initialize_signals()

    def _initialize_signals(self):
        for signal in self.signal_config.get("signals", []):
            signal_id = signal["id"]
            self.signals[signal_id] = {
                "id": signal_id,
                "intersection_id": signal["intersection_id"],
                "phases": signal["phases"],
                "current_phase": 0,
                "state": "green",
                "controlled_roads": signal.get("controlled_roads", []),
            }

    def run(self):
        for signal_id in self.signals:
            self.env.process(self._signal_cycle(signal_id))
        self.env.process(self._monitor_queues())

    def _signal_cycle(self, signal_id):
        signal = self.signals[signal_id]
        while True:
            phases = signal["phases"]
            current_phase = phases[signal["current_phase"]]

            green_roads = current_phase.get("directions", {}).get("green", [])
            red_roads = current_phase.get("directions", {}).get("red", [])

            if isinstance(green_roads, str):
                green_roads = [green_roads]
            if isinstance(red_roads, str):
                red_roads = [red_roads]

            signal["green_roads"] = green_roads
            signal["red_roads"] = red_roads

            for road_id in green_roads:
                if road_id in self.roads_data:
                    self.roads_data[road_id]["signal_state"] = "green"

            for road_id in red_roads:
                if road_id in self.roads_data:
                    self.roads_data[road_id]["signal_state"] = "red"

            yield self.env.timeout(current_phase["duration"])

            signal["current_phase"] = (signal["current_phase"] + 1) % len(phases)

    def _monitor_queues(self):
        while True:
            for road_id, road in self.roads_data.items():
                queue_len = road.get("queue_length", 0)
                self.queue_history[road_id].append({
                    "time": self.env.now,
                    "queue_length": queue_len
                })
            yield self.env.timeout(1)

    def get_signal_states(self):
        states = {}
        for signal_id, signal in self.signals.items():
            states[signal_id] = {
                "current_phase": signal["current_phase"],
                "green_roads": signal.get("green_roads", []),
                "red_roads": signal.get("red_roads", []),
                "time": self.env.now
            }
        return states

    def get_average_queue_length(self, road_id=None):
        if road_id:
            history = self.queue_history.get(road_id, [])
            if not history:
                return 0
            return float(np.mean([h["queue_length"] for h in history]))
        else:
            all_queues = []
            for hist in self.queue_history.values():
                all_queues.extend([h["queue_length"] for h in hist])
            return float(np.mean(all_queues)) if all_queues else 0

    def get_max_queue_length(self, road_id=None):
        if road_id:
            history = self.queue_history.get(road_id, [])
            if not history:
                return 0
            return float(np.max([h["queue_length"] for h in history]))
        else:
            max_val = 0
            for hist in self.queue_history.values():
                for h in hist:
                    max_val = max(max_val, h["queue_length"])
            return float(max_val)


class DiscreteEventSimulator:
    def __init__(self, network_config, signal_config, od_matrix):
        self.network_config = network_config
        self.signal_config = signal_config
        self.od_matrix = od_matrix
        self.env = simpy.Environment()
        self.roads_data = {}
        self.vehicles = []
        self.completed_vehicles = []
        self.arrival_events = []
        self._initialize_roads()
        self.signal_controller = SignalController(self.env, signal_config, self.roads_data)

    def _initialize_roads(self):
        for road in self.network_config.get("roads", []):
            self.roads_data[road["id"]] = {
                "id": road["id"],
                "name": road.get("name", f"Road_{road['id']}"),
                "length": road["length"],
                "capacity": road.get("capacity", road["length"]),
                "speed_limit": road.get("speed_limit", 14),
                "queue_length": 0,
                "flow_rate": 0,
                "signal_state": "green",
                "vehicles": [],
                "total_wait_time": 0,
            }

    def _generate_vehicle_arrivals(self, duration):
        for origin, destinations in self.od_matrix.items():
            for destination, rate in destinations.items():
                if rate <= 0:
                    continue
                inter_arrival_time = max(1, int(1 / rate)) if rate > 0 else float('inf')
                t = 0
                while t < duration:
                    t += np.random.poisson(inter_arrival_time)
                    if t < duration:
                        self.arrival_events.append((t, origin, destination))
        self.arrival_events.sort(key=lambda x: x[0])

    def _vehicle_process(self, vehicle_id, origin, destination):
        arrival_time = self.env.now

        current_road = self._get_road_from_node(origin)
        if not current_road:
            return

        road = self.roads_data[current_road]
        road["queue_length"] += 1

        while road["signal_state"] == "red":
            yield self.env.timeout(1)

        wait_time = self.env.now - arrival_time
        road["total_wait_time"] += wait_time

        travel_time = max(1, int(road["length"] / road["speed_limit"]))
        yield self.env.timeout(travel_time)

        road["queue_length"] -= 1

        current_node = self._get_end_node(current_road)
        path = self._find_path(current_node, destination)

        for next_road_id in path[1:]:
            if next_road_id not in self.roads_data:
                break
            road = self.roads_data[next_road_id]
            road["queue_length"] += 1
            road["flow_rate"] += 1

            arrival_time = self.env.now
            while road["signal_state"] == "red":
                yield self.env.timeout(1)

            wait_time = self.env.now - arrival_time
            road["total_wait_time"] += wait_time

            travel_time = max(1, int(road["length"] / road["speed_limit"]))
            yield self.env.timeout(travel_time)
            road["queue_length"] -= 1

        self.completed_vehicles.append({
            "id": vehicle_id,
            "origin": origin,
            "destination": destination,
            "total_time": self.env.now - arrival_time,
        })

    def _get_road_from_node(self, node):
        for road in self.network_config.get("roads", []):
            if road["start_node"] == node:
                return road["id"]
        return None

    def _get_end_node(self, road_id):
        for road in self.network_config.get("roads", []):
            if road["id"] == road_id:
                return road["end_node"]
        return None

    def _find_path(self, start, end):
        roads = self.network_config.get("roads", [])
        graph = defaultdict(list)
        for road in roads:
            graph[road["start_node"]].append((road["end_node"], road["id"]))

        queue = [(start, [])]
        visited = set()
        while queue:
            node, path = queue.pop(0)
            if node in visited:
                continue
            visited.add(node)
            if node == end:
                return path
            for next_node, road_id in graph[node]:
                if next_node not in visited:
                    queue.append((next_node, path + [road_id]))
        return []

    def _arrival_process(self):
        idx = 0
        vehicle_id = 0
        while idx < len(self.arrival_events):
            event_time, origin, destination = self.arrival_events[idx]
            yield self.env.timeout(max(0, event_time - self.env.now))
            self.env.process(self._vehicle_process(vehicle_id, origin, destination))
            vehicle_id += 1
            idx += 1

    def run(self, duration):
        self._generate_vehicle_arrivals(duration)
        self.signal_controller.run()
        self.env.process(self._arrival_process())
        self.env.run(until=duration)
        return self.get_results()

    def get_results(self):
        road_metrics = {}
        for road_id, road in self.roads_data.items():
            avg_wait = road["total_wait_time"] / max(1, road["flow_rate"]) if road["flow_rate"] > 0 else 0
            road_metrics[road_id] = {
                "name": road["name"],
                "average_queue_length": self.signal_controller.get_average_queue_length(road_id),
                "max_queue_length": self.signal_controller.get_max_queue_length(road_id),
                "flow_rate": road["flow_rate"],
                "average_wait_time": avg_wait,
                "final_queue_length": road["queue_length"],
            }

        signal_metrics = self.signal_controller.get_signal_states()

        total_completed = len(self.completed_vehicles)
        avg_travel_time = float(np.mean([v["total_time"] for v in self.completed_vehicles])) if self.completed_vehicles else 0

        return {
            "road_metrics": road_metrics,
            "signal_states": signal_metrics,
            "total_completed": total_completed,
            "average_travel_time": avg_travel_time,
            "overall_avg_queue": self.signal_controller.get_average_queue_length(),
            "overall_max_queue": self.signal_controller.get_max_queue_length(),
            "queue_history": dict(self.signal_controller.queue_history),
        }
