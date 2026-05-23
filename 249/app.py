from flask import Flask, render_template, jsonify, request
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import os

from config import STATIONS, DATA_DIR
from data_processor import DataProcessor
from prediction_model import HybridPredictionModel
from analysis_module import FlowAnalyzer

app = Flask(__name__)

processor = DataProcessor()
model = HybridPredictionModel()
analyzer = FlowAnalyzer()

historical_data = None
weather_data = None
current_predictions = None


def initialize_data():
    global historical_data, weather_data
    
    start_date = datetime.now() - timedelta(days=30)
    
    if os.path.exists(os.path.join(DATA_DIR, 'historical_data.csv')):
        historical_data = pd.read_csv(os.path.join(DATA_DIR, 'historical_data.csv'), parse_dates=['timestamp'])
    else:
        historical_data = processor.generate_sample_data(start_date, days=30)
        historical_data.to_csv(os.path.join(DATA_DIR, 'historical_data.csv'), index=False)
    
    if os.path.exists(os.path.join(DATA_DIR, 'weather_data.csv')):
        weather_data = pd.read_csv(os.path.join(DATA_DIR, 'weather_data.csv'), parse_dates=['timestamp'])
    else:
        weather_data = processor.generate_weather_data(start_date, days=30)
        weather_data.to_csv(os.path.join(DATA_DIR, 'weather_data.csv'), index=False)
    
    historical_data = processor.add_time_features(historical_data)
    historical_data = processor.merge_weather_data(historical_data, weather_data)


def train_or_load_models():
    try:
        model.load_models()
        print("Models loaded successfully")
    except:
        print("Training new models...")
        model.train_all(historical_data)
        model.save_models()
        print("Models trained and saved")


@app.route('/')
def index():
    return render_template('index.html', stations=STATIONS)


@app.route('/api/predict', methods=['GET'])
def predict():
    global current_predictions
    station = request.args.get('station', STATIONS[0])
    hours = int(request.args.get('hours', 1))
    
    start_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    predictions = model.predict_next_hours(historical_data, start_time, hours=hours)
    current_predictions = predictions
    
    return jsonify({
        'station': station,
        'predictions': predictions[station],
        'all_stations': predictions
    })


@app.route('/api/predict_with_closure', methods=['POST'])
def predict_with_closure():
    data = request.json
    closed_stations = data.get('closed_stations', [])
    hours = int(data.get('hours', 1))
    
    start_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    predictions = model.predict_next_hours(historical_data, start_time, hours=hours)
    adjusted_predictions = model.apply_station_closure(predictions, closed_stations)
    
    return jsonify({
        'closed_stations': closed_stations,
        'predictions': adjusted_predictions
    })


@app.route('/api/apply_event_adjustment', methods=['POST'])
def apply_event_adjustment():
    data = request.json
    event_config = data.get('event_config', {})
    hours = int(data.get('hours', 1))
    
    start_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    
    predictions = model.predict_next_hours(historical_data, start_time, hours=hours)
    adjusted_predictions = model.apply_event_adjustment(predictions, event_config)
    
    return jsonify({
        'event_config': event_config,
        'original_predictions': predictions,
        'adjusted_predictions': adjusted_predictions
    })


@app.route('/api/od_matrix', methods=['GET'])
def get_od_matrix():
    current_time = datetime.now()
    top_n = request.args.get('top_n', type=int, default=None)
    
    if top_n:
        od_data = processor.generate_od_matrix(current_time, top_n=top_n)
        return jsonify({
            'stations': STATIONS,
            'full_matrix': od_data['full_matrix'],
            'top_matrix': od_data['top_matrix'],
            'top_routes': od_data['top_routes'],
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        od_matrix = processor.generate_od_matrix(current_time)
        return jsonify({
            'stations': STATIONS,
            'matrix': od_matrix.tolist(),
            'timestamp': current_time.strftime('%Y-%m-%d %H:%M:%S')
        })


@app.route('/api/historical', methods=['GET'])
def get_historical():
    station = request.args.get('station', STATIONS[0])
    days = int(request.args.get('days', 7))
    
    end_date = historical_data['timestamp'].max()
    start_date = end_date - timedelta(days=days)
    
    station_data = historical_data[
        (historical_data['station'] == station) & 
        (historical_data['timestamp'] >= start_date)
    ].sort_values('timestamp')
    
    return jsonify({
        'station': station,
        'timestamps': station_data['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist(),
        'in_flow': station_data['in_flow'].tolist(),
        'out_flow': station_data['out_flow'].tolist()
    })


@app.route('/api/stations', methods=['GET'])
def get_stations():
    return jsonify({'stations': STATIONS})


@app.route('/api/station_stats', methods=['GET'])
def get_station_stats():
    stats = []
    for station in STATIONS:
        station_data = historical_data[historical_data['station'] == station]
        stats.append({
            'station': station,
            'avg_in_flow': int(station_data['in_flow'].mean()),
            'avg_out_flow': int(station_data['out_flow'].mean()),
            'max_in_flow': int(station_data['in_flow'].max()),
            'max_out_flow': int(station_data['out_flow'].max())
        })
    
    return jsonify({'stats': stats})


@app.route('/api/real_time_alerts', methods=['GET'])
def get_real_time_alerts():
    global current_predictions
    
    if current_predictions is None:
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        current_predictions = model.predict_next_hours(historical_data, start_time, hours=1)
    
    alerts = analyzer.get_all_stations_alerts(historical_data, current_predictions)
    
    return jsonify({
        'alerts': alerts,
        'total_alerts': len(alerts),
        'high_priority_count': len([a for a in alerts if a['level'] == 'high'])
    })


@app.route('/api/trend_analysis', methods=['GET'])
def get_trend_analysis():
    station = request.args.get('station', STATIONS[0])
    
    analysis = analyzer.fast_slow_line_analysis(historical_data, station)
    
    return jsonify(analysis)


@app.route('/api/dispatch_recommendations', methods=['GET'])
def get_dispatch_recommendations():
    current_time = datetime.now()
    od_matrix = processor.generate_od_matrix(current_time)
    
    global current_predictions
    if current_predictions is None:
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        current_predictions = model.predict_next_hours(historical_data, start_time, hours=1)
    
    recommendations = analyzer.generate_dispatch_recommendations(od_matrix, current_predictions)
    
    return jsonify(recommendations)


@app.route('/api/anomaly_detection', methods=['GET'])
def get_anomaly_detection():
    station = request.args.get('station', STATIONS[0])
    hours = int(request.args.get('hours', 24))
    
    global current_predictions
    if current_predictions is None:
        start_time = datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        current_predictions = model.predict_next_hours(historical_data, start_time, hours=1)
    
    anomalies = analyzer.detect_flow_anomalies(historical_data, current_predictions, station, hours)
    
    return jsonify({
        'station': station,
        'anomalies': anomalies,
        'total_anomalies': len(anomalies)
    })


if __name__ == '__main__':
    os.makedirs(DATA_DIR, exist_ok=True)
    initialize_data()
    train_or_load_models()
    app.run(debug=True, host='0.0.0.0', port=5000)
