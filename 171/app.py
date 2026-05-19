import os
import json
import signal
import sys
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify
from config import Config
from log_parser import LogParser
from alert_engine import AlertEngine
from log_replay import LogReplayEngine

app = Flask(__name__)
app.config.from_object(Config)

log_parser = LogParser(app.config)
alert_engine = AlertEngine(app.config, log_parser)
replay_engine = LogReplayEngine(app.config, log_parser)


def signal_handler(signum, frame):
    print("\nShutting down gracefully...")
    alert_engine.stop()
    replay_engine.shutdown()
    log_parser.shutdown()
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)


def parse_datetime_param(param_str):
    if not param_str:
        return None
    try:
        return datetime.strptime(param_str, '%Y-%m-%d %H:%M:%S')
    except ValueError:
        try:
            return datetime.strptime(param_str, '%Y-%m-%d')
        except ValueError:
            return None


@app.before_first_request
def startup():
    log_parser.refresh()
    if app.config['USE_FILE_WATCHER']:
        log_parser.start_watcher()
    if app.config['ENABLE_ALERT_ENGINE']:
        alert_engine.start()


@app.route('/')
def index():
    watcher_active = False
    if app.config['USE_FILE_WATCHER'] and log_parser.file_watcher:
        watcher_active = log_parser.file_watcher.observer is not None
    
    return render_template('index.html', 
                         refresh_interval=app.config['REFRESH_INTERVAL'],
                         slow_threshold=app.config['SLOW_REQUEST_THRESHOLD'],
                         watcher_active=watcher_active,
                         aggregate_slow=app.config['AGGREGATE_SLOW_REQUESTS'],
                         alert_engine_enabled=app.config['ENABLE_ALERT_ENGINE'],
                         log_replay_enabled=app.config['ENABLE_LOG_REPLAY'])


@app.route('/api/overview')
def api_overview():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    
    data = log_parser.get_overview(start_time, end_time, keyword)
    
    recent_alerts = alert_engine.get_alerts(limit=10)
    data['recent_alerts'] = recent_alerts
    data['alert_engine_active'] = alert_engine.enabled and alert_engine._check_thread and alert_engine._check_thread.is_alive()
    
    def serialize(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")
    
    return jsonify(json.loads(json.dumps(data, default=serialize)))


@app.route('/api/refresh')
def api_refresh():
    result = log_parser.refresh()
    recent_alerts = alert_engine.get_alerts(limit=5)
    result['recent_alerts'] = recent_alerts
    return jsonify(result)


@app.route('/api/access_logs')
def api_access_logs():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    
    total = len(filtered)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = filtered[start_idx:end_idx]
    
    def serialize(log):
        result = dict(log)
        result['timestamp'] = log['timestamp'].isoformat()
        return result
    
    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'data': [serialize(log) for log in paginated]
    })


@app.route('/api/error_logs')
def api_error_logs():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.error_logs, start_time, end_time, keyword)
    
    total = len(filtered)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated = filtered[start_idx:end_idx]
    
    def serialize(log):
        result = dict(log)
        result['timestamp'] = log['timestamp'].isoformat()
        return result
    
    return jsonify({
        'total': total,
        'page': page,
        'per_page': per_page,
        'data': [serialize(log) for log in paginated]
    })


@app.route('/api/hourly_stats')
def api_hourly_stats():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    stats = log_parser.get_hourly_stats(filtered)
    
    return jsonify(stats)


@app.route('/api/status_distribution')
def api_status_distribution():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    dist = log_parser.get_status_distribution(filtered)
    
    return jsonify(dist)


@app.route('/api/slow_requests')
def api_slow_requests():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    threshold = float(request.args.get('threshold', app.config['SLOW_REQUEST_THRESHOLD']))
    limit = int(request.args.get('limit', 20))
    aggregate = request.args.get('aggregate', 'true').lower() == 'true'
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    slow = log_parser.get_slow_requests(filtered, threshold, limit, aggregate=aggregate)
    
    return jsonify(slow)


@app.route('/api/geo_distribution')
def api_geo_distribution():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    geo = log_parser.get_geo_distribution(filtered)
    
    return jsonify(geo)


@app.route('/api/top_paths')
def api_top_paths():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    limit = int(request.args.get('limit', 10))
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    paths = log_parser.get_top_paths(filtered, limit)
    
    return jsonify([{'path': p[0], 'count': p[1]} for p in paths])


@app.route('/api/top_ips')
def api_top_ips():
    start_time = parse_datetime_param(request.args.get('start_time'))
    end_time = parse_datetime_param(request.args.get('end_time'))
    keyword = request.args.get('keyword', '').strip() or None
    limit = int(request.args.get('limit', 10))
    
    if not log_parser.file_watcher or not log_parser.file_watcher.observer:
        log_parser.refresh()
    filtered = log_parser.filter_logs(log_parser.access_logs, start_time, end_time, keyword)
    ips = log_parser.get_top_ips(filtered, limit)
    
    return jsonify([{'ip': ip[0], 'count': ip[1]} for ip in ips])


@app.route('/api/alerts/rules', methods=['GET'])
def get_alert_rules():
    rules = alert_engine.get_rules()
    return jsonify(rules)


@app.route('/api/alerts/rules', methods=['POST'])
def add_alert_rule():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
    
    rule = alert_engine.add_rule(data)
    return jsonify(rule), 201


@app.route('/api/alerts/rules/<rule_id>', methods=['GET'])
def get_alert_rule(rule_id):
    rule = alert_engine.get_rule(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify(rule)


@app.route('/api/alerts/rules/<rule_id>', methods=['PUT'])
def update_alert_rule(rule_id):
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid request body'}), 400
    
    rule = alert_engine.update_rule(rule_id, data)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify(rule)


@app.route('/api/alerts/rules/<rule_id>', methods=['DELETE'])
def delete_alert_rule(rule_id):
    success = alert_engine.delete_rule(rule_id)
    if not success:
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify({'success': True})


@app.route('/api/alerts/rules/<rule_id>/toggle', methods=['POST'])
def toggle_alert_rule(rule_id):
    rule = alert_engine.toggle_rule(rule_id)
    if not rule:
        return jsonify({'error': 'Rule not found'}), 404
    return jsonify(rule)


@app.route('/api/alerts/rules/<rule_id>/test', methods=['POST'])
def test_alert_rule(rule_id):
    result = alert_engine.test_rule(rule_id)
    if 'error' in result:
        return jsonify(result), 404
    return jsonify(result)


@app.route('/api/alerts/history', methods=['GET'])
def get_alert_history():
    limit = int(request.args.get('limit', 100))
    alerts = alert_engine.get_alerts(limit)
    return jsonify(alerts)


@app.route('/api/alerts/history', methods=['DELETE'])
def clear_alert_history():
    alert_engine.clear_alerts()
    return jsonify({'success': True})


@app.route('/api/alerts/webhooks', methods=['GET'])
def get_webhooks():
    webhooks = alert_engine.get_global_webhooks()
    return jsonify(webhooks)


@app.route('/api/alerts/webhooks', methods=['POST'])
def add_webhook():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400
    
    success = alert_engine.add_global_webhook(data['url'])
    return jsonify({'success': success, 'url': data['url']})

@app.route('/api/alerts/webhooks', methods=['DELETE'])
def remove_webhook():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400
    
    success = alert_engine.remove_global_webhook(data['url'])
    return jsonify({'success': success})


@app.route('/api/alerts/webhooks/test', methods=['POST'])
def test_webhook():
    data = request.get_json()
    if not data or 'url' not in data:
        return jsonify({'error': 'URL is required'}), 400
    
    success = alert_engine.send_test_webhook(data['url'])
    return jsonify({'success': success})


@app.route('/api/alerts/check', methods=['POST'])
def check_alerts_manual():
    alerts = alert_engine.check_rules()
    return jsonify({'triggered': len(alerts), 'alerts': alerts})


@app.route('/api/replay/ranges', methods=['GET'])
def get_replay_ranges():
    ranges = replay_engine.get_available_time_ranges()
    return jsonify(ranges)


@app.route('/api/replay/sessions', methods=['GET'])
def get_replay_sessions():
    sessions = replay_engine.get_all_sessions()
    return jsonify(sessions)


@app.route('/api/replay/sessions', methods=['POST'])
def create_replay_session():
    data = request.get_json() or {}
    
    start_time = parse_datetime_param(data.get('start_time'))
    end_time = parse_datetime_param(data.get('end_time'))
    keyword = data.get('keyword', '').strip() or None
    speed = float(data.get('speed', app.config['LOG_REPLAY_DEFAULT_SPEED']))
    log_type = data.get('log_type', 'access')
    
    session = replay_engine.create_session(
        start_time=start_time,
        end_time=end_time,
        keyword=keyword,
        speed=speed,
        log_type=log_type
    )
    
    if not session:
        return jsonify({'error': 'No logs found in the specified time range'}), 404
    
    return jsonify(session.to_dict()), 201


@app.route('/api/replay/sessions/<session_id>', methods=['GET'])
def get_replay_session(session_id):
    session = replay_engine.get_session(session_id)
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    return jsonify(session)


@app.route('/api/replay/sessions/<session_id>/start', methods=['POST'])
def start_replay_session(session_id):
    success = replay_engine.start_session(session_id)
    if not success:
        return jsonify({'error': 'Failed to start session'}), 400
    return jsonify({'success': True})


@app.route('/api/replay/sessions/<session_id>/pause', methods=['POST'])
def pause_replay_session(session_id):
    success = replay_engine.pause_session(session_id)
    if not success:
        return jsonify({'error': 'Failed to pause session'}), 400
    return jsonify({'success': True})


@app.route('/api/replay/sessions/<session_id>/resume', methods=['POST'])
def resume_replay_session(session_id):
    success = replay_engine.resume_session(session_id)
    if not success:
        return jsonify({'error': 'Failed to resume session'}), 400
    return jsonify({'success': True})


@app.route('/api/replay/sessions/<session_id>/stop', methods=['POST'])
def stop_replay_session(session_id):
    success = replay_engine.stop_session(session_id)
    if not success:
        return jsonify({'error': 'Failed to stop session'}), 400
    return jsonify({'success': True})


@app.route('/api/replay/sessions/<session_id>/speed', methods=['PUT'])
def set_replay_speed(session_id):
    data = request.get_json()
    if not data or 'speed' not in data:
        return jsonify({'error': 'Speed is required'}), 400
    
    success = replay_engine.set_speed(session_id, float(data['speed']))
    if not success:
        return jsonify({'error': 'Failed to set speed'}), 400
    return jsonify({'success': True})


@app.route('/api/replay/sessions/<session_id>', methods=['DELETE'])
def delete_replay_session(session_id):
    success = replay_engine.delete_session(session_id)
    if not success:
        return jsonify({'error': 'Failed to delete session'}), 404
    return jsonify({'success': True})


if __name__ == '__main__':
    print("Starting Nginx Log Analyzer...")
    print(f"Access log path: {app.config['ACCESS_LOG_PATH']}")
    print(f"Error log path: {app.config['ERROR_LOG_PATH']}")
    print(f"GeoIP database path: {app.config['GEOIP_DB_PATH']}")
    print(f"Alert engine enabled: {app.config['ENABLE_ALERT_ENGINE']}")
    print(f"Log replay enabled: {app.config['ENABLE_LOG_REPLAY']}")
    app.run(host='0.0.0.0', port=5000, debug=True)
