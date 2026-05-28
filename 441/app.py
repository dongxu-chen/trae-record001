from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
import os

from config import Config
from data_generator import TimeSeriesDataGenerator
from prophet_detector import ProphetAnomalyDetector
from three_sigma_detector import ThreeSigmaDetector
from isolation_forest_detector import IsolationForestDetector
from anomaly_fusion import AnomalyFusion
from root_cause_analyzer import RootCauseAnalyzer
from es_storage import ElasticsearchStorage
from holiday_manager import HolidayManager
from anomaly_pattern_library import AnomalyPatternLibrary
from anomaly_predictor import AnomalyPredictor
from event_correlator import EventCorrelator
from incident_manager import IncidentManager

app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

storage = ElasticsearchStorage()
anomaly_fusion = AnomalyFusion()
root_cause_analyzer = RootCauseAnalyzer()
holiday_manager = HolidayManager()
pattern_library = AnomalyPatternLibrary()
anomaly_predictor = AnomalyPredictor()
event_correlator = EventCorrelator()
incident_manager = IncidentManager(storage_path='data/incidents.json')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'metrics': Config.METRICS
    })

@app.route('/api/generate-data', methods=['POST'])
def generate_data():
    data = request.json or {}
    days = data.get('days', 7)
    freq = data.get('freq', '5min')
    inject_anomalies = data.get('inject_anomalies', True)
    
    generator = TimeSeriesDataGenerator(days=days, freq=freq)
    df, injected_anomalies = generator.generate_metrics_data(inject_anomalies=inject_anomalies)
    
    storage.store_metrics(df)
    
    return jsonify({
        'success': True,
        'message': f'Generated {len(df)} data points',
        'date_range': {
            'start': df['timestamp'].min().isoformat(),
            'end': df['timestamp'].max().isoformat()
        },
        'injected_anomalies_count': len(injected_anomalies)
    })

@app.route('/api/metrics', methods=['GET'])
def get_metrics():
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    metric_type = request.args.get('metric_type')
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
    if end_time_str:
        end_time = datetime.fromisoformat(end_time_str)
    
    df = storage.query_metrics(start_time, end_time, metric_type)
    
    if df.empty:
        return jsonify({
            'success': True,
            'data': [],
            'count': 0
        })
    
    result_data = []
    for _, row in df.iterrows():
        result_data.append({
            'timestamp': row['timestamp'].isoformat(),
            'metric_type': row['metric_type'],
            'value': row['value']
        })
    
    return jsonify({
        'success': True,
        'data': result_data,
        'count': len(result_data)
    })

@app.route('/api/detect/prophet', methods=['POST'])
def detect_prophet():
    data = request.json or {}
    metric = data.get('metric', 'qps')
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    detector = ProphetAnomalyDetector()
    anomalies = detector.get_anomaly_points(df_pivot, metric)
    
    return jsonify({
        'success': True,
        'method': 'prophet',
        'metric': metric,
        'anomalies_count': len(anomalies),
        'anomalies': [
            {**a, 'timestamp': a['timestamp'].isoformat() if isinstance(a['timestamp'], datetime) else str(a['timestamp'])}
            for a in anomalies
        ]
    })

@app.route('/api/detect/three-sigma', methods=['POST'])
def detect_three_sigma():
    data = request.json or {}
    metric = data.get('metric', 'qps')
    use_rolling = data.get('use_rolling', False)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    detector = ThreeSigmaDetector()
    anomalies = detector.get_anomaly_points(df_pivot, metric, use_rolling=use_rolling)
    
    return jsonify({
        'success': True,
        'method': 'three_sigma',
        'metric': metric,
        'anomalies_count': len(anomalies),
        'anomalies': [
            {**a, 'timestamp': a['timestamp'].isoformat() if isinstance(a['timestamp'], datetime) else str(a['timestamp'])}
            for a in anomalies
        ]
    })

@app.route('/api/detect/isolation-forest', methods=['POST'])
def detect_isolation_forest():
    data = request.json or {}
    metric = data.get('metric', 'qps')
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    detector = IsolationForestDetector()
    anomalies = detector.get_anomaly_points(df_pivot, metric)
    
    return jsonify({
        'success': True,
        'method': 'isolation_forest',
        'metric': metric,
        'anomalies_count': len(anomalies),
        'anomalies': [
            {**a, 'timestamp': a['timestamp'].isoformat() if isinstance(a['timestamp'], datetime) else str(a['timestamp'])}
            for a in anomalies
        ]
    })

@app.route('/api/detect/fusion', methods=['POST'])
def detect_fusion():
    data = request.json or {}
    metrics = data.get('metrics', Config.METRICS)
    top_n = data.get('top_n', 20)
    score_threshold = data.get('score_threshold', 0.1)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.get_top_anomalies(df_pivot, metrics, top_n, score_threshold)
    
    return jsonify({
        'success': True,
        'method': 'fusion',
        'metrics': metrics,
        'anomalies_count': len(anomalies),
        'anomalies': [
            {**a, 'timestamp': a['timestamp'].isoformat() if isinstance(a['timestamp'], datetime) else str(a['timestamp'])}
            for a in anomalies
        ]
    })

@app.route('/api/detect/joint', methods=['POST'])
def detect_joint():
    data = request.json or {}
    metrics = data.get('metrics', Config.METRICS)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    joint_anomalies = anomaly_fusion.detect_joint_anomalies(df_pivot, metrics)
    
    return jsonify({
        'success': True,
        'method': 'joint_detection',
        'metrics': metrics,
        'anomalies_count': len(joint_anomalies),
        'anomalies': [
            {**a, 'timestamp': a['timestamp'].isoformat() if isinstance(a['timestamp'], datetime) else str(a['timestamp'])}
            for a in joint_anomalies
        ]
    })

@app.route('/api/detect/full', methods=['POST'])
def detect_full():
    data = request.json or {}
    metrics = data.get('metrics', Config.METRICS)
    store_results = data.get('store_results', True)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.fuse_anomalies(df_pivot, metrics)
    
    anomalies_with_root = root_cause_analyzer.analyze_root_causes(df_pivot, anomalies, metrics)
    
    if store_results:
        storage.store_anomalies(anomalies_with_root)
    
    summary = anomaly_fusion.get_anomaly_summary(df_pivot, metrics)
    
    return jsonify({
        'success': True,
        'method': 'full_detection',
        'metrics': metrics,
        'summary': summary,
        'anomalies_count': len(anomalies_with_root),
        'anomalies': [
            json.loads(json.dumps(a, default=str))
            for a in anomalies_with_root
        ]
    })

@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    start_time_str = request.args.get('start_time')
    end_time_str = request.args.get('end_time')
    min_score = float(request.args.get('min_score', 0.0))
    limit = int(request.args.get('limit', 100))
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=30)
    
    if start_time_str:
        start_time = datetime.fromisoformat(start_time_str)
    if end_time_str:
        end_time = datetime.fromisoformat(end_time_str)
    
    anomalies = storage.query_anomalies(start_time, end_time, min_score, limit)
    
    return jsonify({
        'success': True,
        'count': len(anomalies),
        'anomalies': anomalies
    })

@app.route('/api/anomaly/summary', methods=['GET'])
def get_anomaly_summary():
    days = int(request.args.get('days', 7))
    
    summary = storage.get_anomaly_summary(days)
    
    return jsonify({
        'success': True,
        'summary': summary
    })

@app.route('/api/root-cause', methods=['POST'])
def analyze_root_cause():
    data = request.json or {}
    timestamp_str = data.get('timestamp')
    
    if not timestamp_str:
        return jsonify({'success': False, 'error': 'Timestamp is required'})
    
    timestamp = datetime.fromisoformat(timestamp_str)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.fuse_anomalies(df_pivot, Config.METRICS)
    
    target_anomaly = None
    for a in anomalies:
        if abs((a['timestamp'] - timestamp).total_seconds()) < 300:
            target_anomaly = a
            break
    
    if not target_anomaly:
        return jsonify({'success': False, 'error': 'Anomaly not found at given timestamp'})
    
    anomalies_with_root = root_cause_analyzer.analyze_root_causes(
        df_pivot, [target_anomaly], Config.METRICS
    )
    
    incident_report = root_cause_analyzer.generate_incident_report(target_anomaly)
    
    return jsonify({
        'success': True,
        'anomaly': json.loads(json.dumps(anomalies_with_root[0], default=str)),
        'incident_report': incident_report
    })

@app.route('/api/time-series', methods=['GET'])
def get_time_series():
    metric = request.args.get('metric', 'qps')
    days = int(request.args.get('days', 7))
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    ts_data = anomaly_fusion.get_time_series_with_anomalies(df_pivot, [metric])
    
    metric_data = ts_data.get(metric, pd.DataFrame())
    
    if metric_data.empty:
        return jsonify({'success': True, 'data': []})
    
    result_data = []
    for _, row in metric_data.iterrows():
        result_data.append({
            'timestamp': row['timestamp'].isoformat(),
            'value': row['value'],
            'fused_score': row['fused_score'],
            'is_anomaly': row['is_fused_anomaly']
        })
    
    return jsonify({
        'success': True,
        'metric': metric,
        'data': result_data
    })

@app.route('/api/holidays', methods=['GET'])
def get_holidays():
    year = request.args.get('year')
    year = int(year) if year else None
    
    holidays = holiday_manager.get_holiday_list(year)
    
    return jsonify({
        'success': True,
        'year': year,
        'holidays': holidays,
        'count': len(holidays)
    })

@app.route('/api/holidays', methods=['POST'])
def add_holiday():
    data = request.json or {}
    dates = data.get('dates', [])
    
    if not dates:
        return jsonify({'success': False, 'error': 'No dates provided'})
    
    holiday_manager.add_holidays(dates)
    
    return jsonify({
        'success': True,
        'message': f'Added {len(dates)} holidays',
        'holidays': holiday_manager.get_holiday_list()
    })

@app.route('/api/holidays/check', methods=['POST'])
def check_holiday():
    data = request.json or {}
    date_str = data.get('date')
    
    if not date_str:
        return jsonify({'success': False, 'error': 'Date is required'})
    
    date = datetime.fromisoformat(date_str)
    is_special, day_type = holiday_manager.is_special_day(date)
    
    return jsonify({
        'success': True,
        'date': date_str,
        'is_holiday': is_special,
        'day_type': day_type
    })

@app.route('/api/patterns', methods=['GET'])
def get_patterns():
    patterns = pattern_library.get_all_patterns()
    
    return jsonify({
        'success': True,
        'patterns': patterns,
        'count': len(patterns)
    })

@app.route('/api/patterns/match', methods=['POST'])
def match_patterns():
    data = request.json or {}
    anomaly_ids = data.get('anomaly_ids', [])
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.fuse_anomalies(df_pivot, Config.METRICS)
    
    matched_patterns = pattern_library.match_patterns(anomalies, df_pivot)
    
    return jsonify({
        'success': True,
        'matched_patterns_count': len(matched_patterns),
        'matched_patterns': matched_patterns
    })

@app.route('/api/patterns/<pattern_id>', methods=['GET'])
def get_pattern(pattern_id):
    pattern = pattern_library.get_pattern_by_id(pattern_id)
    
    if not pattern:
        return jsonify({'success': False, 'error': 'Pattern not found'})
    
    return jsonify({
        'success': True,
        'pattern': {
            'id': pattern.id,
            'name': pattern.name,
            'description': pattern.description,
            'severity': pattern.severity,
            'metric_patterns': pattern.metric_patterns,
            'temporal_relation': pattern.temporal_relation,
            'confidence': pattern.confidence,
            'root_cause_hint': pattern.root_cause_hint,
            'remediation_hint': pattern.remediation_hint
        }
    })

@app.route('/api/advanced/root-cause', methods=['POST'])
def advanced_root_cause():
    data = request.json or {}
    timestamp_str = data.get('timestamp')
    
    if not timestamp_str:
        return jsonify({'success': False, 'error': 'Timestamp is required'})
    
    timestamp = datetime.fromisoformat(timestamp_str)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.fuse_anomalies(df_pivot, Config.METRICS)
    
    target_anomaly = None
    for a in anomalies:
        if abs((a['timestamp'] - timestamp).total_seconds()) < 300:
            target_anomaly = a
            break
    
    if not target_anomaly:
        return jsonify({'success': False, 'error': 'Anomaly not found at given timestamp'})
    
    anomalies_with_root = root_cause_analyzer.analyze_root_causes(
        df_pivot, [target_anomaly], Config.METRICS
    )
    
    result = anomalies_with_root[0]
    root_causes = result.get('root_cause_candidates', [])
    
    return jsonify({
        'success': True,
        'most_probable_root_cause': result.get('most_probable_root_cause'),
        'root_cause_candidates': [
            {
                'rank': rc.get('probability_rank'),
                'cause_type': rc.get('cause_type'),
                'cause': rc.get('cause'),
                'description': rc.get('description'),
                'prior_probability': rc.get('prior_probability'),
                'posterior_probability': rc.get('posterior_probability'),
                'normalized_probability': rc.get('normalized_probability'),
                'confidence': rc.get('confidence')
            }
            for rc in root_causes
        ],
        'anomaly_details': {
            'timestamp': result['timestamp'].isoformat() if isinstance(result['timestamp'], datetime) else str(result['timestamp']),
            'total_score': result.get('total_score'),
            'matched_pattern': result.get('best_matched_pattern'),
            'is_joint_anomaly': result.get('is_joint_anomaly')
        }
    })

@app.route('/api/predict/anomalies', methods=['POST'])
def predict_anomalies():
    data = request.json or {}
    metrics = data.get('metrics', Config.METRICS)
    threshold_hours = data.get('threshold_hours', 6)
    min_score = data.get('min_score', 0.5)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    combined_alerts = anomaly_predictor.get_combined_alerts(
        df_pivot, metrics, threshold_hours, min_score
    )
    
    detailed_alerts = anomaly_predictor.predict_all_metrics(df_pivot, metrics, threshold_hours)
    
    return jsonify({
        'success': True,
        'prediction_window_hours': threshold_hours,
        'combined_alerts_count': len(combined_alerts),
        'combined_alerts': [
            {
                **alert,
                'alerts': [
                    {
                        **a,
                        'predicted_time': a['predicted_time'].isoformat()
                    }
                    for a in alert['alerts']
                ]
            }
            for alert in combined_alerts
        ],
        'detailed_alerts': {
            metric: [
                {
                    **a,
                    'predicted_time': a['predicted_time'].isoformat()
                }
                for a in alerts
            ]
            for metric, alerts in detailed_alerts.items()
        }
    })

@app.route('/api/events/correlate', methods=['POST'])
def correlate_events():
    data = request.json or {}
    time_window_minutes = data.get('time_window_minutes', 30)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.fuse_anomalies(df_pivot, Config.METRICS)
    
    correlator = EventCorrelator(
        time_window_minutes=time_window_minutes,
        similarity_threshold=0.6
    )
    
    events = correlator.correlate_anomalies(anomalies)
    merged_events = correlator.merge_similar_events(events)
    
    summary = correlator.get_summary(events)
    
    return jsonify({
        'success': True,
        'summary': summary,
        'events_count': len(events),
        'merged_events_count': len(merged_events),
        'events': [
            {
                **event.to_dict(),
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat() if event.end_time else None
            }
            for event in events
        ],
        'merged_events': [
            {
                **event.to_dict(),
                'start_time': event.start_time.isoformat(),
                'end_time': event.end_time.isoformat() if event.end_time else None
            }
            for event in merged_events
        ]
    })

@app.route('/api/incidents', methods=['GET'])
def get_incidents():
    status = request.args.get('status')
    priority = request.args.get('priority')
    
    incidents = incident_manager.get_all_incidents(status=status, priority=priority)
    
    summary = incident_manager.get_incident_summary()
    
    return jsonify({
        'success': True,
        'summary': summary,
        'count': len(incidents),
        'incidents': [
            incident_manager._incident_to_dict(i)
            for i in incidents
        ]
    })

@app.route('/api/incidents', methods=['POST'])
def create_incident():
    data = request.json or {}
    
    timestamp_str = data.get('timestamp')
    if not timestamp_str:
        return jsonify({'success': False, 'error': 'Timestamp is required'})
    
    timestamp = datetime.fromisoformat(timestamp_str)
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    df = storage.query_metrics(start_time, end_time)
    
    if df.empty:
        return jsonify({'success': False, 'error': 'No data available'})
    
    df_pivot = df.pivot(index='timestamp', columns='metric_type', values='value').reset_index()
    
    anomalies = anomaly_fusion.fuse_anomalies(df_pivot, Config.METRICS)
    
    target_anomaly = None
    for a in anomalies:
        if abs((a['timestamp'] - timestamp).total_seconds()) < 300:
            target_anomaly = a
            break
    
    if not target_anomaly:
        return jsonify({'success': False, 'error': 'Anomaly not found at given timestamp'})
    
    incident = incident_manager.create_incident_from_anomaly(
        target_anomaly,
        title=data.get('title'),
        description=data.get('description')
    )
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/<incident_id>', methods=['GET'])
def get_incident(incident_id):
    incident = incident_manager.get_incident(incident_id)
    
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/<incident_id>/acknowledge', methods=['POST'])
def acknowledge_incident(incident_id):
    data = request.json or {}
    user = data.get('user', 'system')
    
    incident = incident_manager.acknowledge_incident(incident_id, user)
    
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/<incident_id>/start-treatment', methods=['POST'])
def start_treatment(incident_id):
    data = request.json or {}
    user = data.get('user', 'system')
    description = data.get('description', '开始处置')
    
    incident = incident_manager.start_treatment(incident_id, user, description)
    
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/<incident_id>/add-log', methods=['POST'])
def add_action_log(incident_id):
    data = request.json or {}
    action_type = data.get('action_type', 'note')
    description = data.get('description', '')
    user = data.get('user', 'system')
    details = data.get('details')
    
    incident = incident_manager.add_action_log(
        incident_id, action_type, description, user, details
    )
    
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/<incident_id>/feedback', methods=['POST'])
def add_effect_feedback(incident_id):
    data = request.json or {}
    metric = data.get('metric')
    before_value = data.get('before_value')
    after_value = data.get('after_value')
    user = data.get('user', 'system')
    
    if not metric or before_value is None or after_value is None:
        return jsonify({'success': False, 'error': 'metric, before_value, and after_value are required'})
    
    feedback = incident_manager.add_effect_feedback(
        incident_id, metric, float(before_value), float(after_value), user
    )
    
    if not feedback:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'feedback': {
            'timestamp': feedback.timestamp.isoformat(),
            'metric': feedback.metric,
            'before_value': feedback.before_value,
            'after_value': feedback.after_value,
            'improvement_pct': feedback.improvement_pct,
            'is_effective': feedback.is_effective
        }
    })

@app.route('/api/incidents/<incident_id>/resolve', methods=['POST'])
def resolve_incident(incident_id):
    data = request.json or {}
    resolution_notes = data.get('resolution_notes', '')
    user = data.get('user', 'system')
    
    incident = incident_manager.resolve_incident(incident_id, resolution_notes, user)
    
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/<incident_id>/close', methods=['POST'])
def close_incident(incident_id):
    data = request.json or {}
    user = data.get('user', 'system')
    
    incident = incident_manager.close_incident(incident_id, user)
    
    if not incident:
        return jsonify({'success': False, 'error': 'Incident not found'})
    
    return jsonify({
        'success': True,
        'incident': incident_manager._incident_to_dict(incident)
    })

@app.route('/api/incidents/summary', methods=['GET'])
def get_incident_summary():
    summary = incident_manager.get_incident_summary()
    effectiveness = incident_manager.get_effectiveness_stats()
    
    return jsonify({
        'success': True,
        'summary': summary,
        'effectiveness': effectiveness
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'success': False, 'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

if __name__ == '__main__':
    os.makedirs('data', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
