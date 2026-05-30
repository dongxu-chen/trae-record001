from flask import Blueprint, jsonify, request
from app.slowlog_analyzer import SlowLogAnalyzer
from app.optimizer import OptimizationAdvisor
from app.monitor import RealTimeMonitor
from app.predictor import SlowLogPredictor
from app.audit_logger import AuditLogger

api_bp = Blueprint('api', __name__)

slowlog_analyzer = SlowLogAnalyzer()
optimizer = OptimizationAdvisor()
monitor = RealTimeMonitor()
predictor = SlowLogPredictor()
audit_logger = AuditLogger()


@api_bp.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'message': 'Redis Slow Query Analyzer API is running'})


@api_bp.route('/slowlogs', methods=['GET'])
def get_slow_logs():
    count = request.args.get('count', 100, type=int)
    logs = slowlog_analyzer.get_slow_logs(count)
    return jsonify({
        'success': True,
        'data': logs,
        'total': len(logs)
    })


@api_bp.route('/slowlogs/config', methods=['GET'])
def get_slowlog_config():
    config = slowlog_analyzer.get_slow_log_config()
    return jsonify({
        'success': True,
        'data': config
    })


@api_bp.route('/analysis/commands', methods=['GET'])
def get_command_analysis():
    count = request.args.get('count', 1000, type=int)
    normalize = request.args.get('normalize', 'true').lower() == 'true'
    logs = slowlog_analyzer.get_slow_logs(count)
    patterns = slowlog_analyzer.analyze_command_patterns(logs, normalize=normalize)
    return jsonify({
        'success': True,
        'data': patterns,
        'total_commands': len(patterns),
        'normalized': normalize
    })


@api_bp.route('/analysis/hotkeys', methods=['GET'])
def get_hot_keys():
    count = request.args.get('count', 1000, type=int)
    top_n = request.args.get('top_n', 20, type=int)
    logs = slowlog_analyzer.get_slow_logs(count)
    hot_keys = slowlog_analyzer.find_hot_keys(logs, top_n)
    return jsonify({
        'success': True,
        'data': hot_keys
    })


@api_bp.route('/analysis/largekeys', methods=['GET'])
def get_large_keys():
    size_threshold = request.args.get('size_threshold', 10240, type=int)
    element_threshold = request.args.get('element_threshold', None, type=int)
    use_composite_score = request.args.get('composite', 'true').lower() == 'true'
    large_keys = slowlog_analyzer.find_large_keys(
        size_threshold=size_threshold,
        element_threshold=element_threshold,
        use_composite_score=use_composite_score
    )
    return jsonify({
        'success': True,
        'data': large_keys,
        'use_composite_score': use_composite_score
    })


@api_bp.route('/analysis/ranking', methods=['GET'])
def get_slow_queries_ranking():
    count = request.args.get('count', 1000, type=int)
    top_n = request.args.get('top_n', 20, type=int)
    sort_by = request.args.get('sort_by', 'duration', type=str)
    
    logs = slowlog_analyzer.get_slow_logs(count)
    ranking = slowlog_analyzer.get_slow_queries_ranking(logs, top_n, sort_by)
    
    return jsonify({
        'success': True,
        'data': ranking
    })


@api_bp.route('/optimizations', methods=['GET'])
def get_optimizations():
    count = request.args.get('count', 1000, type=int)
    size_threshold = request.args.get('size_threshold', 10240, type=int)
    element_threshold = request.args.get('element_threshold', None, type=int)
    use_composite_score = request.args.get('composite', 'true').lower() == 'true'
    normalize = request.args.get('normalize', 'true').lower() == 'true'
    
    logs = slowlog_analyzer.get_slow_logs(count)
    command_patterns = slowlog_analyzer.analyze_command_patterns(logs, normalize=normalize)
    hot_keys = slowlog_analyzer.find_hot_keys(logs)
    large_keys = slowlog_analyzer.find_large_keys(
        size_threshold=size_threshold,
        element_threshold=element_threshold,
        use_composite_score=use_composite_score
    )
    
    suggestions = optimizer.generate_optimization_suggestions(
        command_patterns, hot_keys, large_keys)
    
    return jsonify({
        'success': True,
        'data': suggestions
    })


@api_bp.route('/monitor/metrics', methods=['GET'])
def get_monitor_metrics():
    metrics = monitor.get_instant_metrics()
    return jsonify({
        'success': True,
        'data': metrics
    })


@api_bp.route('/monitor/history', methods=['GET'])
def get_monitor_history():
    count = request.args.get('count', None, type=int)
    history = monitor.get_raw_metrics_history(count)
    return jsonify({
        'success': True,
        'data': history
    })


@api_bp.route('/monitor/aggregated', methods=['GET'])
def get_aggregated_metrics():
    count = request.args.get('count', None, type=int)
    if count is None:
        latest = monitor.get_latest_aggregated()
        if latest is None:
            latest = monitor.get_instant_metrics()
        return jsonify({
            'success': True,
            'data': latest
        })
    else:
        history = monitor.get_aggregated_metrics(count)
        return jsonify({
            'success': True,
            'data': history
        })


@api_bp.route('/monitor/stream/start', methods=['POST'])
def start_stream():
    stream_interval_ms = request.json.get('stream_interval_ms', 100) if request.json else 100
    aggregate_interval_ms = request.json.get('aggregate_interval_ms', 1000) if request.json else 1000
    monitor.start_streaming(stream_interval_ms, aggregate_interval_ms)
    return jsonify({
        'success': True,
        'message': f'Streaming started with {stream_interval_ms}ms raw interval, {aggregate_interval_ms}ms aggregate interval',
        'stream_interval_ms': stream_interval_ms,
        'aggregate_interval_ms': aggregate_interval_ms
    })


@api_bp.route('/monitor/stream/stop', methods=['POST'])
def stop_stream():
    monitor.stop_streaming()
    return jsonify({
        'success': True,
        'message': 'Streaming stopped'
    })


@api_bp.route('/monitor/start', methods=['POST'])
def start_monitor():
    interval = request.json.get('interval', 1) if request.json else 1
    stream_interval_ms = int(interval * 1000)
    monitor.start_streaming(stream_interval_ms, 1000)
    return jsonify({
        'success': True,
        'message': f'Monitoring started with interval {interval}s',
        'stream_interval_ms': stream_interval_ms
    })


@api_bp.route('/monitor/stop', methods=['POST'])
def stop_monitor():
    monitor.stop_streaming()
    return jsonify({
        'success': True,
        'message': 'Monitoring stopped'
    })


@api_bp.route('/monitor/stream/slowlogs', methods=['GET'])
def get_stream_slowlogs():
    logs = monitor.get_new_slowlogs()
    return jsonify({
        'success': True,
        'data': logs,
        'count': len(logs)
    })


@api_bp.route('/monitor/slowlogs/new', methods=['GET'])
def get_new_slowlogs():
    last_id = request.args.get('last_id', -1, type=int)
    new_logs = monitor.check_slowlog_new_entries(last_id)
    return jsonify({
        'success': True,
        'data': new_logs
    })


@api_bp.route('/monitor/databases', methods=['GET'])
def get_database_stats():
    stats = monitor.get_database_stats()
    return jsonify({
        'success': True,
        'data': stats
    })


@api_bp.route('/monitor/commands', methods=['GET'])
def get_command_stats():
    stats = monitor.get_command_stats()
    return jsonify({
        'success': True,
        'data': stats
    })


@api_bp.route('/full', methods=['GET'])
def get_full_analysis():
    log_count = request.args.get('log_count', 1000, type=int)
    size_threshold = request.args.get('size_threshold', 10240, type=int)
    
    slow_logs = slowlog_analyzer.get_slow_logs(log_count)
    command_patterns = slowlog_analyzer.analyze_command_patterns(slow_logs)
    hot_keys = slowlog_analyzer.find_hot_keys(slow_logs)
    large_keys = slowlog_analyzer.find_large_keys(size_threshold=size_threshold)
    slowlog_config = slowlog_analyzer.get_slow_log_config()
    
    optimizations = optimizer.generate_optimization_suggestions(
        command_patterns, hot_keys, large_keys)
    
    metrics = monitor.get_instant_metrics()
    db_stats = monitor.get_database_stats()
    
    return jsonify({
        'success': True,
        'data': {
            'slow_logs': slow_logs[:50],
            'command_patterns': command_patterns,
            'hot_keys': hot_keys,
            'large_keys': large_keys,
            'slowlog_config': slowlog_config,
            'optimizations': optimizations,
            'metrics': metrics,
            'database_stats': db_stats,
            'summary': {
                'total_slow_logs': len(slow_logs),
                'total_commands': len(command_patterns),
                'hot_keys_count': len(hot_keys),
                'large_keys_count': len(large_keys)
            }
        }
    })


@api_bp.route('/prediction/trend', methods=['GET'])
def get_prediction_trend():
    hours_ahead = request.args.get('hours_ahead', 24, type=int)
    hours = request.args.get('hours', 24, type=int)
    
    predictor.collect_historical_data(hours)
    prediction = predictor.predict_slowlog_trend(hours_ahead)
    
    return jsonify({
        'success': True,
        'data': prediction
    })


@api_bp.route('/prediction/hot-commands', methods=['GET'])
def get_prediction_hot_commands():
    top_n = request.args.get('top_n', 10, type=int)
    hours = request.args.get('hours', 24, type=int)
    
    predictor.collect_historical_data(hours)
    hot_commands = predictor.predict_hot_commands(top_n)
    
    return jsonify({
        'success': True,
        'data': hot_commands
    })


@api_bp.route('/prediction/risk', methods=['GET'])
def get_prediction_risk():
    hours = request.args.get('hours', 24, type=int)
    
    predictor.collect_historical_data(hours)
    risk = predictor.get_risk_assessment()
    
    return jsonify({
        'success': True,
        'data': risk
    })


@api_bp.route('/prediction/summary', methods=['GET'])
def get_prediction_summary():
    hours = request.args.get('hours', 24, type=int)
    
    predictor.collect_historical_data(hours)
    summary = predictor.get_prediction_summary()
    
    return jsonify({
        'success': True,
        'data': summary
    })


@api_bp.route('/optimizations/auto-commands', methods=['GET'])
def get_auto_optimization_commands():
    log_count = request.args.get('log_count', 1000, type=int)
    size_threshold = request.args.get('size_threshold', 10240, type=int)
    element_threshold = request.args.get('element_threshold', None, type=int)
    use_composite_score = request.args.get('composite', 'true').lower() == 'true'
    
    logs = slowlog_analyzer.get_slow_logs(log_count)
    hot_keys = slowlog_analyzer.find_hot_keys(logs)
    large_keys = slowlog_analyzer.find_large_keys(
        size_threshold=size_threshold,
        element_threshold=element_threshold,
        use_composite_score=use_composite_score
    )
    
    commands = optimizer.generate_auto_optimization_commands(large_keys, hot_keys)
    
    return jsonify({
        'success': True,
        'data': commands
    })


@api_bp.route('/optimizations/scripts', methods=['GET'])
def get_optimization_scripts():
    script_type = request.args.get('type', 'all', type=str)
    scripts = optimizer.get_executable_scripts(script_type)
    
    return jsonify({
        'success': True,
        'data': scripts
    })


@api_bp.route('/audit/logs', methods=['GET'])
def get_audit_logs():
    action_type = request.args.get('action_type', None, type=str)
    status = request.args.get('status', None, type=str)
    limit = request.args.get('limit', 100, type=int)
    
    logs = audit_logger.get_audit_logs(action_type, status, limit)
    
    return jsonify({
        'success': True,
        'data': logs,
        'total': len(logs)
    })


@api_bp.route('/audit/statistics', methods=['GET'])
def get_audit_statistics():
    stats = audit_logger.get_statistics()
    
    return jsonify({
        'success': True,
        'data': stats
    })


@api_bp.route('/audit/pending', methods=['GET'])
def get_pending_optimizations():
    pending = audit_logger.get_pending_optimizations()
    
    return jsonify({
        'success': True,
        'data': pending,
        'count': len(pending)
    })


@api_bp.route('/audit/log', methods=['POST'])
def create_audit_log():
    data = request.json or {}
    
    action_type = data.get('action_type', 'manual')
    target_key = data.get('target_key', '')
    description = data.get('description', '')
    status = data.get('status', 'pending')
    metadata = data.get('metadata', {})
    
    entry = audit_logger.log_optimization_action(
        action_type, target_key, description, status, metadata
    )
    
    return jsonify({
        'success': True,
        'data': entry
    })


@api_bp.route('/audit/log/<int:entry_id>/execute', methods=['POST'])
def execute_audit_log(entry_id):
    data = request.json or {}
    result = data.get('result', 'Action executed')
    
    entry = audit_logger.mark_as_executed(entry_id, result)
    
    if entry:
        return jsonify({
            'success': True,
            'data': entry
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Entry not found'
        }), 404


@api_bp.route('/audit/log/<int:entry_id>/fail', methods=['POST'])
def fail_audit_log(entry_id):
    data = request.json or {}
    error_message = data.get('error_message', 'Action failed')
    
    entry = audit_logger.mark_as_failed(entry_id, error_message)
    
    if entry:
        return jsonify({
            'success': True,
            'data': entry
        })
    else:
        return jsonify({
            'success': False,
            'message': 'Entry not found'
        }), 404


@api_bp.route('/audit/clear', methods=['POST'])
def clear_audit_logs():
    data = request.json or {}
    days = data.get('days', 30, type=int)
    
    deleted_count = audit_logger.clear_old_logs(days)
    
    return jsonify({
        'success': True,
        'deleted_count': deleted_count
    })

