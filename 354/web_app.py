import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, render_template, request, jsonify, send_from_directory
import json
import time
import random
from datetime import datetime

from src.review_system import HumanReviewSystem
from src.publisher_network import PublisherNetworkAnalyzer
from src.attribution_analyzer import AttributionAnalyzer

app = Flask(__name__, 
            template_folder='web/templates', 
            static_folder='web/static')

review_system = HumanReviewSystem()
network_analyzer = PublisherNetworkAnalyzer()
attribution_analyzer = AttributionAnalyzer()

def init_sample_data():
    sample_ips = [f"192.168.1.{i}" for i in range(1, 50)]
    sample_devices = [f"device_{i:03d}" for i in range(1, 30)]
    publishers = [f"pub_{i:02d}" for i in range(1, 11)]
    campaigns = [f"camp_{i:02d}" for i in range(1, 6)]
    
    base_time = time.time() - 3600
    
    for i in range(200):
        ip = random.choice(sample_ips)
        device = random.choice(sample_devices)
        publisher = random.choice(publishers)
        campaign = random.choice(campaigns)
        fraud_score = random.random()
        is_fraud = fraud_score > 0.7
        action = "block" if fraud_score > 0.9 else "discount" if fraud_score > 0.7 else "observe"
        
        click_id = f"click_{i:05d}"
        ts = base_time + i * 30
        
        review_system.add_sample(
            click_id=click_id,
            ip=ip,
            device_id=device,
            publisher_id=publisher,
            fraud_score=fraud_score,
            predicted_action=action,
            rule_hits=["high_frequency", "suspicious_pattern"][:random.randint(0, 2)],
            model_features={
                'click_count': random.randint(1, 100),
                'avg_interval': random.uniform(0.1, 10),
                'entropy': random.uniform(0, 1)
            }
        )
        
        network_analyzer.record_click(
            publisher_id=publisher,
            ip=ip,
            device_id=device,
            session_id=f"sess_{i % 20}",
            is_fraud=is_fraud
        )
        
        attribution_analyzer.add_click(
            click_id=click_id,
            ip=ip,
            device_id=device,
            publisher_id=publisher,
            campaign_id=campaign,
            timestamp=ts,
            fraud_score=fraud_score,
            is_fraud=is_fraud,
            action_taken=action,
            cost=random.uniform(0.3, 2.0)
        )
    
    for i in range(50):
        ip = random.choice(sample_ips[:20])
        device = random.choice(sample_devices[:15])
        campaign = random.choice(campaigns)
        
        attribution_analyzer.add_conversion(
            conversion_id=f"conv_{i:03d}",
            ip=ip,
            device_id=device,
            campaign_id=campaign,
            timestamp=base_time + 200 * 30 + i * 120 + random.uniform(0, 3600),
            revenue=random.uniform(20, 200),
            conversion_type=random.choice(["purchase", "signup", "download"])
        )
    
    pending = review_system.get_pending_samples(limit=30)
    for j, sample in enumerate(pending[:20]):
        label = "fraud" if sample.fraud_score > 0.6 else "legitimate"
        review_system.review_sample(sample.sample_id, label, reviewer="system_init")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/review')
def review():
    return render_template('review.html')

@app.route('/network')
def network():
    return render_template('network.html')

@app.route('/attribution')
def attribution():
    return render_template('attribution.html')

@app.route('/api/dashboard')
def api_dashboard():
    data = review_system.get_dashboard_data()
    return jsonify(data)

@app.route('/api/samples/pending')
def api_pending_samples():
    limit = int(request.args.get('limit', 50))
    publisher = request.args.get('publisher')
    min_score = request.args.get('min_score')
    min_score = float(min_score) if min_score else None
    
    samples = review_system.get_pending_samples(
        limit=limit,
        publisher_id=publisher,
        min_score=min_score
    )
    
    return jsonify([{
        'sample_id': s.sample_id,
        'click_id': s.click_id,
        'ip': s.ip,
        'device_id': s.device_id,
        'publisher_id': s.publisher_id,
        'fraud_score': s.fraud_score,
        'predicted_action': s.predicted_action,
        'rule_hits': s.rule_hits,
        'timestamp': s.timestamp,
        'time_str': datetime.fromtimestamp(s.timestamp).strftime('%Y-%m-%d %H:%M:%S')
    } for s in samples])

@app.route('/api/sample/<sample_id>')
def api_get_sample(sample_id):
    sample = review_system.get_sample(sample_id)
    if not sample:
        return jsonify({'error': 'Sample not found'}), 404
    
    return jsonify({
        'sample_id': sample.sample_id,
        'click_id': sample.click_id,
        'ip': sample.ip,
        'device_id': sample.device_id,
        'publisher_id': sample.publisher_id,
        'timestamp': sample.timestamp,
        'time_str': datetime.fromtimestamp(sample.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        'fraud_score': sample.fraud_score,
        'predicted_action': sample.predicted_action,
        'rule_hits': sample.rule_hits,
        'model_features': sample.model_features,
        'review_status': sample.review_status,
        'reviewed_by': sample.reviewed_by,
        'actual_label': sample.actual_label,
        'review_notes': sample.review_notes
    })

@app.route('/api/sample/<sample_id>/review', methods=['POST'])
def api_review_sample(sample_id):
    data = request.json
    actual_label = data.get('actual_label')
    reviewer = data.get('reviewer', 'admin')
    notes = data.get('notes')
    
    if actual_label not in ['fraud', 'legitimate', 'uncertain']:
        return jsonify({'error': 'Invalid label'}), 400
    
    success = review_system.review_sample(sample_id, actual_label, reviewer, notes)
    if not success:
        return jsonify({'error': 'Sample not found'}), 404
    
    return jsonify({'success': True})

@app.route('/api/samples/batch-review', methods=['POST'])
def api_batch_review():
    data = request.json
    sample_ids = data.get('sample_ids', [])
    actual_label = data.get('actual_label')
    reviewer = data.get('reviewer', 'admin')
    
    count = review_system.batch_review(sample_ids, actual_label, reviewer)
    return jsonify({'success': True, 'count': count})

@app.route('/api/network')
def api_network():
    stats = network_analyzer.get_network_statistics()
    return jsonify(stats)

@app.route('/api/network/graph')
def api_network_graph():
    graph_json = network_analyzer.export_network_json()
    return jsonify(json.loads(graph_json))

@app.route('/api/network/publisher/<publisher_id>')
def api_publisher_connections(publisher_id):
    data = network_analyzer.get_publisher_connections(publisher_id)
    return jsonify(data)

@app.route('/api/attribution/summary')
def api_attribution_summary():
    data = attribution_analyzer.get_fraud_impact_summary()
    return jsonify(data)

@app.route('/api/attribution/report')
def api_attribution_report():
    report = attribution_analyzer.generate_report()
    return jsonify(report)

@app.route('/api/attribution/timeseries')
def api_attribution_timeseries():
    hours = int(request.args.get('hours', 24))
    data = attribution_analyzer.get_time_series_data(hours)
    return jsonify(data)

@app.route('/api/attribution/publishers')
def api_attribution_publishers():
    data = attribution_analyzer.get_all_publishers_summary()
    return jsonify([{
        'publisher_id': p.publisher_id,
        'total_clicks': p.total_clicks,
        'total_conversions': p.total_conversions,
        'fraud_clicks': p.fraud_clicks,
        'fraud_cost': p.fraud_cost,
        'legitimate_revenue': p.legitimate_revenue,
        'roi': p.roi
    } for p in data])

@app.route('/api/stats')
def api_stats():
    network_analyzer.detect_communities()
    
    return jsonify({
        'review': review_system.calculate_statistics().__dict__,
        'network': network_analyzer.get_network_statistics(),
        'attribution': attribution_analyzer.get_fraud_impact_summary()['summary']
    })

if __name__ == '__main__':
    print("Initializing sample data...")
    init_sample_data()
    print("Starting web server at http://localhost:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
