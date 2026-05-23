from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import numpy as np
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import Config
from data.data_loader import ODDataLoader
from models.model_trainer import ODPredictorTrainer
from utils.supply_demand_analyzer import SupplyDemandAnalyzer
from utils.event_simulator import EventSimulator

app = Flask(__name__, 
            template_folder='../templates',
            static_folder='../static')
CORS(app)

data_loader = None
predictor = None
supply_demand_analyzer = None
event_simulator = None

def initialize_data():
    global data_loader, predictor, supply_demand_analyzer, event_simulator
    print("Initializing data loader...")
    data_loader = ODDataLoader()
    data_loader.load_data()
    print("Data loader initialized.")
    
    print("Initializing predictor with meta-learning...")
    predictor = ODPredictorTrainer(use_meta_learning=True)
    meta_path = os.path.join(os.path.dirname(Config.MODEL_PATH), 'meta_predictor.pth')
    if os.path.exists(meta_path):
        predictor.load_model()
    elif os.path.exists(Config.MODEL_PATH):
        predictor.use_meta_learning = False
        predictor.load_model()
    else:
        predictor.train(epochs=20)
    print("Predictor initialized.")
    
    print("Initializing supply-demand analyzer...")
    supply_demand_analyzer = SupplyDemandAnalyzer()
    print("Supply-demand analyzer initialized.")
    
    print("Initializing event simulator...")
    event_simulator = EventSimulator()
    print("Event simulator initialized.")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/grid_centers', methods=['GET'])
def get_grid_centers():
    centers = data_loader.get_grid_centers()
    return jsonify({
        'grid_size': Config.GRID_SIZE,
        'centers': centers.to_dict('records')
    })

@app.route('/api/od_matrix', methods=['GET'])
def get_od_matrix():
    date = request.args.get('date', '2024-01-01')
    hour = int(request.args.get('hour', 8))
    
    od_matrix = data_loader.get_flattened_od(date, hour)
    
    heatmap_data = []
    for i in range(od_matrix.shape[0]):
        for j in range(od_matrix.shape[1]):
            if od_matrix[i, j] > 0:
                heatmap_data.append([int(i), int(j), float(od_matrix[i, j])])
    
    row_sums = np.sum(od_matrix, axis=1).tolist()
    col_sums = np.sum(od_matrix, axis=0).tolist()
    
    return jsonify({
        'date': date,
        'hour': hour,
        'heatmap_data': heatmap_data,
        'row_sums': row_sums,
        'col_sums': col_sums,
        'total_demand': float(np.sum(od_matrix)),
        'od_matrix': od_matrix.tolist()
    })

@app.route('/api/pred_od_matrix', methods=['GET'])
def get_pred_od_matrix():
    date = request.args.get('date', '2024-01-08')
    hour = int(request.args.get('hour', 8))
    
    history_matrices = []
    for h in range(max(0, hour - 3), hour):
        try:
            hist_matrix = data_loader.get_od_matrix('2024-01-01', h)
            history_matrices.append(hist_matrix)
        except:
            pass
    
    pred_matrix = predictor.predict_od(date, hour, history_matrices)
    
    heatmap_data = []
    for i in range(pred_matrix.shape[0]):
        for j in range(pred_matrix.shape[1]):
            if pred_matrix[i, j] > 0.1:
                heatmap_data.append([int(i), int(j), float(pred_matrix[i, j])])
    
    row_sums = np.sum(pred_matrix, axis=1).tolist()
    col_sums = np.sum(pred_matrix, axis=0).tolist()
    
    return jsonify({
        'date': date,
        'hour': hour,
        'heatmap_data': heatmap_data,
        'row_sums': row_sums,
        'col_sums': col_sums,
        'total_demand': float(np.sum(pred_matrix)),
        'od_matrix': pred_matrix.tolist()
    })

@app.route('/api/flow_data', methods=['GET'])
def get_flow_data():
    date = request.args.get('date', '2024-01-01')
    hour = int(request.args.get('hour', 8))
    top_k = int(request.args.get('top_k', 50))
    use_pred = request.args.get('pred', 'false').lower() == 'true'
    
    if use_pred:
        history_matrices = []
        for h in range(max(0, hour - 3), hour):
            try:
                hist_matrix = data_loader.get_od_matrix('2024-01-01', h)
                history_matrices.append(hist_matrix)
            except:
                pass
        
        pred_matrix = predictor.predict_od(date, hour, history_matrices)
        centers = data_loader.get_grid_centers()
        
        flows = []
        flat_indices = [(i, j, pred_matrix[i, j]) 
                       for i in range(pred_matrix.shape[0]) 
                       for j in range(pred_matrix.shape[1]) if i != j]
        flat_indices.sort(key=lambda x: x[2], reverse=True)
        
        for orig_idx, dest_idx, demand in flat_indices[:top_k]:
            if demand < 0.1:
                continue
            orig = centers.iloc[orig_idx]
            dest = centers.iloc[dest_idx]
            flows.append({
                'from': [float(orig['lon']), float(orig['lat'])],
                'to': [float(dest['lon']), float(dest['lat'])],
                'demand': float(demand),
                'origin_grid': int(orig_idx),
                'dest_grid': int(dest_idx)
            })
    else:
        flows = data_loader.get_flow_data(date, hour, top_k)
    
    return jsonify({
        'date': date,
        'hour': hour,
        'flows': flows
    })

@app.route('/api/trend', methods=['GET'])
def get_trend():
    date = request.args.get('date', '2024-01-08')
    start_hour = int(request.args.get('start_hour', 0))
    hours = int(request.args.get('hours', 24))
    granularity = request.args.get('granularity', '1h')
    
    if granularity not in ['5min', '15min', '1h']:
        granularity = '1h'
    
    trend_data = predictor.predict_trend(date, start_hour, hours, granularity)
    
    return jsonify({
        'date': date,
        'start_hour': start_hour,
        'hours': hours,
        'granularity': granularity,
        'trend': trend_data
    })

@app.route('/api/similar_grids', methods=['GET'])
def get_similar_grids():
    grid_idx = int(request.args.get('grid_idx', 0))
    similar_info = predictor.get_similar_grids_info(grid_idx)
    return jsonify(similar_info)

@app.route('/api/model_info', methods=['GET'])
def get_model_info():
    return jsonify({
        'use_meta_learning': predictor.use_meta_learning,
        'model_type': 'MetaLearner' if predictor.use_meta_learning else 'SimpleODPredictor',
        'grid_size': Config.GRID_SIZE,
        'num_grids': Config.GRID_SIZE * Config.GRID_SIZE
    })

@app.route('/api/time_slots', methods=['GET'])
def get_time_slots():
    return jsonify({
        'time_slots': Config.TIME_SLOTS,
        'dates': ['2024-01-0' + str(d) for d in range(1, 8)],
        'granularities': [
            {'value': '5min', 'label': '5分钟'},
            {'value': '15min', 'label': '15分钟'},
            {'value': '1h', 'label': '1小时'}
        ]
    })

@app.route('/api/supply_demand', methods=['GET'])
def get_supply_demand():
    date = request.args.get('date', '2024-01-01')
    hour = int(request.args.get('hour', 8))
    use_pred = request.args.get('pred', 'false').lower() == 'true'
    
    if use_pred:
        history_matrices = []
        for h in range(max(0, hour - 3), hour):
            try:
                hist_matrix = data_loader.get_od_matrix('2024-01-01', h)
                history_matrices.append(hist_matrix)
            except:
                pass
        od_matrix = predictor.predict_od(date, hour, history_matrices)
    else:
        od_matrix = data_loader.get_flattened_od(date, hour)
    
    balance_analysis = supply_demand_analyzer.analyze_supply_demand_balance(date, hour, od_matrix)
    relocation_suggestions = supply_demand_analyzer.suggest_relocation(balance_analysis, top_k=5)
    
    centers = data_loader.get_grid_centers()
    
    return jsonify({
        'date': date,
        'hour': hour,
        'balance_analysis': balance_analysis,
        'relocation_suggestions': relocation_suggestions,
        'grid_centers': centers.to_dict('records')
    })

@app.route('/api/available_events', methods=['GET'])
def get_available_events():
    events = event_simulator.get_available_events()
    return jsonify({'events': events})

@app.route('/api/simulate_event', methods=['POST'])
def simulate_event():
    data = request.json
    event_type = data.get('event_type')
    event_params = data.get('params', {})
    date = data.get('date', '2024-01-01')
    hour = int(data.get('hour', 8))
    use_pred = data.get('use_pred', False)
    
    if use_pred:
        history_matrices = []
        for h in range(max(0, hour - 3), hour):
            try:
                hist_matrix = data_loader.get_od_matrix('2024-01-01', h)
                history_matrices.append(hist_matrix)
            except:
                pass
        base_od = predictor.predict_od(date, hour, history_matrices)
    else:
        base_od = data_loader.get_flattened_od(date, hour)
    
    event_result = event_simulator.simulate_event(event_type, event_params, base_od, date, hour)
    diff_stats = event_simulator.compare_od_diff(base_od, np.array(event_result['affected_od']))
    
    centers = data_loader.get_grid_centers()
    affected_flows = []
    affected_od = np.array(event_result['affected_od'])
    
    flat_indices = [(i, j, affected_od[i, j], base_od[i, j]) 
                   for i in range(affected_od.shape[0]) 
                   for j in range(affected_od.shape[1]) if i != j]
    flat_indices.sort(key=lambda x: abs(x[2] - x[3]), reverse=True)
    
    for orig_idx, dest_idx, demand, base_demand in flat_indices[:50]:
        if abs(demand - base_demand) < 0.1:
            continue
        orig = centers.iloc[orig_idx]
        dest = centers.iloc[dest_idx]
        affected_flows.append({
            'from': [float(orig['lon']), float(orig['lat'])],
            'to': [float(dest['lon']), float(dest['lat'])],
            'demand': float(demand),
            'base_demand': float(base_demand),
            'diff': float(demand - base_demand),
            'origin_grid': int(orig_idx),
            'dest_grid': int(dest_idx)
        })
    
    return jsonify({
        'event_result': event_result,
        'diff_stats': diff_stats,
        'affected_flows': affected_flows,
        'base_total_demand': float(np.sum(base_od)),
        'affected_total_demand': float(np.sum(affected_od))
    })

@app.route('/api/3d_flow_data', methods=['GET'])
def get_3d_flow_data():
    date = request.args.get('date', '2024-01-01')
    hour = int(request.args.get('hour', 8))
    top_k = int(request.args.get('top_k', 30))
    use_pred = request.args.get('pred', 'false').lower() == 'true'
    
    centers = data_loader.get_grid_centers()
    
    if use_pred:
        history_matrices = []
        for h in range(max(0, hour - 3), hour):
            try:
                hist_matrix = data_loader.get_od_matrix('2024-01-01', h)
                history_matrices.append(hist_matrix)
            except:
                pass
        od_matrix = predictor.predict_od(date, hour, history_matrices)
    else:
        od_matrix = data_loader.get_flattened_od(date, hour)
    
    flows_3d = []
    flat_indices = [(i, j, od_matrix[i, j]) 
                   for i in range(od_matrix.shape[0]) 
                   for j in range(od_matrix.shape[1]) if i != j]
    flat_indices.sort(key=lambda x: x[2], reverse=True)
    
    max_demand = flat_indices[0][2] if flat_indices else 1
    
    for orig_idx, dest_idx, demand in flat_indices[:top_k]:
        if demand < 0.5:
            continue
        orig = centers.iloc[orig_idx]
        dest = centers.iloc[dest_idx]
        
        height = (demand / max_demand) * 50
        
        flows_3d.append({
            'from': {
                'x': float(orig['lon']),
                'y': float(orig['lat']),
                'z': 0,
                'grid_idx': int(orig_idx)
            },
            'to': {
                'x': float(dest['lon']),
                'y': float(dest['lat']),
                'z': height,
                'grid_idx': int(dest_idx)
            },
            'demand': float(demand),
            'normalized_demand': float(demand / max_demand),
            'height': float(height)
        })
    
    grid_points = []
    for _, grid in centers.iterrows():
        total_outflow = float(np.sum(od_matrix[int(grid['grid_id']), :]))
        total_inflow = float(np.sum(od_matrix[:, int(grid['grid_id'])]))
        grid_points.append({
            'x': float(grid['lon']),
            'y': float(grid['lat']),
            'z': 0,
            'grid_idx': int(grid['grid_id']),
            'total_outflow': total_outflow,
            'total_inflow': total_inflow,
            'net_flow': total_outflow - total_inflow
        })
    
    return jsonify({
        'date': date,
        'hour': hour,
        'flows_3d': flows_3d,
        'grid_points': grid_points,
        'max_demand': float(max_demand),
        'center_point': {
            'x': float(centers['lon'].mean()),
            'y': float(centers['lat'].mean()),
            'z': 25
        }
    })

if __name__ == '__main__':
    initialize_data()
    app.run(debug=True, host='0.0.0.0', port=5000)
