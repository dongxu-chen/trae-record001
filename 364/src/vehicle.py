import mesa
import random
import numpy as np
from collections import defaultdict


class GameTheoryLaneChanger:
    def __init__(self):
        self.politeness_factor = 0.5
        self.risk_threshold = 0.3
        self.cooperation_bonus = 0.2

    def calculate_yielding_decision(self, vehicle, target_vehicle, current_road, target_lane_vehicles):
        gap = target_vehicle.position - vehicle.position if target_vehicle else float('inf')
        speed_advantage = vehicle.speed - target_vehicle.speed if target_vehicle else vehicle.speed

        if gap <= 0:
            return False, 0

        yield_utility = self._calculate_yield_utility(
            vehicle, target_vehicle, gap, speed_advantage, target_lane_vehicles
        )
        no_yield_utility = self._calculate_no_yield_utility(
            vehicle, target_vehicle, gap, speed_advantage
        )

        should_yield = yield_utility > no_yield_utility
        confidence = abs(yield_utility - no_yield_utility)

        return should_yield, confidence

    def _calculate_yield_utility(self, vehicle, target_vehicle, gap, speed_advantage, target_lane_vehicles):
        base_utility = 0.0

        if gap > vehicle.speed * 2:
            base_utility += 0.3

        if target_vehicle:
            if target_vehicle.speed < vehicle.speed:
                base_utility += 0.2
            if target_vehicle.wait_time > 5:
                base_utility += self.politeness_factor * 0.3

        if target_lane_vehicles and hasattr(target_lane_vehicles[0], 'model'):
            road = target_lane_vehicles[0].model.roads.get(target_lane_vehicles[0].road_id, {})
            capacity = road.get("capacity", 100)
            lane_density = len(target_lane_vehicles) / max(1, capacity)
            if lane_density < 0.5:
                base_utility += 0.2

        return base_utility

    def _calculate_no_yield_utility(self, vehicle, target_vehicle, gap, speed_advantage):
        utility = vehicle.speed / vehicle.max_speed * 0.5

        if target_vehicle and target_vehicle.speed > vehicle.speed:
            utility += 0.3

        if gap < vehicle.speed:
            utility += 0.4

        return utility

    def calculate_merge_score(self, vehicle, target_lane_vehicles, gap_to_front, gap_to_back):
        score = 0.0

        if gap_to_front >= vehicle.speed + 1:
            score += 0.3
        if gap_to_back >= vehicle.speed:
            score += 0.3

        if target_lane_vehicles:
            lane_speed = np.mean([v.speed for v in target_lane_vehicles])
            if lane_speed > vehicle.speed * 0.8:
                score += 0.2
        else:
            score += 0.4

        return score


class Vehicle(mesa.Agent):
    def __init__(self, model, road_id, position, max_speed, origin, destination, lane=0, vehicle_type='passenger_car'):
        super().__init__(model)
        self.road_id = road_id
        self.position = position
        self.speed = 0
        self.max_speed = max_speed
        self.origin = origin
        self.destination = destination
        self.travel_time = 0
        self.total_distance = 0
        self.status = "moving"
        self.wait_time = 0
        self.history = []
        self.lane = lane
        self.lane_change_count = 0
        self.yield_count = 0
        self.blocked_count = 0
        self.cooperation_score = 0.5
        self.aggression_level = random.uniform(0.2, 0.8)
        self.game_theory = GameTheoryLaneChanger()
        self.vehicle_type = vehicle_type
        self._prev_speed = 0
        self.emissions = {}
        self.current_signal_wait = 0
        self.bus_stop_wait = 0

    def is_bus(self):
        return self.vehicle_type in ['bus', 'bus_electric', 'bus_hybrid']

    def is_public_transport(self):
        return self.is_bus()

    def step(self):
        road = self.model.roads[self.road_id]
        if self.status == "waiting_at_signal":
            self.wait_time += 1
            self.speed = 0
            return

        self.travel_time += 1

        if road.get("lanes", 1) > 1:
            self._consider_lane_change(road)

        front_vehicle = self._get_front_vehicle(road)
        signal_state = self._check_signal(road)

        self._update_speed(front_vehicle, signal_state, road)
        self._move(road)

        if self.speed > 0:
            self.total_distance += self.speed

        self.history.append({
            "time": self.model.schedule.time,
            "position": self.position,
            "speed": self.speed,
            "road_id": self.road_id,
            "lane": self.lane
        })

    def _consider_lane_change(self, road):
        if self.lane_change_count > 3:
            return

        current_lane_vehicles = self._get_lane_vehicles(road, self.lane)
        front_vehicle = self._get_front_vehicle_in_lane(current_lane_vehicles)

        should_change = False
        target_lane = self.lane

        if front_vehicle and front_vehicle.speed < self.speed * 0.5:
            for other_lane in range(road.get("lanes", 1)):
                if other_lane != self.lane:
                    other_lane_vehicles = self._get_lane_vehicles(road, other_lane)
                    other_front = self._get_front_vehicle_in_lane(other_lane_vehicles)

                    if not other_front or other_front.position > self.position + self.speed:
                        other_back = self._get_back_vehicle_in_lane(other_lane_vehicles)
                        gap_to_back = self.position - other_back.position if other_back else float('inf')

                        merge_score = self.game_theory.calculate_merge_score(
                            self, other_lane_vehicles,
                            other_front.position - self.position if other_front else float('inf'),
                            gap_to_back
                        )

                        if merge_score > 0.5:
                            should_change = self._negotiate_lane_change(
                                other_lane_vehicles, other_lane
                            )
                            if should_change:
                                target_lane = other_lane
                                break

        if should_change and target_lane != self.lane:
            self.lane = target_lane
            self.lane_change_count += 1
            self.cooperation_score = max(0, min(1, self.cooperation_score + 0.01))

    def _negotiate_lane_change(self, target_lane_vehicles, target_lane):
        if not target_lane_vehicles:
            return True

        front_vehicle = self._get_front_vehicle_in_lane(target_lane_vehicles)
        back_vehicle = self._get_back_vehicle_in_lane(target_lane_vehicles)

        if back_vehicle:
            should_yield, confidence = self.game_theory.calculate_yielding_decision(
                back_vehicle, self, None, [self]
            )

            if not should_yield and back_vehicle.aggression_level < 0.7:
                self.yield_count += 1
                back_vehicle.blocked_count += 1
                back_vehicle.cooperation_score = max(0, min(1, back_vehicle.cooperation_score - 0.01))
                return True
            elif should_yield:
                return False

        if front_vehicle and front_vehicle.aggression_level < 0.7:
            return True

        return random.random() < 0.3

    def _get_lane_vehicles(self, road, lane):
        return [v for v in road.get("lane_vehicles", {}).get(lane, [])
                if v.unique_id != self.unique_id]

    def _get_front_vehicle_in_lane(self, vehicles):
        front = [v for v in vehicles if v.position > self.position]
        if front:
            return min(front, key=lambda v: v.position - self.position)
        return None

    def _get_back_vehicle_in_lane(self, vehicles):
        back = [v for v in vehicles if v.position < self.position]
        if back:
            return max(back, key=lambda v: self.position - v.position)
        return None

    def _get_front_vehicle(self, road):
        vehicles = [v for v in road["vehicles"] if v.unique_id != self.unique_id]
        if not vehicles:
            return None
        front = [v for v in vehicles if v.position > self.position]
        if front:
            return min(front, key=lambda v: v.position - self.position)
        return None

    def _check_signal(self, road):
        if not road["has_signal"]:
            return "green"
        signal = self.model.signals.get(road["signal_id"])
        if not signal:
            return "green"
        return signal["state"]

    def _update_speed(self, front_vehicle, signal_state, road):
        v_max = min(self.max_speed, road["speed_limit"])

        if signal_state == "red":
            stop_line = road["length"] - 5
            if self.position >= stop_line - self.speed and self.position < stop_line + 2:
                self.speed = max(0, self.speed - 2)
                if self.speed == 0:
                    self.status = "waiting_at_signal"
                    self.wait_time = 0
                return

        if front_vehicle:
            gap = front_vehicle.position - self.position - 1

            safe_gap = max(1, int(self.speed * (1 + self.aggression_level * 0.5)))
            if gap < safe_gap:
                target_speed = max(0, gap)
                self.speed = min(self.speed + 1, target_speed, v_max)
            else:
                self.speed = min(self.speed + 1, v_max, gap)

            if front_vehicle.yield_count > front_vehicle.blocked_count and front_vehicle.speed < self.speed:
                if random.random() < self.cooperation_score * 0.1:
                    self.speed = max(0, self.speed - 1)
                    self.yield_count += 1
                    front_vehicle.cooperation_score = min(1, front_vehicle.cooperation_score + 0.005)
        else:
            self.speed = min(self.speed + 1, v_max)

        if random.random() < 0.3 and self.speed > 0:
            self.speed = max(0, self.speed - 1)

    def _move(self, road):
        new_position = self.position + self.speed
        if new_position >= road["length"]:
            self._transfer_road(road)
        else:
            self.position = new_position

    def _transfer_road(self, road):
        if self.destination and road["end_node"] == self.destination:
            self.model.remove_vehicle(self)
            return

        next_roads = self._find_next_roads(road)
        if next_roads:
            best_road = self._choose_best_road(next_roads, road)
            if best_road:
                next_road = self.model.roads[best_road]
                if len(next_road["vehicles"]) < next_road["capacity"]:
                    self.road_id = best_road
                    self.position = 0
                    self.lane = 0
                    road["vehicles"].remove(self)
                    next_road["vehicles"].append(self)
                else:
                    self.speed = 0
                    self.position = road["length"] - 1
            else:
                self.model.remove_vehicle(self)
        else:
            self.model.remove_vehicle(self)

    def _choose_best_road(self, next_road_ids, current_road):
        if not next_road_ids:
            return None

        road_scores = {}
        for rid in next_road_ids:
            road = self.model.roads.get(rid)
            if not road:
                continue

            score = 0.0
            num_vehicles = len(road["vehicles"])
            capacity = road.get("capacity", 100)
            density = num_vehicles / capacity if capacity > 0 else 1

            score -= density * 0.5

            if road.get("signal_state") == "green":
                score += 0.3

            if self.destination and road["end_node"] == self.destination:
                score += 0.5

            road_scores[rid] = score

        if road_scores:
            best_road = max(road_scores, key=road_scores.get)
            return best_road
        return random.choice(next_road_ids) if next_road_ids else None

    def _find_next_roads(self, current_road):
        end_node = current_road["end_node"]
        possible_roads = []
        for rid, road in self.model.roads.items():
            if road["start_node"] == end_node and rid != current_road["id"]:
                possible_roads.append(rid)
        return possible_roads


class Bus(Vehicle):
    def __init__(self, model, road_id, position, max_speed, origin, destination,
                 lane=0, bus_type='bus', route_id=None, stops=None):
        super().__init__(model, road_id, position, max_speed, origin, destination, lane, bus_type)
        self.route_id = route_id
        self.stops = stops or []
        self.current_stop_index = 0
        self.passenger_count = random.randint(10, 40)
        self.stop_wait_time = 0
        self.dwell_time = 0
        self.total_dwell_time = 0
        self.is_at_stop = False
        self.bus_priority_eligible = True
        self.max_speed = min(max_speed, 10)

    def step(self):
        road = self.model.roads[self.road_id]

        if self.is_at_stop:
            self.dwell_time += 1
            self.total_dwell_time += 1
            self.speed = 0
            self.stop_wait_time += 1

            if self.stop_wait_time >= self._calculate_dwell_time():
                self.is_at_stop = False
                self.stop_wait_time = 0
                self.current_stop_index = (self.current_stop_index + 1) % max(1, len(self.stops))
            return

        if self.status == "waiting_at_signal":
            self.wait_time += 1
            self.current_signal_wait += 1
            self.speed = 0
            return

        self.travel_time += 1

        self._check_bus_stop(road)

        if self.is_at_stop:
            return

        if road.get("lanes", 1) > 1:
            self._consider_bus_lane(road)

        front_vehicle = self._get_front_vehicle(road)
        signal_state = self._check_signal_with_priority(road)

        self._update_speed(front_vehicle, signal_state, road)
        self._move(road)

        if self.speed > 0:
            self.total_distance += self.speed

        self.history.append({
            "time": self.model.schedule.time,
            "position": self.position,
            "speed": self.speed,
            "road_id": self.road_id,
            "lane": self.lane,
            "passengers": self.passenger_count
        })

    def _check_bus_stop(self, road):
        if not self.stops:
            return

        next_stop = self.stops[self.current_stop_index]
        stop_position = next_stop.get("position", road["length"] - 10)
        stop_road = next_stop.get("road_id", self.road_id)

        if stop_road == self.road_id and abs(self.position - stop_position) < 3:
            if self.speed <= 1:
                self.is_at_stop = True
                self.stop_wait_time = 0
                self.passenger_count += random.randint(-5, 8)
                self.passenger_count = max(0, min(50, self.passenger_count))

    def _calculate_dwell_time(self):
        base_time = 3
        passenger_factor = int(self.passenger_count / 10)
        return base_time + passenger_factor + random.randint(0, 2)

    def _consider_bus_lane(self, road):
        if self.lane_change_count > 2:
            return

        bus_lane = road.get("bus_lane", -1)
        if bus_lane >= 0 and self.lane != bus_lane:
            bus_lane_vehicles = self._get_lane_vehicles(road, bus_lane)

            if not bus_lane_vehicles or all(v.position > self.position + self.speed for v in bus_lane_vehicles):
                self.lane = bus_lane
                self.lane_change_count += 1

    def _check_signal_with_priority(self, road):
        if not road["has_signal"]:
            return "green"

        signal = self.model.signals.get(road["signal_id"])
        if not signal:
            return "green"

        if signal["state"] == "red" and self.bus_priority_eligible:
            bus_queue = self._count_buses_at_signal(road)
            if bus_queue >= 2 or self.current_signal_wait >= 15:
                self._request_priority(signal, road)

        return signal["state"]

    def _count_buses_at_signal(self, road):
        stop_line = road["length"] - 10
        count = 0
        for vehicle in road["vehicles"]:
            if getattr(vehicle, 'is_bus', lambda: False)() and vehicle.position >= stop_line - 10:
                count += 1
        return count

    def _request_priority(self, signal, road):
        if hasattr(self.model, 'bus_priority_manager'):
            self.model.bus_priority_manager.request_priority(signal["id"], self)

    def _update_speed(self, front_vehicle, signal_state, road):
        v_max = min(self.max_speed, road["speed_limit"])

        if signal_state == "red":
            stop_line = road["length"] - 5
            if self.position >= stop_line - self.speed and self.position < stop_line + 2:
                self.speed = max(0, self.speed - 2)
                if self.speed == 0:
                    self.status = "waiting_at_signal"
                    self.wait_time = 0
                return

        if front_vehicle:
            gap = front_vehicle.position - self.position - 1
            safe_gap = max(2, int(self.speed * 1.2))
            if gap < safe_gap:
                target_speed = max(0, gap)
                self.speed = min(self.speed + 1, target_speed, v_max)
            else:
                self.speed = min(self.speed + 1, v_max, gap)

            if front_vehicle.yield_count > front_vehicle.blocked_count and front_vehicle.speed < self.speed:
                if random.random() < self.cooperation_score * 0.1:
                    self.speed = max(0, self.speed - 1)
                    self.yield_count += 1
                    front_vehicle.cooperation_score = min(1, front_vehicle.cooperation_score + 0.005)
        else:
            self.speed = min(self.speed + 1, v_max)

        if random.random() < 0.2 and self.speed > 0:
            self.speed = max(0, self.speed - 1)

    def _transfer_road(self, road):
        if self.destination and road["end_node"] == self.destination:
            self.model.remove_vehicle(self)
            return

        next_roads = self._find_next_roads(road)
        if next_roads:
            best_road = self._choose_best_road(next_roads, road)
            if best_road:
                next_road = self.model.roads[best_road]
                if len(next_road["vehicles"]) < next_road["capacity"]:
                    self.road_id = best_road
                    self.position = 0
                    self.lane = next_road.get("bus_lane", 0)
                    road["vehicles"].remove(self)
                    next_road["vehicles"].append(self)
                else:
                    self.speed = 0
                    self.position = road["length"] - 1
            else:
                self.model.remove_vehicle(self)
        else:
            self.model.remove_vehicle(self)
