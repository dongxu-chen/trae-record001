import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS

from db_connector import DBConnector
from sql_parser import parse_sql, format_sql, validate_syntax
from slow_query_capture import SlowQueryCapture
from explain_analyzer import ExplainAnalyzer
from query_optimizer import QueryOptimizer
from trend_analyzer import TrendAnalyzer
from sql_clusterer import SQLFingerprintClusterer
from cost_calibrator import CostModelCalibrator
from index_validator import IndexValidator

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

db_connector = DBConnector()
slow_query_capture = SlowQueryCapture()
explain_analyzer = ExplainAnalyzer()
query_optimizer = QueryOptimizer()
trend_analyzer = TrendAnalyzer()
sql_clusterer = SQLFingerprintClusterer()
cost_calibrator = CostModelCalibrator()
index_validator = IndexValidator()


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/config', methods=['GET'])
def get_config():
    return jsonify(db_connector.get_config())


@app.route('/api/config', methods=['POST'])
def save_config():
    data = request.get_json()
    host = data.get('host', '127.0.0.1')
    port = int(data.get('port', 3306))
    user = data.get('user', 'root')
    password = data.get('password', '')
    database = data.get('database', '')
    db_connector.save_config(host, port, user, password, database)
    return jsonify({'success': True, 'message': '配置已保存'})


@app.route('/api/test_connection', methods=['POST'])
def test_connection():
    data = request.get_json()
    host = data.get('host', '127.0.0.1')
    port = int(data.get('port', 3306))
    user = data.get('user', 'root')
    password = data.get('password', '')
    database = data.get('database', '')
    success, message = db_connector.test_connection(host, port, user, password, database)
    return jsonify({'success': success, 'message': message})


@app.route('/api/execute', methods=['POST'])
def execute_query():
    data = request.get_json()
    sql = data.get('sql', '')
    timeout = data.get('timeout', 30)
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    result = db_connector.execute_query(sql, timeout=timeout)
    return jsonify(result)


@app.route('/api/explain', methods=['POST'])
def explain_query():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    result = db_connector.execute_explain(sql)
    if result['success']:
        analysis = explain_analyzer.analyze(result['data'], sql)
        return jsonify({
            'success': True,
            'explain_data': result['data'],
            'analysis': analysis
        })
    return jsonify(result)


@app.route('/api/parse_sql', methods=['POST'])
def parse_sql_route():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    analysis = parse_sql(sql)
    formatted = format_sql(sql)
    valid, msg = validate_syntax(sql)
    return jsonify({
        'success': True,
        'analysis': analysis,
        'formatted': formatted,
        'valid': valid,
        'validation_message': msg
    })


@app.route('/api/format_sql', methods=['POST'])
def format_sql_route():
    data = request.get_json()
    sql = data.get('sql', '')
    formatted = format_sql(sql)
    return jsonify({'success': True, 'formatted': formatted})


@app.route('/api/validate_sql', methods=['POST'])
def validate_sql_route():
    data = request.get_json()
    sql = data.get('sql', '')
    valid, msg = validate_syntax(sql)
    return jsonify({'success': True, 'valid': valid, 'message': msg})


@app.route('/api/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    sql_analysis = parse_sql(sql)
    explain_result = db_connector.execute_explain(sql)
    explain_analysis = None
    if explain_result['success']:
        explain_analysis = explain_analyzer.analyze(explain_result['data'], sql)
    optimization = query_optimizer.get_optimization_report(sql, explain_analysis)
    return jsonify({
        'success': True,
        'sql_analysis': sql_analysis,
        'explain_analysis': explain_analysis,
        'explain_data': explain_result.get('data', []),
        'optimization': optimization
    })


@app.route('/api/optimize', methods=['POST'])
def optimize():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    optimization = query_optimizer.get_optimization_report(sql)
    return jsonify({'success': True, 'optimization': optimization})


@app.route('/api/suggest_indexes', methods=['POST'])
def suggest_indexes():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    suggestions = query_optimizer.suggest_indexes(sql)
    return jsonify({'success': True, 'index_suggestions': suggestions})


@app.route('/api/rewrite', methods=['POST'])
def rewrite():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    result = query_optimizer.rewrite_query(sql)
    return jsonify({'success': True, 'rewrite': result})


@app.route('/api/transforms', methods=['POST'])
def get_transforms():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    transforms = query_optimizer.generate_equivalent_transforms(sql)
    cost_estimate = query_optimizer.estimate_cost(sql)
    return jsonify({
        'success': True,
        'transforms': transforms,
        'cost_estimate': cost_estimate
    })


@app.route('/api/estimate_cost', methods=['POST'])
def estimate_cost():
    data = request.get_json()
    sql = data.get('sql', '')
    if not sql.strip():
        return jsonify({'success': False, 'error': 'SQL语句不能为空'})
    result = query_optimizer.estimate_cost(sql)
    return jsonify({'success': True, 'cost_estimate': result})


@app.route('/api/slow_queries/capture', methods=['POST'])
def capture_slow_queries():
    data = request.get_json() or {}
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    min_query_time = float(data.get('min_query_time', 1.0))
    limit = int(data.get('limit', 100))
    result = slow_query_capture.capture_slow_queries(start_time, end_time, min_query_time, limit)
    return jsonify(result)


@app.route('/api/slow_queries/history', methods=['GET'])
def get_slow_query_history():
    history = slow_query_capture.get_history()
    stats = slow_query_capture.get_history_stats()
    return jsonify({
        'success': True,
        'history': history,
        'stats': stats
    })


@app.route('/api/slow_queries/grouped', methods=['GET'])
def get_grouped_slow_queries():
    history = slow_query_capture.get_history()
    grouped = slow_query_capture.group_similar_queries(history)
    return jsonify({'success': True, 'grouped': grouped})


@app.route('/api/slow_queries/top', methods=['GET'])
def get_top_slow_queries():
    limit = int(request.args.get('limit', 20))
    top = slow_query_capture.get_top_slow_queries(limit)
    return jsonify({'success': True, 'top_queries': top})


@app.route('/api/slow_log/enable', methods=['POST'])
def enable_slow_log():
    data = request.get_json() or {}
    long_query_time = float(data.get('long_query_time', 1))
    result = db_connector.enable_slow_log(long_query_time)
    return jsonify(result)


@app.route('/api/slow_log/disable', methods=['POST'])
def disable_slow_log():
    result = db_connector.disable_slow_log()
    return jsonify(result)


@app.route('/api/slow_log/status', methods=['GET'])
def slow_log_status():
    result = db_connector.get_slow_log_status()
    return jsonify(result)


@app.route('/api/trends', methods=['GET'])
def get_trends():
    days = int(request.args.get('days', 7))
    granularity = request.args.get('granularity', 'day')
    trends = trend_analyzer.analyze_trends(days, granularity)
    return jsonify(trends)


@app.route('/api/trends/chart_data', methods=['GET'])
def get_trend_chart_data():
    days = int(request.args.get('days', 7))
    granularity = request.args.get('granularity', 'day')
    chart_data = trend_analyzer.get_trend_chart_data(days, granularity)
    return jsonify(chart_data)


@app.route('/api/trends/multi_granularity', methods=['GET'])
def get_multi_granularity_data():
    days = int(request.args.get('days', 7))
    data = trend_analyzer.get_multi_granularity_data(days)
    return jsonify({'success': True, 'data': data})


@app.route('/api/trends/report', methods=['GET'])
def get_trend_report():
    days = int(request.args.get('days', 7))
    granularity = request.args.get('granularity', 'day')
    report = trend_analyzer.export_trend_report(days, granularity)
    return jsonify(report)


@app.route('/api/tables', methods=['GET'])
def get_tables():
    result = db_connector.get_tables()
    return jsonify(result)


@app.route('/api/table/<table_name>/indexes', methods=['GET'])
def get_table_indexes(table_name):
    result = db_connector.get_table_indexes(table_name)
    return jsonify(result)


@app.route('/api/table/<table_name>/columns', methods=['GET'])
def get_table_columns(table_name):
    result = db_connector.get_table_columns(table_name)
    return jsonify(result)


@app.route('/api/table/<table_name>/status', methods=['GET'])
def get_table_status(table_name):
    result = db_connector.get_table_status(table_name)
    return jsonify(result)


@app.route('/api/database/size', methods=['GET'])
def get_database_size():
    result = db_connector.get_database_size()
    return jsonify(result)


@app.route('/api/database/top_tables', methods=['GET'])
def get_top_large_tables():
    limit = int(request.args.get('limit', 20))
    result = db_connector.get_top_large_tables(limit)
    return jsonify(result)


@app.route('/api/processlist', methods=['GET'])
def get_processlist():
    result = db_connector.get_processlist()
    return jsonify(result)


@app.route('/api/health', methods=['GET'])
def health_check():
    db_status = 'disconnected'
    try:
        success, msg = db_connector.test_connection()
        if success:
            db_status = 'connected'
        else:
            db_status = f'error: {msg}'
    except Exception as e:
        db_status = f'error: {str(e)}'
    return jsonify({
        'status': 'ok',
        'database': db_status,
        'timestamp': datetime.now().isoformat()
    })


@app.route('/api/cluster/queries', methods=['POST'])
def cluster_queries():
    data = request.get_json()
    queries = data.get('queries', [])
    threshold = float(data.get('threshold', 0.85))
    method = data.get('method', 'fingerprint')
    if method == 'advanced':
        clusters = sql_clusterer.advanced_cluster_queries(queries)
    else:
        clusters = sql_clusterer.cluster_queries(queries, threshold)
    return jsonify({'success': True, 'clusters': clusters, 'method': method})


@app.route('/api/cluster/patterns', methods=['POST'])
def extract_patterns():
    data = request.get_json()
    queries = data.get('queries', [])
    patterns = sql_clusterer.extract_patterns(queries)
    return jsonify({'success': True, 'patterns': patterns})


@app.route('/api/cluster/fingerprint', methods=['POST'])
def get_fingerprint():
    data = request.get_json()
    sql = data.get('sql', '')
    version = data.get('version', 'v1')
    if version == 'v2':
        fp = sql_clusterer.get_fingerprint_v2(sql)
    else:
        fp = sql_clusterer.get_fingerprint_v1(sql)
    return jsonify({
        'success': True,
        'fingerprint': fp,
        'hash': sql_clusterer.hash_fingerprint(fp),
        'structural': sql_clusterer.get_structural_fingerprint(sql)
    })


@app.route('/api/cluster/similar', methods=['POST'])
def find_similar():
    data = request.get_json()
    target_sql = data.get('target_sql', '')
    queries = data.get('queries', [])
    threshold = float(data.get('threshold', 0.7))
    similar = sql_clusterer.find_similar_queries(target_sql, queries, threshold)
    return jsonify({'success': True, 'similar_queries': similar})


@app.route('/api/calibrate/accuracy', methods=['GET'])
def get_calibration_accuracy():
    report = cost_calibrator.get_accuracy_report()
    return jsonify(report)


@app.route('/api/calibrate/calibrate', methods=['POST'])
def perform_calibration():
    data = request.get_json()
    queries = data.get('queries', [])
    cost_estimates = data.get('cost_estimates', [])
    training_data = cost_calibrator.collect_training_data(queries, cost_estimates)
    result = cost_calibrator.calibrate(training_data)
    return jsonify(result)


@app.route('/api/calibrate/compare', methods=['POST'])
def compare_estimates():
    data = request.get_json()
    sql_list = data.get('sql_list', [])
    queries = data.get('queries', [])
    comparisons = cost_calibrator.compare_estimated_actual(sql_list, queries)
    summary = cost_calibrator.analyze_deviation_patterns(comparisons)
    return jsonify({
        'success': True,
        'comparisons': comparisons,
        'summary': summary
    })


@app.route('/api/calibrate/reset', methods=['POST'])
def reset_calibration():
    result = cost_calibrator.reset_calibration()
    return jsonify(result)


@app.route('/api/index/suggest', methods=['POST'])
def api_suggest_indexes():
    data = request.get_json()
    sql = data.get('sql', '')
    suggestions = index_validator.suggest_indexes_for_query(sql)
    return jsonify({'success': True, 'suggestions': suggestions})


@app.route('/api/index/create', methods=['POST'])
def create_index():
    data = request.get_json()
    table = data.get('table', '')
    columns = data.get('columns', [])
    index_name = data.get('index_name')
    index_type = data.get('index_type', 'INDEX')
    result = index_validator.create_index(table, columns, index_name, index_type)
    return jsonify(result)


@app.route('/api/index/drop', methods=['POST'])
def drop_index():
    data = request.get_json()
    table = data.get('table', '')
    index_name = data.get('index_name', '')
    result = index_validator.drop_index(table, index_name)
    return jsonify(result)


@app.route('/api/index/validate', methods=['POST'])
def validate_index():
    data = request.get_json()
    sql = data.get('sql', '')
    table = data.get('table', '')
    columns = data.get('columns', [])
    auto_cleanup = data.get('auto_cleanup', True)
    result = index_validator.validate_index_improvement(sql, table, columns)
    if auto_cleanup and result.get('index_created', {}).get('created'):
        index_validator.drop_index(table, result['index_created']['index_name'])
        result['index_cleaned'] = True
    return jsonify(result)


@app.route('/api/index/auto_validate', methods=['POST'])
def auto_validate_indexes():
    data = request.get_json()
    sql = data.get('sql', '')
    auto_cleanup = data.get('auto_cleanup', True)
    result = index_validator.auto_validate_indexes(sql, auto_cleanup)
    return jsonify(result)


@app.route('/api/index/existing/<table_name>', methods=['GET'])
def get_existing_indexes(table_name):
    indexes = index_validator.get_existing_indexes(table_name)
    return jsonify({'success': True, 'indexes': indexes})


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)