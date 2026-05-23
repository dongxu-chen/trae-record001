from flask import Flask, render_template, request, jsonify
from vrp_solver import VRPSolver
import os
import requests
import random

app = Flask(__name__)
app.config['SECRET_KEY'] = 'vrp-optimization-tool-secret-key'

GAODE_API_KEY = os.environ.get('GAODE_API_KEY', '')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/traffic/status', methods=['GET'])
def get_traffic_status():
    try:
        rectangle = request.args.get('rectangle', '')
        
        if not GAODE_API_KEY:
            return jsonify({
                'status': '0',
                'info': '模拟交通数据（无API密钥，使用模拟数据)',
                'trafficinfo': {
                    'description': '模拟交通数据',
                    'evaluation': '整体畅通'
                }
            })
        
        url = f'https://restapi.amap.com/v3/traffic/status/rectangle'
        params = {
            'key': GAODE_API_KEY,
            'rectangle': rectangle,
            'level': 5
        }
        
        response = requests.get(url, params=params, timeout=10)
        return jsonify(response.json())
        
    except Exception as e:
        return jsonify({
            'status': '0',
            'info': str(e),
            'trafficinfo': {
                'description': '获取失败，使用模拟数据',
                'evaluation': '整体畅通'
            }
        })


@app.route('/api/traffic/matrix', methods=['POST'])
def get_traffic_matrix():
    try:
        data = request.json
        locations = data.get('locations', [])
        
        traffic_matrix = {}
        n = len(locations)
        
        if not GAODE_API_KEY:
            for i in range(n):
                for j in range(n):
                    if i != j:
                        traffic_factor = 1.0 + random.uniform(-0.2, 0.5)
                        traffic_matrix[f'{i}-{j}'] = round(traffic_factor, 2)
            
            return jsonify({
                'status': '1',
                'info': '模拟交通数据',
                'traffic_matrix': traffic_matrix,
                'note': '未配置高德API密钥，使用模拟数据'
            })
        
        for i in range(n):
            for j in range(n):
                if i != j:
                    origin = f"{locations[i]['lng']},{locations[i]['lat']}"
                    destination = f"{locations[j]['lng']},{locations[j]['lat']}"
                    
                    url = 'https://restapi.amap.com/v3/direction/driving'
                    params = {
                        'key': GAODE_API_KEY,
                        'origin': origin,
                        'destination': destination,
                        'strategy': 0
                    }
                    
                    try:
                        response = requests.get(url, params=params, timeout=5)
                        result = response.json()
                        
                        if result.get('status') == '1' and result.get('route'):
                            distance = float(result['route']['paths'][0]['distance']) / 1000
                            duration = float(result['route']['paths'][0]['duration']) / 3600
                            traffic_matrix[f'{i}-{j}'] = round(duration / (distance / 30) if distance > 0 else 1.0, 2)
                        else:
                            traffic_matrix[f'{i}-{j}'] = 1.0
                            
                    except:
                        traffic_matrix[f'{i}-{j}'] = 1.0 + random.uniform(0, 0.3)
        
        return jsonify({
            'status': '1',
            'info': 'OK',
            'traffic_matrix': traffic_matrix
        })
        
    except Exception as e:
        return jsonify({
            'status': '0',
            'info': str(e)
        }), 500


@app.route('/api/solve', methods=['POST'])
def solve_vrp():
    try:
        data = request.json
        
        locations = data.get('locations', [])
        vehicle_capacity = float(data.get('vehicle_capacity', 100))
        num_vehicles = int(data.get('num_vehicles', 3))
        time_windows = data.get('time_windows', {})
        forbidden_areas = data.get('forbidden_areas', [])
        locked_routes = data.get('locked_routes', [])
        traffic_data = data.get('traffic_data', {})
        objective_weights = data.get('objective_weights', {})
        
        if len(locations) < 2:
            return jsonify({
                'error': '至少需要一个仓库和一个配送点'
            }), 400
        
        solver = VRPSolver(
            locations=locations,
            vehicle_capacity=vehicle_capacity,
            num_vehicles=num_vehicles,
            time_windows=time_windows,
            forbidden_areas=forbidden_areas,
            locked_routes=locked_routes,
            traffic_data=traffic_data,
            objective_weights=objective_weights
        )
        
        result = solver.solve(
            population_size=int(data.get('population_size', 100)),
            generations=int(data.get('generations', 50))
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/capacity/analyze', methods=['POST'])
def analyze_capacity():
    try:
        data = request.json
        locations = data.get('locations', [])
        vehicle_capacity = float(data.get('vehicle_capacity', 100))
        num_vehicles = int(data.get('num_vehicles', 3))
        
        if len(locations) < 2:
            return jsonify({
                'error': '至少需要一个仓库和一个配送点'
            }), 400
        
        solver = VRPSolver(
            locations=locations,
            vehicle_capacity=vehicle_capacity,
            num_vehicles=num_vehicles
        )
        
        result = solver.analyze_capacity()
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/recalculate', methods=['POST'])
def recalculate_route():
    try:
        data = request.json
        locations = data.get('locations', [])
        routes = data.get('routes', [])
        
        from geopy.distance import geodesic
        
        result = {
            'routes': [],
            'total_distance': 0,
            'total_load': 0
        }
        
        vehicle_capacity = float(data.get('vehicle_capacity', 100))
        
        for route_data in routes:
            route_distance = 0.0
            route_load = 0.0
            points = []
            
            for loc_idx in route_data.get('location_indices', []):
                if loc_idx < len(locations):
                    loc = locations[loc_idx]
                    points.append({'lat': loc['lat'], 'lng': loc['lng']})
                    if loc_idx > 0:
                        route_load += loc.get('demand', 0)
            
            for i in range(len(points) - 1):
                coord1 = (points[i]['lat'], points[i]['lng'])
                coord2 = (points[i+1]['lat'], points[i+1]['lng'])
                route_distance += geodesic(coord1, coord2).kilometers
            
            result['routes'].append({
                'vehicle_id': route_data.get('vehicle_id'),
                'color': route_data.get('color', '#3498db'),
                'points': points,
                'location_indices': route_data.get('location_indices', []),
                'distance': round(route_distance, 2),
                'load': round(route_load, 2),
                'load_rate': round(route_load / vehicle_capacity * 100, 1) if vehicle_capacity > 0 else 0,
                'locked': route_data.get('locked', False)
            })
            
            result['total_distance'] += route_distance
            result['total_load'] += route_load
        
        result['total_distance'] = round(result['total_distance'], 2)
        result['total_load'] = round(result['total_load'], 2)
        result['used_vehicles'] = len(routes)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
