import mesa
import numpy as np
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from .vehicle import Vehicle, Bus
from .emission_model import EmissionModel


class RoadSegment:
    def __init__(self, road_id, segment_id, start_pos, end_pos):
        self.road_id = road_id
        self.segment_id = segment_id
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.vehicles = []
        self.lock = threading.Lock()

    def add_vehicle(self, vehicle):
        with self.lock:
            self.vehicles.append(vehicle)

    def remove_vehicle(self, vehicle):
        with self.lock:
            if vehicle in self.vehicles:
                self.vehicles.remove(vehicle)

    def update_vehicles(self, model):
        with self.lock:
            vehicles_to_process = list(self.vehicles)

        for vehicle in vehicles_to_process:
            if vehicle.position >= self.start_pos and vehicle.position < self.end_pos:
                road = model.roads[vehicle.road_id]

                if vehicle.status == "waiting_at_signal":
                    vehicle.wait_time += 1
                    vehicle.speed = 0
                    continue

                vehicle.travel_time += 1

                if road.get("lanes", 1) > 1:
                    vehicle._consider_lane_change(road)

                front_vehicle = vehicle._get_front_vehicle(road)
                signal_state = vehicle._check_signal(road)

                vehicle._update_speed(front_vehicle, signal_state, road)
                vehicle._move(road)

                if vehicle.speed > 0:
                    vehicle.total_distance += vehicle.speed

                vehicle.history.append({
                    "time": model.schedule.time,
                    "position": vehicle.position,
                    "speed": vehicle.speed,
                    "road_id": vehicle.road_id,
                    "lane": vehicle.lane
                })


class VariableLaneManager:
    def __init__(self, roads):
        self.roads = roads
        self.lane_configs = {}
        self.lane_change_history = defaultdict(list)
        self.dynamic_lane_enabled = True
        self.evaluation_interval = 50
        self.last_evaluation = 0

        for road_id, road in roads.items():
            num_lanes = road.get("lanes", 1)
            self.lane_configs[road_id] = {
                "lane_directions": ["forward"] * num_lanes,
                "lane_types": ["general"] * num_lanes,
                "bus_lane": road.get("bus_lane", -1),
                "reversible_lanes": road.get("reversible_lanes", []),
                "dynamic_enabled": road.get("dynamic_lanes", False)
            }

            bus_lane = road.get("bus_lane", -1)
            if bus_lane >= 0 and bus_lane < num_lanes:
                self.lane_configs[road_id]["lane_types"][bus_lane] = "bus"

            for rev_lane in road.get("reversible_lanes", []):
                if rev_lane < num_lanes:
                    self.lane_configs[road_id]["lane_types"][rev_lane] = "reversible"

    def evaluate_and_adjust(self, current_time, queue_lengths):
        if not self.dynamic_lane_enabled:
            return

        if current_time - self.last_evaluation < self.evaluation_interval:
            return

        self.last_evaluation = current_time
        changes_made = []

        for road_id, config in self.lane_configs.items():
            if not config["dynamic_enabled"]:
                continue

            road = self.roads.get(road_id)
            if not road:
                continue

            queue = queue_lengths.get(road_id, 0)
            capacity = road.get("capacity", 100)
            density = queue / capacity if capacity > 0 else 0

            if density > 0.7:
                change = self._convert_lane_to_forward(road_id, config)
                if change:
                    changes_made.append(change)
            elif density < 0.2:
                change = self._convert_lane_to_opposite(road_id, config)
                if change:
                    changes_made.append(change)

        for change in changes_made:
            self.lane_change_history[change["road_id"]].append({
                "time": current_time,
                "lane": change["lane"],
                "old_type": change["old_type"],
                "new_type": change["new_type"],
                "reason": change["reason"]
            })

        return changes_made

    def _convert_lane_to_forward(self, road_id, config):
        for i, lane_type in enumerate(config["lane_types"]):
            if lane_type == "reversible":
                old_type = lane_type
                config["lane_types"][i] = "forward"
                config["lane_directions"][i] = "forward"
                return {
                    "road_id": road_id,
                    "lane": i,
                    "old_type": old_type,
                    "new_type": "forward",
                    "reason": "high_density"
                }
        return None

    def _convert_lane_to_opposite(self, road_id, config):
        forward_count = sum(1 for d in config["lane_directions"] if d == "forward")
        if forward_count <= 1:
            return None

        for i, lane_type in enumerate(config["lane_types"]):
            if lane_type == "forward" and i != config["bus_lane"]:
                old_type = lane_type
                config["lane_types"][i] = "reversible"
                config["lane_directions"][i] = "opposite"
                return {
                    "road_id": road_id,
                    "lane": i,
                    "old_type": old_type,
                    "new_type": "reversible",
                    "reason": "low_density"
                }
        return None

    def is_bus_lane(self, road_id, lane):
        config = self.lane_configs.get(road_id, {})
        lane_types = config.get("lane_types", [])
        if 0 <= lane < len(lane_types):
            return lane_types[lane] == "bus"
        return False

    def can_vehicle_use_lane(self, vehicle, road_id, lane):
        config = self.lane_configs.get(road_id, {})
        lane_types = config.get("lane_types", [])

        if 0 <= lane < len(lane_types):
            lane_type = lane_types[lane]
            if lane_type == "bus":
                return getattr(vehicle, 'is_bus', lambda: False)()
            elif lane_type == "reversible":
                direction = config.get("lane_directions", [])[lane]
                return direction == "forward"
        return True

    def get_lane_status(self, road_id):
        return self.lane_configs.get(road_id, {})

    def get_change_history(self, road_id=None):
        if road_id:
            return self.lane_change_history.get(road_id, [])
        return dict(self.lane_change_history)


class BusPriorityManager:
    def __init__(self, signals):
        self.signals = signals
        self.priority_requests = defaultdict(list)
        self.priority_granted = 0
        self.priority_denied = 0
        self.min_green_extension = 5
        self.max_green_extension = 15
        self.min_red_truncation = 3
        self.bus_queue_threshold = 2
        self.wait_time_threshold = 15

    def request_priority(self, signal_id, bus):
        request = {
            "bus_id": bus.unique_id,
            "road_id": bus.road_id,
            "request_time": bus.model.schedule.time,
            "wait_time": getattr(bus, 'current_signal_wait', 0),
            "passenger_count": getattr(bus, 'passenger_count', 0)
        }
        self.priority_requests[signal_id].append(request)
        self._evaluate_priority(signal_id, bus, request)

    def _evaluate_priority(self, signal_id, bus, request):
        signal = self.signals.get(signal_id)
        if not signal:
            self.priority_denied += 1
            return False

        road_id = bus.road_id
        is_green_road = road_id in signal.get("green_roads", [])

        bus_queue = self._count_buses_at_signal(signal, road_id)
        should_grant = False

        if signal["state"] == "green" and is_green_road:
            if bus_queue >= self.bus_queue_threshold or request["wait_time"] >= self.wait_time_threshold:
                should_grant = True
                self._extend_green_phase(signal, road_id)
        elif signal["state"] == "red":
            if bus_queue >= self.bus_queue_threshold + 1 or request["wait_time"] >= self.wait_time_threshold + 5:
                should_grant = True
                self._truncate_red_phase(signal, road_id)

        if should_grant:
            self.priority_granted += 1
            return True
        else:
            self.priority_denied += 1
            return False

    def _count_buses_at_signal(self, signal, road_id):
        count = 0
        controlled_roads = signal.get("controlled_roads", [])
        for rid in controlled_roads:
            for vehicle in signal.get("model", type('Dummy', (), {'roads': {}})).roads.get(rid, {}).get("vehicles", []):
                if getattr(vehicle, 'is_bus', lambda: False)() and vehicle.road_id == road_id:
                    count += 1
        return count

    def _extend_green_phase(self, signal, road_id):
        current_phase = signal["phases"][signal["current_phase"]]
        current_phase["duration"] = min(
            current_phase["duration"] + self.min_green_extension,
            current_phase["duration"] + self.max_green_extension
        )
        signal["cycle_length"] = sum(p["duration"] for p in signal["phases"])
        signal["priority_extended"] = True

    def _truncate_red_phase(self, signal, road_id):
        phases = signal["phases"]
        for i, phase in enumerate(phases):
            if road_id in phase.get("directions", {}).get("green", []):
                red_duration = phases[(i - 1) % len(phases)]["duration"]
                phases[(i - 1) % len(phases)]["duration"] = max(
                    10, red_duration - self.min_red_truncation
                )
                break
        signal["cycle_length"] = sum(p["duration"] for p in signal["phases"])
        signal["priority_truncated"] = True

    def get_statistics(self):
        total = self.priority_granted + self.priority_denied
        return {
            "total_requests": total,
            "granted": self.priority_granted,
            "denied": self.priority_denied,
            "grant_rate": self.priority_granted / max(1, total)
        }

    def clear_requests(self, signal_id=None):
        if signal_id:
            self.priority_requests[signal_id] = []
        else:
            self.priority_requests.clear()


class ParallelTrafficModel(mesa.Model):
    def __init__(self, network_config, signal_config, od_matrix, sim_config=None):
        super().__init__()
        self.network_config = network_config
        self.signal_config = signal_config
        self.od_matrix = od_matrix
        self.sim_config = sim_config or {"max_speed": 14, "generation_rate": 0.3}

        self.segment_size = 20
        self.num_workers = min(4, len(network_config.get("roads", [])))
        self.executor = ThreadPoolExecutor(max_workers=self.num_workers)

        self.roads = {}
        self.road_segments = {}
        self.signals = {}
        self.nodes = {}
        self.vehicle_id_counter = 0
        self.completed_vehicles = []
        self.use_parallel = sim_config.get("use_parallel", True) if sim_config else True
        self._vehicles_to_remove = []
        self._remove_lock = threading.Lock()

        self.datacollector = mesa.DataCollector(
            model_reporters={
                "TotalVehicles": lambda m: len(m.agents),
                "AvgSpeed": lambda m: m._calculate_avg_speed(),
                "CongestionIndex": lambda m: m._calculate_congestion_index(),
            },
            agent_reporters={
                "Speed": "speed",
                "Position": "position",
                "RoadID": "road_id",
            }
        )

        self.schedule = mesa.time.RandomActivation(self)
        self._agent_count = 0
        self._initialize_network()
        self._initialize_signals()

        self.variable_lane_manager = VariableLaneManager(self.roads)
        self.bus_priority_manager = BusPriorityManager(self.signals)
        self.emission_model = EmissionModel()

        for signal in self.signals.values():
            signal["model"] = self

        self.enable_bus_priority = sim_config.get("enable_bus_priority", True) if sim_config else True
        self.enable_variable_lanes = sim_config.get("enable_variable_lanes", True) if sim_config else True
        self.enable_emission_calc = sim_config.get("enable_emission_calc", True) if sim_config else True
        self.bus_generation_rate = sim_config.get("bus_generation_rate", 0.1) if sim_config else 0.1

        self._initialize_vehicles()
        self.emission_history = []
        self.lane_change_events = []

    def _initialize_network(self):
        for node in self.network_config.get("nodes", []):
            self.nodes[node["id"]] = node

        for road in self.network_config.get("roads", []):
            road_id = road["id"]
            num_lanes = road.get("lanes", 1)

            self.roads[road_id] = {
                "id": road_id,
                "name": road.get("name", f"Road_{road_id}"),
                "start_node": road["start_node"],
                "end_node": road["end_node"],
                "length": road["length"],
                "lanes": num_lanes,
                "capacity": road.get("capacity", road["length"] * num_lanes),
                "speed_limit": road.get("speed_limit", 14),
                "has_signal": road.get("has_signal", False),
                "signal_id": road.get("signal_id"),
                "vehicles": [],
                "lane_vehicles": {i: [] for i in range(num_lanes)},
                "signal_state": "green",
                "coordinates": road.get("coordinates", []),
                "bus_lane": road.get("bus_lane", -1),
                "reversible_lanes": road.get("reversible_lanes", []),
                "dynamic_lanes": road.get("dynamic_lanes", False),
                "bus_stops": road.get("bus_stops", []),
            }

            self._create_road_segments(road_id, road["length"])

    def _create_road_segments(self, road_id, road_length):
        segments = []
        for i in range(0, road_length, self.segment_size):
            seg_id = f"{road_id}_seg_{i // self.segment_size}"
            segment = RoadSegment(
                road_id, seg_id,
                start_pos=i,
                end_pos=min(i + self.segment_size, road_length)
            )
            segments.append(segment)
        self.road_segments[road_id] = segments

    def _initialize_signals(self):
        for signal in self.signal_config.get("signals", []):
            signal_id = signal["id"]
            phases = signal["phases"]

            total_duration = sum(phase.get("duration", 30) for phase in phases)
            green_ratio = {}
            for i, phase in enumerate(phases):
                duration = phase.get("duration", 30)
                green_ratio[f"phase_{i}"] = duration / total_duration if total_duration > 0 else 0

            self.signals[signal_id] = {
                "id": signal_id,
                "intersection_id": signal["intersection_id"],
                "phases": phases,
                "current_phase": 0,
                "phase_timer": 0,
                "phase_offset": signal.get("phase_offset", 0),
                "state": "green",
                "controlled_roads": signal.get("controlled_roads", []),
                "total_duration": total_duration,
                "green_ratio": green_ratio,
                "cycle_length": total_duration,
            }

    def _initialize_vehicles(self):
        num_initial = int(len(self.roads) * 2)
        for _ in range(num_initial):
            self._generate_vehicle()

    def _generate_vehicle(self, origin=None, destination=None, vehicle_type=None):
        if not self.roads:
            return None

        if vehicle_type is None:
            if np.random.random() < self.bus_generation_rate:
                vehicle_type = np.random.choice(['bus', 'bus_hybrid', 'bus_electric'])
            else:
                vehicle_type = 'passenger_car'

        if origin is None and self.od_matrix:
            origins = list(self.od_matrix.keys())
            if not origins:
                return None
            origin = np.random.choice(origins)

        if destination is None and self.od_matrix and origin in self.od_matrix:
            dests = list(self.od_matrix[origin].keys())
            weights = list(self.od_matrix[origin].values())
            total = sum(weights)
            if total > 0:
                weights = [w / total for w in weights]
                destination = np.random.choice(dests, p=weights)

        available_roads = [rid for rid, r in self.roads.items()
                           if r["start_node"] == origin] if origin else list(self.roads.keys())

        if not available_roads:
            return None

        road_id = np.random.choice(available_roads)
        road = self.roads[road_id]

        if len(road["vehicles"]) >= road["capacity"]:
            return None

        max_speed = self.sim_config.get("max_speed", 14)

        if vehicle_type in ['bus', 'bus_hybrid', 'bus_electric']:
            lane = road.get("bus_lane", 0) if road.get("bus_lane", -1) >= 0 else 0

            bus_stops = self._generate_bus_stops(road_id, origin, destination)

            vehicle = Bus(
                self,
                road_id,
                position=0,
                max_speed=min(max_speed, 10),
                origin=origin,
                destination=destination,
                lane=lane,
                bus_type=vehicle_type,
                route_id=f"Route_{np.random.randint(100, 999)}",
                stops=bus_stops
            )
        else:
            lane = np.random.randint(0, road.get("lanes", 1))
            while not self.variable_lane_manager.can_vehicle_use_lane(
                type('Dummy', (), {'is_bus': lambda self: False})(), road_id, lane
            ):
                lane = np.random.randint(0, road.get("lanes", 1))

            vehicle = Vehicle(
                self,
                road_id,
                position=0,
                max_speed=max_speed,
                origin=origin,
                destination=destination,
                lane=lane,
                vehicle_type=vehicle_type
            )

        vehicle.unique_id = self.vehicle_id_counter

        road["vehicles"].append(vehicle)
        road["lane_vehicles"][lane].append(vehicle)

        if self.road_segments.get(road_id):
            seg_idx = 0
            self.road_segments[road_id][seg_idx].add_vehicle(vehicle)

        self.schedule.add(vehicle)
        self.vehicle_id_counter += 1
        return vehicle

    def _generate_bus_stops(self, road_id, origin, destination):
        stops = []
        road = self.roads.get(road_id, {})
        predefined_stops = road.get("bus_stops", [])

        if predefined_stops:
            stops = predefined_stops
        else:
            possible_nodes = [origin, destination]
            for i in range(1, 3):
                pos = int(road.get("length", 100) * (i / 4))
                stops.append({
                    "road_id": road_id,
                    "position": pos,
                    "name": f"Stop_{road_id}_{i}"
                })

        return stops

    def remove_vehicle(self, vehicle):
        with self._remove_lock:
            self._vehicles_to_remove.append(vehicle)

    def _process_vehicle_removals(self):
        with self._remove_lock:
            vehicles_to_remove = self._vehicles_to_remove[:]
            self._vehicles_to_remove.clear()

        removed_ids = set()

        for vehicle in vehicles_to_remove:
            if vehicle.unique_id in removed_ids:
                continue

            road = self.roads.get(vehicle.road_id)
            if road and vehicle in road["vehicles"]:
                road["vehicles"].remove(vehicle)
                if vehicle in road["lane_vehicles"].get(vehicle.lane, []):
                    road["lane_vehicles"][vehicle.lane].remove(vehicle)

            if vehicle.road_id in self.road_segments:
                for segment in self.road_segments[vehicle.road_id]:
                    segment.remove_vehicle(vehicle)

            try:
                if vehicle in self.agents:
                    self.schedule.remove(vehicle)
            except (KeyError, ValueError):
                pass

            self.completed_vehicles.append({
                "id": vehicle.unique_id,
                "origin": vehicle.origin,
                "destination": vehicle.destination,
                "travel_time": vehicle.travel_time,
                "total_distance": vehicle.total_distance,
                "wait_time": vehicle.wait_time,
                "lane_change_count": vehicle.lane_change_count,
                "yield_count": vehicle.yield_count,
                "cooperation_score": vehicle.cooperation_score,
                "history": vehicle.history
            })

            removed_ids.add(vehicle.unique_id)

    def step(self):
        self._update_signals()
        self._release_waiting_vehicles()

        if self.use_parallel and len(self.roads) > 1:
            self._parallel_step()
        else:
            self.schedule.step()

        self._process_vehicle_removals()
        self._update_vehicle_segments()
        self._update_lane_assignments()

        if self.enable_variable_lanes:
            queue_lengths = self.get_queue_lengths()
            changes = self.variable_lane_manager.evaluate_and_adjust(self.schedule.time, queue_lengths)
            if changes:
                self.lane_change_events.extend(changes)

        if self.enable_emission_calc and self.schedule.time % 5 == 0:
            emission_summary = self.emission_model.get_emission_summary(self.roads, self.schedule.time)
            self.emission_history.append({
                "time": self.schedule.time,
                "emissions": emission_summary
            })

        if np.random.random() < self.sim_config.get("generation_rate", 0.3):
            self._generate_vehicle()

        self.datacollector.collect(self)

    def _update_lane_assignments(self):
        for road_id, road in self.roads.items():
            lane_vehicles = {i: [] for i in range(road.get("lanes", 1))}
            for vehicle in road["vehicles"]:
                if hasattr(vehicle, 'lane') and vehicle.lane in lane_vehicles:
                    lane_vehicles[vehicle.lane].append(vehicle)
            road["lane_vehicles"] = lane_vehicles

    def _parallel_step(self):
        all_segments = []
        for road_id, segments in self.road_segments.items():
            all_segments.extend(segments)

        if not all_segments:
            self.schedule.step()
            return

        futures = []
        segments_per_worker = max(1, len(all_segments) // self.num_workers)

        for i in range(0, len(all_segments), segments_per_worker):
            batch = all_segments[i:i + segments_per_worker]
            future = self.executor.submit(self._process_segments, batch)
            futures.append(future)

        for future in as_completed(futures):
            future.result()

    def _process_segments(self, segments):
        for segment in segments:
            segment.update_vehicles(self)

    def _update_vehicle_segments(self):
        for road_id, segments in self.road_segments.items():
            road = self.roads.get(road_id)
            if not road:
                continue

            for vehicle in road["vehicles"]:
                current_seg_idx = min(
                    int(vehicle.position // self.segment_size),
                    len(segments) - 1
                )
                for i, segment in enumerate(segments):
                    if i == current_seg_idx:
                        if vehicle not in segment.vehicles:
                            segment.add_vehicle(vehicle)
                    else:
                        segment.remove_vehicle(vehicle)

    def _update_signals(self):
        for signal_id, signal in self.signals.items():
            phases = signal["phases"]
            offset = signal.get("phase_offset", 0)

            adjusted_time = (self.schedule.time + offset) % signal["cycle_length"]

            cumulative_time = 0
            current_phase_idx = 0
            for i, phase in enumerate(phases):
                duration = phase.get("duration", 30)
                if cumulative_time + duration > adjusted_time:
                    current_phase_idx = i
                    break
                cumulative_time += duration

            signal["current_phase"] = current_phase_idx
            current_phase = phases[current_phase_idx]
            signal["phase_timer"] = adjusted_time - cumulative_time

            road_states = {}
            green_roads = []
            red_roads = []

            for direction, road_ids in current_phase.get("directions", {}).items():
                if isinstance(road_ids, str):
                    road_ids = [road_ids]
                for road_id in road_ids:
                    if direction == "green":
                        road_states[road_id] = "green"
                        green_roads.append(road_id)
                    elif direction == "red":
                        road_states[road_id] = "red"
                        red_roads.append(road_id)

            for road_id, state in road_states.items():
                if road_id in self.roads:
                    self.roads[road_id]["signal_state"] = state
                    signal["state"] = state

            signal["green_roads"] = green_roads
            signal["red_roads"] = red_roads

    def _release_waiting_vehicles(self):
        for road_id, road in self.roads.items():
            if road["has_signal"]:
                signal = self.signals.get(road["signal_id"])
                if signal and signal["state"] == "green":
                    for vehicle in road["vehicles"]:
                        if vehicle.status == "waiting_at_signal":
                            vehicle.status = "moving"
                            vehicle.wait_time = 0

    def _calculate_avg_speed(self):
        if not self.agents:
            return 0
        speeds = [a.speed for a in self.agents]
        return float(np.mean(speeds)) if speeds else 0

    def _calculate_congestion_index(self):
        if not self.roads:
            return 0
        congestion_values = []
        for road_id, road in self.roads.items():
            if road["capacity"] > 0:
                density = len(road["vehicles"]) / road["capacity"]
                congestion_values.append(density)
        return float(np.mean(congestion_values)) if congestion_values else 0

    def get_queue_lengths(self):
        queue_lengths = {}
        for road_id, road in self.roads.items():
            queue = 0
            for vehicle in road["vehicles"]:
                if vehicle.speed == 0:
                    queue += 1
            queue_lengths[road_id] = queue
        return queue_lengths

    def get_speed_distribution(self):
        speed_data = defaultdict(list)
        for agent in self.agents:
            if hasattr(agent, 'speed') and hasattr(agent, 'road_id'):
                road = self.roads.get(agent.road_id)
                if road:
                    pos_ratio = agent.position / road["length"] if road["length"] > 0 else 0
                    speed_data[agent.road_id].append({
                        "position": pos_ratio,
                        "speed": agent.speed,
                        "absolute_position": agent.position,
                        "lane": getattr(agent, 'lane', 0)
                    })
        return dict(speed_data)

    def get_vehicle_positions(self):
        positions = []
        for agent in self.agents:
            if hasattr(agent, 'road_id') and hasattr(agent, 'position'):
                road = self.roads.get(agent.road_id)
                coords = road.get("coordinates", []) if road else []
                lat, lng = self._interpolate_position(coords, agent.position, road["length"] if road else 1)
                positions.append({
                    "id": agent.unique_id,
                    "lat": lat,
                    "lng": lng,
                    "speed": agent.speed,
                    "road_id": agent.road_id,
                    "lane": getattr(agent, 'lane', 0)
                })
        return positions

    def get_lane_statistics(self):
        lane_stats = {}
        for road_id, road in self.roads.items():
            num_lanes = road.get("lanes", 1)
            lane_stats[road_id] = {
                "num_lanes": num_lanes,
                "vehicles_per_lane": [len(road["lane_vehicles"].get(i, [])) for i in range(num_lanes)],
                "lane_changes": sum(v.lane_change_count for v in road["vehicles"]),
                "avg_cooperation": np.mean([v.cooperation_score for v in road["vehicles"]]) if road["vehicles"] else 0
            }
        return lane_stats

    def _interpolate_position(self, coords, position, length):
        if not coords or len(coords) < 2:
            return 0, 0
        total_distance = 0
        segments = []
        for i in range(len(coords) - 1):
            lat1, lng1 = coords[i]
            lat2, lng2 = coords[i + 1]
            seg_length = np.sqrt((lat2 - lat1) ** 2 + (lng2 - lng1) ** 2)
            segments.append((lat1, lng1, lat2, lng2, seg_length))
            total_distance += seg_length

        if total_distance == 0:
            return coords[0]

        target_dist = (position / length) * total_distance if length > 0 else 0
        accumulated = 0
        for lat1, lng1, lat2, lng2, seg_length in segments:
            if accumulated + seg_length >= target_dist:
                ratio = (target_dist - accumulated) / seg_length if seg_length > 0 else 0
                lat = lat1 + (lat2 - lat1) * ratio
                lng = lng1 + (lng2 - lng1) * ratio
                return lat, lng
            accumulated += seg_length
        return coords[-1]

    def run_model(self, steps):
        for _ in range(steps):
            self.step()
        return self.get_simulation_results()

    def get_simulation_results(self):
        df = self.datacollector.get_model_vars_dataframe()
        results = {
            "metrics": df.to_dict(orient="records"),
            "queue_lengths": self.get_queue_lengths(),
            "speed_distribution": self.get_speed_distribution(),
            "vehicle_positions": self.get_vehicle_positions(),
            "congestion_index": self._calculate_congestion_index(),
            "avg_speed": self._calculate_avg_speed(),
            "total_completed": len(self.completed_vehicles),
            "lane_statistics": self.get_lane_statistics(),
            "roads": {rid: {
                "name": r["name"],
                "length": r["length"],
                "num_vehicles": len(r["vehicles"]),
                "capacity": r["capacity"],
                "lanes": r["lanes"]
            } for rid, r in self.roads.items()}
        }

        if self.enable_emission_calc:
            results["emissions"] = self.get_emission_data()
            results["emission_index"] = self.emission_model.get_emission_index(self.roads)

        if self.enable_bus_priority:
            results["bus_statistics"] = self.get_bus_statistics()
            results["bus_priority_stats"] = self.bus_priority_manager.get_statistics()

        if self.enable_variable_lanes:
            results["lane_configs"] = self.get_all_lane_configs()
            results["lane_change_events"] = self.lane_change_events[-10:]

        return results

    def get_emission_data(self):
        if not self.enable_emission_calc:
            return {}

        emission_data = self.emission_model.calculate_network_emission(self.roads)
        summary = self.emission_model.get_emission_summary(self.roads, self.schedule.time)

        queue_emissions = {}
        queue_lengths = self.get_queue_lengths()
        for road_id, qlen in queue_lengths.items():
            if qlen > 0:
                queue_emissions[road_id] = self.emission_model.calculate_emission_from_queue(
                    road_id, qlen
                )

        return {
            "real_time": emission_data,
            "summary": summary,
            "queue_emissions": queue_emissions,
            "history": self.emission_history[-20:] if hasattr(self, 'emission_history') else []
        }

    def get_bus_statistics(self):
        bus_stats = {
            "total_buses": 0,
            "buses": [],
            "avg_passengers": 0,
            "avg_dwell_time": 0,
            "avg_wait_time": 0
        }

        buses = []
        passengers = []
        dwell_times = []
        wait_times = []

        for agent in self.agents:
            if getattr(agent, 'is_bus', lambda: False)():
                buses.append({
                    "id": agent.unique_id,
                    "route_id": getattr(agent, 'route_id', ''),
                    "passenger_count": getattr(agent, 'passenger_count', 0),
                    "current_stop": getattr(agent, 'current_stop_index', 0),
                    "is_at_stop": getattr(agent, 'is_at_stop', False),
                    "dwell_time": getattr(agent, 'total_dwell_time', 0),
                    "wait_time": getattr(agent, 'wait_time', 0),
                    "speed": agent.speed,
                    "road_id": agent.road_id,
                    "position": agent.position,
                    "bus_type": getattr(agent, 'vehicle_type', 'bus')
                })
                passengers.append(getattr(agent, 'passenger_count', 0))
                dwell_times.append(getattr(agent, 'total_dwell_time', 0))
                wait_times.append(getattr(agent, 'wait_time', 0))

        bus_stats["total_buses"] = len(buses)
        bus_stats["buses"] = buses
        bus_stats["avg_passengers"] = float(np.mean(passengers)) if passengers else 0
        bus_stats["avg_dwell_time"] = float(np.mean(dwell_times)) if dwell_times else 0
        bus_stats["avg_wait_time"] = float(np.mean(wait_times)) if wait_times else 0

        return bus_stats

    def get_all_lane_configs(self):
        configs = {}
        for road_id in self.roads.keys():
            configs[road_id] = self.variable_lane_manager.get_lane_status(road_id)
        return configs

    def get_lane_change_history(self, road_id=None):
        return self.variable_lane_manager.get_change_history(road_id)

    def __del__(self):
        if hasattr(self, 'executor') and self.executor:
            self.executor.shutdown(wait=False)


TrafficModel = ParallelTrafficModel
