from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import numpy as np
import json
from src.traffic_model import TrafficModel
from src.signal_controller import DiscreteEventSimulator
from src.signal_optimizer import SignalOptimizer

app = Flask(__name__)
CORS(app)

traffic_model = None
simulation_history = []


def get_default_network_config():
    return {
        "nodes": [
            {"id": "A", "lat": 39.9042, "lng": 116.4074},
            {"id": "B", "lat": 39.9042, "lng": 116.4174},
            {"id": "C", "lat": 39.9142, "lng": 116.4074},
            {"id": "D", "lat": 39.9142, "lng": 116.4174},
            {"id": "E", "lat": 39.8942, "lng": 116.4074},
            {"id": "F", "lat": 39.8942, "lng": 116.4174},
        ],
        "roads": [
            {
                "id": "R1",
                "name": "长安街东段",
                "start_node": "A",
                "end_node": "B",
                "length": 100,
                "lanes": 3,
                "capacity": 150,
                "speed_limit": 14,
                "has_signal": True,
                "signal_id": "S1",
                "coordinates": [[39.9042, 116.4074], [39.9042, 116.4124], [39.9042, 116.4174]]
            },
            {
                "id": "R2",
                "name": "长安街西段",
                "start_node": "B",
                "end_node": "A",
                "length": 100,
                "lanes": 3,
                "capacity": 150,
                "speed_limit": 14,
                "has_signal": True,
                "signal_id": "S1",
                "coordinates": [[39.9042, 116.4174], [39.9042, 116.4124], [39.9042, 116.4074]]
            },
            {
                "id": "R3",
                "name": "王府井大街北段",
                "start_node": "A",
                "end_node": "C",
                "length": 100,
                "lanes": 2,
                "capacity": 100,
                "speed_limit": 12,
                "has_signal": True,
                "signal_id": "S1",
                "coordinates": [[39.9042, 116.4074], [39.9092, 116.4074], [39.9142, 116.4074]]
            },
            {
                "id": "R4",
                "name": "王府井大街南段",
                "start_node": "C",
                "end_node": "A",
                "length": 100,
                "lanes": 2,
                "capacity": 100,
                "speed_limit": 12,
                "has_signal": True,
                "signal_id": "S1",
                "coordinates": [[39.9142, 116.4074], [39.9092, 116.4074], [39.9042, 116.4074]]
            },
            {
                "id": "R5",
                "name": "东单北大街",
                "start_node": "B",
                "end_node": "D",
                "length": 100,
                "lanes": 2,
                "capacity": 100,
                "speed_limit": 12,
                "has_signal": True,
                "signal_id": "S2",
                "coordinates": [[39.9042, 116.4174], [39.9092, 116.4174], [39.9142, 116.4174]]
            },
            {
                "id": "R6",
                "name": "东单南大街",
                "start_node": "D",
                "end_node": "B",
                "length": 100,
                "lanes": 2,
                "capacity": 100,
                "speed_limit": 12,
                "has_signal": True,
                "signal_id": "S2",
                "coordinates": [[39.9142, 116.4174], [39.9092, 116.4174], [39.9042, 116.4174]]
            },
            {
                "id": "R7",
                "name": "建国门内大街东段",
                "start_node": "C",
                "end_node": "D",
                "length": 100,
                "lanes": 3,
                "capacity": 150,
                "speed_limit": 14,
                "has_signal": True,
                "signal_id": "S2",
                "coordinates": [[39.9142, 116.4074], [39.9142, 116.4124], [39.9142, 116.4174]]
            },
            {
                "id": "R8",
                "name": "建国门内大街西段",
                "start_node": "D",
                "end_node": "C",
                "length": 100,
                "lanes": 3,
                "capacity": 150,
                "speed_limit": 14,
                "has_signal": True,
                "signal_id": "S2",
                "coordinates": [[39.9142, 116.4174], [39.9142, 116.4124], [39.9142, 116.4074]]
            },
            {
                "id": "R9",
                "name": "前门大街北段",
                "start_node": "E",
                "end_node": "A",
                "length": 100,
                "lanes": 2,
                "capacity": 100,
                "speed_limit": 12,
                "has_signal": False,
                "coordinates": [[39.8942, 116.4074], [39.8992, 116.4074], [39.9042, 116.4074]]
            },
            {
                "id": "R10",
                "name": "前门大街南段",
                "start_node": "A",
                "end_node": "E",
                "length": 100,
                "lanes": 2,
                "capacity": 100,
                "speed_limit": 12,
                "has_signal": False,
                "coordinates": [[39.9042, 116.4074], [39.8992, 116.4074], [39.8942, 116.4074]]
            },
        ]
    }


def get_default_signal_config():
    return {
        "signals": [
            {
                "id": "S1",
                "intersection_id": "A",
                "controlled_roads": ["R1", "R2", "R3", "R4"],
                "phases": [
                    {"name": "东西绿", "duration": 30, "directions": {"green": ["R1", "R2"], "red": ["R3", "R4"]}},
                    {"name": "南北绿", "duration": 25, "directions": {"green": ["R3", "R4"], "red": ["R1", "R2"]}}
                ]
            },
            {
                "id": "S2",
                "intersection_id": "B",
                "controlled_roads": ["R5", "R6", "R7", "R8"],
                "phases": [
                    {"name": "东西绿", "duration": 30, "directions": {"green": ["R7", "R8"], "red": ["R5", "R6"]}},
                    {"name": "南北绿", "duration": 25, "directions": {"green": ["R5", "R6"], "red": ["R7", "R8"]}}
                ]
            }
        ]
    }


def get_default_od_matrix():
    return {
        "A": {"B": 0.15, "C": 0.10, "D": 0.08, "E": 0.05, "F": 0.03},
        "B": {"A": 0.12, "C": 0.06, "D": 0.10, "E": 0.04, "F": 0.05},
        "C": {"A": 0.10, "B": 0.08, "D": 0.15, "E": 0.03, "F": 0.04},
        "D": {"A": 0.06, "B": 0.12, "C": 0.10, "E": 0.02, "F": 0.06},
        "E": {"A": 0.08, "B": 0.05, "C": 0.04, "D": 0.02, "F": 0.08},
        "F": {"A": 0.04, "B": 0.08, "C": 0.03, "D": 0.06, "E": 0.06},
    }


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify({
        "network": get_default_network_config(),
        "signal": get_default_signal_config(),
        "od_matrix": get_default_od_matrix()
    })


@app.route('/api/simulation/init', methods=['POST'])
def init_simulation():
    global traffic_model, simulation_history

    data = request.json or {}
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    sim_config = data.get('sim_config', {"max_speed": 14, "generation_rate": 0.3})

    traffic_model = TrafficModel(network_config, signal_config, od_matrix, sim_config)
    simulation_history = []

    return jsonify({
        "status": "success",
        "message": "Simulation initialized successfully"
    })


@app.route('/api/simulation/step', methods=['POST'])
def step_simulation():
    global traffic_model, simulation_history

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    data = request.json or {}
    steps = data.get('steps', 1)

    for _ in range(steps):
        traffic_model.step()

    results = traffic_model.get_simulation_results()
    simulation_history.append({
        "time": traffic_model.schedule.time,
        "results": results
    })

    return jsonify({
        "status": "success",
        "time": traffic_model.schedule.time,
        "results": results
    })


@app.route('/api/simulation/run', methods=['POST'])
def run_simulation():
    global traffic_model, simulation_history

    data = request.json or {}
    steps = data.get('steps', 100)
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    sim_config = data.get('sim_config', {"max_speed": 14, "generation_rate": 0.3})

    traffic_model = TrafficModel(network_config, signal_config, od_matrix, sim_config)
    simulation_history = []

    for i in range(steps):
        traffic_model.step()
        if i % 5 == 0 or i == steps - 1:
            results = traffic_model.get_simulation_results()
            simulation_history.append({
                "time": traffic_model.schedule.time,
                "results": results
            })

    final_results = traffic_model.get_simulation_results()

    return jsonify({
        "status": "success",
        "total_steps": steps,
        "final_results": final_results,
        "history": simulation_history
    })


@app.route('/api/simulation/results', methods=['GET'])
def get_results():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    results = traffic_model.get_simulation_results()
    return jsonify({
        "status": "success",
        "results": results
    })


@app.route('/api/simulation/heatmap', methods=['GET'])
def get_heatmap_data():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    vehicle_positions = traffic_model.get_vehicle_positions()
    speed_distribution = traffic_model.get_speed_distribution()

    heatmap_points = []
    for vp in vehicle_positions:
        intensity = 1.0 - (vp["speed"] / 14.0) if vp["speed"] <= 14 else 0
        heatmap_points.append([vp["lat"], vp["lng"], intensity])

    road_heatmap = {}
    for road_id, speeds in speed_distribution.items():
        road = traffic_model.roads.get(road_id)
        if road and road.get("coordinates"):
            coords = road["coordinates"]
            road_points = []
            for sp in speeds:
                pos_ratio = sp["position"]
                lat, lng = traffic_model._interpolate_position(coords, sp["absolute_position"], road["length"])
                intensity = 1.0 - (sp["speed"] / 14.0) if sp["speed"] <= 14 else 0
                road_points.append([lat, lng, intensity])
            road_heatmap[road_id] = road_points

    return jsonify({
        "status": "success",
        "vehicle_heatmap": heatmap_points,
        "road_heatmap": road_heatmap,
        "speed_distribution": speed_distribution
    })


@app.route('/api/simulation/queue_lengths', methods=['GET'])
def get_queue_lengths():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    queue_lengths = traffic_model.get_queue_lengths()
    congestion_index = traffic_model._calculate_congestion_index()
    avg_speed = traffic_model._calculate_avg_speed()

    road_details = {}
    for rid, qlen in queue_lengths.items():
        road = traffic_model.roads.get(rid, {})
        capacity = road.get("capacity", 1)
        num_vehicles = len(road.get("vehicles", []))
        density = num_vehicles / capacity if capacity > 0 else 0

        if density < 0.3:
            level = "畅通"
            color = "#2ecc71"
        elif density < 0.6:
            level = "缓行"
            color = "#f39c12"
        elif density < 0.8:
            level = "拥堵"
            color = "#e67e22"
        else:
            level = "严重拥堵"
            color = "#e74c3c"

        road_details[rid] = {
            "name": road.get("name", f"Road_{rid}"),
            "queue_length": qlen,
            "num_vehicles": num_vehicles,
            "capacity": capacity,
            "density": density,
            "congestion_level": level,
            "color": color
        }

    return jsonify({
        "status": "success",
        "queue_lengths": queue_lengths,
        "road_details": road_details,
        "congestion_index": congestion_index,
        "avg_speed": avg_speed,
        "time": traffic_model.schedule.time
    })


@app.route('/api/optimize/grid_search', methods=['POST'])
def optimize_grid_search():
    data = request.json or {}
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    min_duration = data.get('min_duration', 10)
    max_duration = data.get('max_duration', 60)
    step = data.get('step', 10)
    method = data.get('method', 'ca')

    optimizer = SignalOptimizer(network_config, signal_config, od_matrix)
    result = optimizer.grid_search_optimize(
        min_duration=min_duration,
        max_duration=max_duration,
        step=step,
        method=method
    )

    return jsonify({
        "status": "success",
        "result": result
    })


@app.route('/api/optimize/hill_climb', methods=['POST'])
def optimize_hill_climb():
    data = request.json or {}
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    iterations = data.get('iterations', 20)
    step_size = data.get('step_size', 5)
    method = data.get('method', 'ca')

    optimizer = SignalOptimizer(network_config, signal_config, od_matrix)
    result = optimizer.hill_climb_optimize(
        iterations=iterations,
        step_size=step_size,
        method=method
    )

    return jsonify({
        "status": "success",
        "result": result
    })


@app.route('/api/optimize/genetic', methods=['POST'])
def optimize_genetic():
    data = request.json or {}
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    population_size = data.get('population_size', 20)
    generations = data.get('generations', 10)
    mutation_rate = data.get('mutation_rate', 0.2)
    method = data.get('method', 'ca')

    optimizer = SignalOptimizer(network_config, signal_config, od_matrix)
    result = optimizer.genetic_algorithm_optimize(
        population_size=population_size,
        generations=generations,
        mutation_rate=mutation_rate,
        method=method
    )

    return jsonify({
        "status": "success",
        "result": result
    })


@app.route('/api/optimize/compare', methods=['POST'])
def compare_configs():
    data = request.json or {}
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    optimized_config = data.get('optimized_signal')
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    simulation_steps = data.get('simulation_steps', 200)
    method = data.get('method', 'ca')

    optimizer = SignalOptimizer(network_config, signal_config, od_matrix)
    result = optimizer.compare_configurations(
        signal_config,
        optimized_config,
        simulation_steps=simulation_steps,
        method=method
    )

    return jsonify({
        "status": "success",
        "result": result
    })


@app.route('/api/des/run', methods=['POST'])
def run_des():
    data = request.json or {}
    network_config = data.get('network') or get_default_network_config()
    signal_config = data.get('signal') or get_default_signal_config()
    od_matrix = data.get('od_matrix') or get_default_od_matrix()
    duration = data.get('duration', 300)

    simulator = DiscreteEventSimulator(network_config, signal_config, od_matrix)
    results = simulator.run(duration=duration)

    return jsonify({
        "status": "success",
        "results": results
    })


@app.route('/api/network', methods=['GET'])
def get_network():
    network = get_default_network_config()
    return jsonify({
        "status": "success",
        "network": network
    })


@app.route('/api/signal', methods=['GET'])
def get_signal():
    signal = get_default_signal_config()
    return jsonify({
        "status": "success",
        "signal": signal
    })


@app.route('/api/od_matrix', methods=['GET'])
def get_od():
    od = get_default_od_matrix()
    return jsonify({
        "status": "success",
        "od_matrix": od
    })


@app.route('/api/simulation/reset', methods=['POST'])
def reset_simulation():
    global traffic_model, simulation_history
    traffic_model = None
    simulation_history = []
    return jsonify({"status": "success", "message": "Simulation reset"})


@app.route('/api/emissions', methods=['GET'])
def get_emissions():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    if not hasattr(traffic_model, 'enable_emission_calc') or not traffic_model.enable_emission_calc:
        return jsonify({"status": "error", "message": "Emission calculation not enabled"}), 400

    emission_data = traffic_model.get_emission_data()
    emission_index = traffic_model.emission_model.get_emission_index(traffic_model.roads)

    return jsonify({
        "status": "success",
        "emission_data": emission_data,
        "emission_index": emission_index,
        "time": traffic_model.schedule.time
    })


@app.route('/api/emissions/road/<road_id>', methods=['GET'])
def get_road_emissions(road_id):
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    road = traffic_model.roads.get(road_id)
    if not road:
        return jsonify({"status": "error", "message": f"Road {road_id} not found"}), 404

    road_emissions = traffic_model.emission_model.calculate_road_emission(road, road["vehicles"])
    queue = traffic_model.get_queue_lengths().get(road_id, 0)
    queue_emissions = traffic_model.emission_model.calculate_emission_from_queue(road_id, queue)

    return jsonify({
        "status": "success",
        "road_id": road_id,
        "road_emissions": road_emissions,
        "queue_emissions": queue_emissions,
        "queue_length": queue
    })


@app.route('/api/buses', methods=['GET'])
def get_buses():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    if not hasattr(traffic_model, 'enable_bus_priority') or not traffic_model.enable_bus_priority:
        return jsonify({"status": "error", "message": "Bus priority not enabled"}), 400

    bus_stats = traffic_model.get_bus_statistics()
    priority_stats = traffic_model.bus_priority_manager.get_statistics()

    bus_positions = []
    for bus_info in bus_stats.get("buses", []):
        road = traffic_model.roads.get(bus_info["road_id"])
        if road:
            coords = road.get("coordinates", [])
            lat, lng = traffic_model._interpolate_position(
                coords, bus_info["position"], road["length"]
            )
            bus_positions.append({
                "id": bus_info["id"],
                "lat": lat,
                "lng": lng,
                "route_id": bus_info["route_id"],
                "passengers": bus_info["passenger_count"],
                "speed": bus_info["speed"],
                "is_at_stop": bus_info["is_at_stop"],
                "bus_type": bus_info["bus_type"]
            })

    return jsonify({
        "status": "success",
        "bus_statistics": bus_stats,
        "bus_priority_stats": priority_stats,
        "bus_positions": bus_positions,
        "time": traffic_model.schedule.time
    })


@app.route('/api/buses/<bus_id>', methods=['GET'])
def get_bus_detail(bus_id):
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    bus_id = int(bus_id)
    bus = None
    for agent in traffic_model.agents:
        if getattr(agent, 'unique_id', -1) == bus_id and getattr(agent, 'is_bus', lambda: False)():
            bus = agent
            break

    if not bus:
        return jsonify({"status": "error", "message": f"Bus {bus_id} not found"}), 404

    return jsonify({
        "status": "success",
        "bus_id": bus_id,
        "route_id": getattr(bus, 'route_id', ''),
        "passenger_count": getattr(bus, 'passenger_count', 0),
        "current_stop": getattr(bus, 'current_stop_index', 0),
        "is_at_stop": getattr(bus, 'is_at_stop', False),
        "total_dwell_time": getattr(bus, 'total_dwell_time', 0),
        "stops": getattr(bus, 'stops', []),
        "speed": bus.speed,
        "position": bus.position,
        "road_id": bus.road_id,
        "vehicle_type": getattr(bus, 'vehicle_type', 'bus'),
        "history": bus.history[-20:] if hasattr(bus, 'history') else []
    })


@app.route('/api/lanes', methods=['GET'])
def get_lane_configs():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    if not hasattr(traffic_model, 'enable_variable_lanes') or not traffic_model.enable_variable_lanes:
        return jsonify({"status": "error", "message": "Variable lanes not enabled"}), 400

    lane_configs = traffic_model.get_all_lane_configs()
    lane_stats = traffic_model.get_lane_statistics()

    return jsonify({
        "status": "success",
        "lane_configs": lane_configs,
        "lane_statistics": lane_stats,
        "time": traffic_model.schedule.time
    })


@app.route('/api/lanes/road/<road_id>', methods=['GET'])
def get_road_lane_config(road_id):
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    road = traffic_model.roads.get(road_id)
    if not road:
        return jsonify({"status": "error", "message": f"Road {road_id} not found"}), 404

    lane_config = traffic_model.variable_lane_manager.get_lane_status(road_id)
    change_history = traffic_model.get_lane_change_history(road_id)

    return jsonify({
        "status": "success",
        "road_id": road_id,
        "lane_config": lane_config,
        "change_history": change_history,
        "num_vehicles_per_lane": [
            len(road["lane_vehicles"].get(i, [])) for i in range(road.get("lanes", 1))
        ]
    })


@app.route('/api/lanes/changes', methods=['GET'])
def get_lane_changes():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    all_changes = traffic_model.get_lane_change_history()
    recent_changes = getattr(traffic_model, 'lane_change_events', [])[-20:]

    return jsonify({
        "status": "success",
        "all_changes": all_changes,
        "recent_changes": recent_changes,
        "time": traffic_model.schedule.time
    })


@app.route('/api/lanes/toggle', methods=['POST'])
def toggle_lane_type():
    global traffic_model

    if traffic_model is None:
        return jsonify({"status": "error", "message": "Simulation not initialized"}), 400

    data = request.json or {}
    road_id = data.get('road_id')
    lane = data.get('lane')
    new_type = data.get('new_type', 'forward')

    if not road_id or lane is None:
        return jsonify({"status": "error", "message": "Missing road_id or lane parameter"}), 400

    road = traffic_model.roads.get(road_id)
    if not road:
        return jsonify({"status": "error", "message": f"Road {road_id} not found"}), 404

    num_lanes = road.get("lanes", 1)
    if lane < 0 or lane >= num_lanes:
        return jsonify({"status": "error", "message": f"Invalid lane {lane}"}), 400

    config = traffic_model.variable_lane_manager.lane_configs.get(road_id, {})
    lane_types = config.get("lane_types", [])
    lane_directions = config.get("lane_directions", [])

    if 0 <= lane < len(lane_types):
        old_type = lane_types[lane]
        lane_types[lane] = new_type
        lane_directions[lane] = "forward" if new_type != "reversible" else "opposite"

        traffic_model.lane_change_events.append({
            "time": traffic_model.schedule.time,
            "road_id": road_id,
            "lane": lane,
            "old_type": old_type,
            "new_type": new_type,
            "reason": "manual"
        })

        return jsonify({
            "status": "success",
            "road_id": road_id,
            "lane": lane,
            "old_type": old_type,
            "new_type": new_type
        })

    return jsonify({"status": "error", "message": "Failed to update lane type"}), 500


@app.route('/api/simulation/config', methods=['POST'])
def update_sim_config():
    global traffic_model

    data = request.json or {}

    if traffic_model and hasattr(traffic_model, 'enable_bus_priority'):
        traffic_model.enable_bus_priority = data.get('enable_bus_priority', traffic_model.enable_bus_priority)
        traffic_model.enable_variable_lanes = data.get('enable_variable_lanes', traffic_model.enable_variable_lanes)
        traffic_model.enable_emission_calc = data.get('enable_emission_calc', traffic_model.enable_emission_calc)
        traffic_model.bus_generation_rate = data.get('bus_generation_rate', traffic_model.bus_generation_rate)

    return jsonify({
        "status": "success",
        "enable_bus_priority": traffic_model.enable_bus_priority if traffic_model else True,
        "enable_variable_lanes": traffic_model.enable_variable_lanes if traffic_model else True,
        "enable_emission_calc": traffic_model.enable_emission_calc if traffic_model else True,
        "bus_generation_rate": traffic_model.bus_generation_rate if traffic_model else 0.1
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
