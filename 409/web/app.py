import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

socketio = SocketIO(cors_allowed_origins="*")


def create_app():
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'templates'),
                static_folder=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static'))
    
    app.config.from_object('config.Config')
    
    CORS(app)
    socketio.init_app(app)
    
    from data_pipeline import DataPipeline
    from crawlers.data_generator import MockDataGenerator
    
    pipeline = DataPipeline(use_kafka=app.config.get('ENABLE_KAFKA', False))
    data_generator = MockDataGenerator()
    
    from database import init_db
    init_db()
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.utcnow().isoformat(),
            'processed_count': pipeline.processed_count
        })
    
    @app.route('/api/dashboard')
    def get_dashboard():
        hours = int(request.args.get('hours', 24))
        
        sentiment_dist = pipeline.get_sentiment_distribution(hours=hours)
        trend_data = pipeline.get_trend_data(hours=hours)
        top_keywords = pipeline.get_top_keywords(hours=hours, top_k=20)
        platform_stats = pipeline.get_platform_stats(hours=hours)
        alerts = pipeline.alert_manager.get_recent_alerts(limit=10)
        alert_summary = pipeline.alert_manager.get_alert_summary(hours=hours)
        
        return jsonify({
            'sentiment_distribution': sentiment_dist,
            'trend_data': trend_data,
            'top_keywords': top_keywords,
            'platform_stats': platform_stats,
            'recent_alerts': alerts,
            'alert_summary': alert_summary
        })
    
    @app.route('/api/sentiment')
    def get_sentiment():
        platform = request.args.get('platform')
        hours = int(request.args.get('hours', 24))
        
        result = pipeline.get_sentiment_distribution(platform=platform, hours=hours)
        return jsonify(result)
    
    @app.route('/api/trends')
    def get_trends():
        platform = request.args.get('platform')
        hours = int(request.args.get('hours', 24))
        
        data = pipeline.get_trend_data(platform=platform, hours=hours)
        return jsonify(data)
    
    @app.route('/api/keywords')
    def get_keywords():
        platform = request.args.get('platform')
        hours = int(request.args.get('hours', 24))
        top_k = int(request.args.get('top_k', 20))
        
        data = pipeline.get_top_keywords(platform=platform, hours=hours, top_k=top_k)
        return jsonify(data)
    
    @app.route('/api/alerts')
    def get_alerts():
        limit = int(request.args.get('limit', 20))
        severity = request.args.get('severity')
        
        alerts = pipeline.alert_manager.get_recent_alerts(limit=limit, severity=severity)
        return jsonify(alerts)
    
    @app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
    def acknowledge_alert(alert_id):
        success = pipeline.alert_manager.acknowledge_alert(alert_id)
        return jsonify({'success': success})
    
    @app.route('/api/alerts/summary')
    def get_alert_summary():
        hours = int(request.args.get('hours', 24))
        summary = pipeline.alert_manager.get_alert_summary(hours=hours)
        return jsonify(summary)
    
    @app.route('/api/analyze', methods=['POST'])
    def analyze_text():
        data = request.get_json()
        text = data.get('text', '')
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        sentiment = pipeline.sentiment_analyzer.analyze(text)
        topics = pipeline.topic_modeler.get_topics(text)
        keywords = pipeline.text_processor.extract_keywords(text, top_k=10)
        
        return jsonify({
            'text': text,
            'sentiment': sentiment,
            'topics': topics,
            'keywords': keywords
        })
    
    @app.route('/api/analyze/batch', methods=['POST'])
    def analyze_batch():
        data = request.get_json()
        texts = data.get('texts', [])
        
        if not texts:
            return jsonify({'error': 'No texts provided'}), 400
        
        results = []
        for text in texts:
            sentiment = pipeline.sentiment_analyzer.analyze(text)
            topics = pipeline.topic_modeler.get_topics(text)
            keywords = pipeline.text_processor.extract_keywords(text, top_k=5)
            results.append({
                'text': text,
                'sentiment': sentiment,
                'topics': topics,
                'keywords': keywords
            })
        
        return jsonify({'results': results, 'count': len(results)})
    
    @app.route('/api/data/generate', methods=['POST'])
    def generate_data():
        data = request.get_json() or {}
        count = data.get('count', 50)
        platform = data.get('platform')
        
        posts = data_generator.generate_batch(count=count)
        
        if platform:
            posts = [p for p in posts if p['platform'] == platform]
        
        results = pipeline.process_batch(posts)
        
        socketio.emit('new_data', {
            'count': len(results),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'generated': len(posts),
            'processed': len(results)
        })
    
    @app.route('/api/data/ingest', methods=['POST'])
    def ingest_data():
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        if isinstance(data, list):
            results = pipeline.process_batch(data)
        else:
            result = pipeline.process_post(data)
            results = [result] if result else []
        
        socketio.emit('new_data', {
            'count': len(results),
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return jsonify({
            'processed': len(results)
        })
    
    @app.route('/api/propagation', methods=['POST'])
    def analyze_propagation():
        data = request.get_json()
        root_post_id = data.get('root_post_id')
        paths = data.get('paths', [])
        
        if not root_post_id or not paths:
            return jsonify({'error': 'Missing root_post_id or paths'}), 400
        
        result = pipeline.analyze_propagation(root_post_id, paths)
        return jsonify(result)
    
    @app.route('/api/topics')
    def get_topics():
        topics = pipeline.topic_modeler.get_all_topics()
        return jsonify(topics)
    
    @app.route('/api/topics/train', methods=['POST'])
    def train_topics():
        data = request.get_json()
        texts = data.get('texts', [])
        
        if len(texts) < 10:
            return jsonify({'error': 'Need at least 10 texts for training'}), 400
        
        success = pipeline.train_topic_model(texts)
        return jsonify({'success': success})
    
    @app.route('/api/stats')
    def get_stats():
        hours = int(request.args.get('hours', 24))
        stats = pipeline.get_platform_stats(hours=hours)
        return jsonify(stats)
    
    @socketio.on('connect')
    def handle_connect():
        logger.info('Client connected')
    
    @socketio.on('disconnect')
    def handle_disconnect():
        logger.info('Client disconnected')
    
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow()
        }
    
    return app
