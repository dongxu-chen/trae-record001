import os
import json
import time
from flask import Flask, request, jsonify, render_template

from vrptw.models import ProblemData, Customer, Depot, TrafficFactor, CarbonConfig
from vrptw.ga_solver import VRPTWSolver
from vrptw.network import NetworkManager
from vrptw.visualization import RouteVisualizer

app = Flask(__name__)
app.config["SECRET_KEY"] = "vrptw-secret-key-2024"


def parse_input_data(data: dict) -> tuple:
    depots_data = data.get("depots", [])
    if not depots_data:
        depot_data = data.get("depot", {})
        depots_data = [depot_data]

    depots = []
    for idx, d in enumerate(depots_data):
        depot = Depot(
            id=int(d.get("id", idx)),
            x=float(d.get("x", 116.407)),
            y=float(d.get("y", 39.904)),
            num_vehicles=int(d.get("num_vehicles", 5)),
            vehicle_capacity=float(d.get("vehicle_capacity", 100)),
        )
        depots.append(depot)

    customers_data = data.get("customers", [])
    customers = []
    for idx, c in enumerate(customers_data):
        cust = Customer(
            id=int(c.get("id", idx + 1)),
            x=float(c.get("x", 0)),
            y=float(c.get("y", 0)),
            demand=float(c.get("demand", 10)),
            ready_time=float(c.get("ready_time", 0)),
            due_time=float(c.get("due_time", 1440)),
            service_time=float(c.get("service_time", 10)),
            assigned_depot=int(c.get("assigned_depot", 0)) if c.get("assigned_depot") is not None else None,
        )
        customers.append(cust)

    use_osm = bool(data.get("use_osm", False))
    travel_speed = float(data.get("travel_speed", 40))

    traffic_data = data.get("traffic", {})
    traffic_factor = None
    if traffic_data:
        traffic_factor = TrafficFactor(
            hour_of_day=int(traffic_data.get("hour_of_day", 12)),
            congestion_level=traffic_data.get("congestion_level", "normal"),
        )

    carbon_data = data.get("carbon_config", {})
    carbon_config = None
    if carbon_data:
        carbon_config = CarbonConfig(
            enabled=bool(carbon_data.get("enabled", True)),
            emission_factor=float(carbon_data.get("emission_factor", 0.27)),
            fuel_efficiency=float(carbon_data.get("fuel_efficiency", 8.0)),
            carbon_price_per_ton=float(carbon_data.get("carbon_price_per_ton", 50.0)),
        )
    else:
        carbon_config = CarbonConfig()

    return depots, customers, use_osm, travel_speed, traffic_factor, carbon_config


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/solve", methods=["POST"])
def solve():
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({"error": "请求数据为空"}), 400

        depots, customers, use_osm, travel_speed, traffic_factor, carbon_config = parse_input_data(data)

        if not customers:
            return jsonify({"error": "请至少添加一个配送点"}), 400

        if not depots:
            return jsonify({"error": "请至少配置一个仓库"}), 400

        total_vehicles = sum(d.num_vehicles for d in depots)
        if total_vehicles <= 0:
            return jsonify({"error": "车辆数量必须大于0"}), 400

        network = NetworkManager(use_osm=use_osm)
        problem_data = network.create_problem_data(
            depots=depots,
            customers=customers,
            travel_speed=travel_speed,
            traffic_factor=traffic_factor,
            carbon_config=carbon_config,
        )

        if len(depots) > 1:
            network.assign_customers_to_depots(depots, customers)

        solver = VRPTWSolver(problem_data)
        solution = solver.solve(
            population_size=150,
            num_generations=200,
            crossover_prob=0.8,
            mutation_prob=0.2,
            use_local_search=True,
            verbose=True,
        )

        visualizer = RouteVisualizer(problem_data, solution)
        map_html = visualizer.get_map_html()

        result = solution.to_dict()
        result["map_html"] = map_html
        result["problem_info"] = {
            "num_customers": len(customers),
            "num_depots": len(depots),
            "total_vehicles": total_vehicles,
            "use_osm": use_osm,
            "traffic_enabled": traffic_factor is not None,
            "carbon_enabled": carbon_config is not None,
        }

        if traffic_factor:
            result["traffic_info"] = {
                "hour_of_day": traffic_factor.hour_of_day,
                "congestion_level": traffic_factor.congestion_level,
                "factor": traffic_factor.get_factor(),
            }

        return jsonify(result)

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"求解失败: {str(e)}"}), 500


@app.route("/api/sample", methods=["GET"])
def get_sample_data():
    num_customers = int(request.args.get("n", 10))
    num_depots = int(request.args.get("depots", 1))
    depot_lon = float(request.args.get("depot_lon", 116.407))
    depot_lat = float(request.args.get("depot_lat", 39.904))
    spread = float(request.args.get("spread", 0.05))

    depots, customers = NetworkManager.generate_sample_data(
        num_customers=num_customers,
        num_depots=num_depots,
        depot_lon=depot_lon,
        depot_lat=depot_lat,
        spread=spread,
    )

    if num_depots > 1:
        network = NetworkManager()
        network.assign_customers_to_depots(depots, customers)

    traffic_factor = NetworkManager.generate_traffic_factor(
        hour_of_day=8,
        congestion_level="normal",
    )

    carbon_config = NetworkManager.generate_carbon_config()

    return jsonify({
        "depots": [
            {
                "id": d.id,
                "x": d.x,
                "y": d.y,
                "num_vehicles": d.num_vehicles,
                "vehicle_capacity": d.vehicle_capacity,
            }
            for d in depots
        ],
        "customers": [
            {
                "id": c.id,
                "x": c.x,
                "y": c.y,
                "demand": round(c.demand, 1),
                "ready_time": round(c.ready_time, 1),
                "due_time": round(c.due_time, 1),
                "service_time": round(c.service_time, 1),
                "assigned_depot": c.assigned_depot,
            }
            for c in customers
        ],
        "traffic": {
            "hour_of_day": traffic_factor.hour_of_day,
            "congestion_level": traffic_factor.congestion_level,
        },
        "carbon_config": {
            "enabled": carbon_config.enabled,
            "emission_factor": carbon_config.emission_factor,
            "fuel_efficiency": carbon_config.fuel_efficiency,
            "carbon_price_per_ton": carbon_config.carbon_price_per_ton,
        },
    })


@app.route("/api/traffic/preview", methods=["POST"])
def preview_traffic():
    try:
        data = request.get_json(force=True)
        hour = int(data.get("hour_of_day", 12))
        level = data.get("congestion_level", "normal")

        tf = TrafficFactor(hour_of_day=hour, congestion_level=level)
        factor = tf.get_factor()

        return jsonify({
            "factor": round(factor, 4),
            "description": f"当前时段({hour}:00)交通{level}，行程时间将变为原来的{factor:.1f}倍"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)