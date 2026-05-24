import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from deadlock_parser import MySQLDeadlockParser, PostgreSQLDeadlockParser, Deadlock
from deadlock_analyzer import (
    DeadlockAnalyzer, DeadlockGraphGenerator, OptimizationAdvisor,
    ExplainAnalyzer, DeadlockMonitor, DeadlockSimulator, APMIntegration
)
import json
from datetime import datetime, timedelta
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

mysql_parser = MySQLDeadlockParser()
pg_parser = PostgreSQLDeadlockParser()
analyzer = DeadlockAnalyzer()
graph_generator = DeadlockGraphGenerator()
optimizer = OptimizationAdvisor()
explain_analyzer_mysql = ExplainAnalyzer(db_type='mysql')
explain_analyzer_pg = ExplainAnalyzer(db_type='postgresql')
monitor = DeadlockMonitor(check_interval=5.0)
simulator = DeadlockSimulator()
apm_integration = APMIntegration(apm_type='mock')

_parsed_deadlocks_cache = None
_parsed_log_content = None
_parsed_db_type = None
_monitor_lock = threading.Lock()


def alert_callback(alert):
    print(f"[ALERT] {alert.level.upper()}: {alert.title}")
    if alert.level == 'critical':
        try:
            correlations = apm_integration.correlate_deadlock_with_traces(
                _parsed_deadlocks_cache[0] if _parsed_deadlocks_cache else None
            )
            if correlations:
                apm_integration.send_deadlock_alert(
                    _parsed_deadlocks_cache[0] if _parsed_deadlocks_cache else None,
                    correlations
                )
        except Exception as e:
            print(f"APM回调出错: {e}")


monitor.alert_callback = alert_callback


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/parse', methods=['POST'])
def parse_log():
    global _parsed_deadlocks_cache, _parsed_log_content, _parsed_db_type

    try:
        db_type = request.form.get('db_type', 'mysql')
        log_content = request.form.get('log_content', '')

        if not log_content and 'log_file' in request.files:
            file = request.files['log_file']
            if file.filename:
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    log_content = f.read()

        if not log_content.strip():
            return jsonify({'error': '请提供死锁日志内容或上传日志文件'}), 400

        if db_type == 'mysql':
            parser = mysql_parser
            explain_analyzer = explain_analyzer_mysql
        elif db_type == 'postgresql':
            parser = pg_parser
            explain_analyzer = explain_analyzer_pg
        else:
            return jsonify({'error': '不支持的数据库类型'}), 400

        deadlocks = parser.parse(log_content)
        detected_version = getattr(parser, 'get_detected_version', lambda: 'unknown')()

        _parsed_deadlocks_cache = deadlocks
        _parsed_log_content = log_content
        _parsed_db_type = db_type

        if not deadlocks:
            return jsonify({
                'success': True,
                'message': '未检测到死锁',
                'deadlocks': [],
                'statistics': {},
                'suggestions': [],
                'graph': {'elements': []},
                'graph_stats': {},
                'detected_version': detected_version
            })

        statistics = analyzer.analyze(deadlocks)
        graph = graph_generator.generate_graph(deadlocks)

        all_sqls = []
        for d in deadlocks:
            for txn in d.transactions:
                all_sqls.extend(txn.sql_statements)

        explain_results = explain_analyzer.analyze_multiple(all_sqls)
        index_recommendations = explain_analyzer.get_all_recommendations(explain_results)

        suggestions = optimizer.analyze(deadlocks, statistics)

        graph_data = graph_generator.to_cytoscape_json(graph)
        graph_stats = graph_generator.get_graph_statistics(graph)
        cycles = graph_generator.detect_cycles_with_details(graph)

        return jsonify({
            'success': True,
            'message': f'成功解析 {len(deadlocks)} 个死锁',
            'deadlocks': [d.to_dict() for d in deadlocks],
            'statistics': statistics.to_dict(),
            'suggestions': [s.to_dict() for s in suggestions],
            'graph': graph_data,
            'graph_stats': graph_stats,
            'cycles': cycles,
            'detected_version': detected_version,
            'index_recommendations': [
                {
                    'table_name': rec.table_name,
                    'index_columns': rec.index_columns,
                    'index_name': rec.index_name,
                    'reason': rec.reason,
                    'estimated_benefit': rec.estimated_benefit,
                    'create_statement': rec.create_statement,
                    'sql_sample': rec.sql_sample
                }
                for rec in index_recommendations
            ],
            'explain_analysis': [
                {
                    'sql': r.sql[:100],
                    'table_name': r.table_name,
                    'has_index': r.has_index,
                    'has_full_table_scan': r.has_full_table_scan,
                    'type': r.type,
                    'rows_expected': r.rows_expected,
                    'warnings': r.warnings,
                    'has_filesort': r.has_filesort,
                    'has_temporary': r.has_temporary
                }
                for r in explain_results[:20]
            ]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'解析失败: {str(e)}'}), 500


@app.route('/api/graph/<int:deadlock_index>', methods=['GET'])
def get_single_deadlock_graph(deadlock_index):
    try:
        db_type = request.args.get('db_type', 'mysql')
        log_content = request.args.get('log_content', '')

        if not log_content and _parsed_log_content:
            log_content = _parsed_log_content
            db_type = _parsed_db_type or 'mysql'

        if not log_content:
            return jsonify({'error': '缺少日志内容'}), 400

        if db_type == 'mysql':
            parser = mysql_parser
        elif db_type == 'postgresql':
            parser = pg_parser
        else:
            return jsonify({'error': '不支持的数据库类型'}), 400

        deadlocks = parser.parse(log_content)

        if deadlock_index >= len(deadlocks):
            return jsonify({'error': '死锁索引超出范围'}), 400

        single_deadlock = deadlocks[deadlock_index:deadlock_index + 1]
        graph = graph_generator.generate_graph(single_deadlock)
        graph_data = graph_generator.to_cytoscape_json(graph)
        graph_stats = graph_generator.get_graph_statistics(graph)
        cycles = graph_generator.detect_cycles_with_details(graph)

        return jsonify({
            'success': True,
            'deadlock': single_deadlock[0].to_dict(),
            'graph': graph_data,
            'graph_stats': graph_stats,
            'cycles': cycles
        })

    except Exception as e:
        return jsonify({'error': f'生成图失败: {str(e)}'}), 500


@app.route('/api/sample/<string:db_type>')
def get_sample_log(db_type):
    try:
        sample_dir = os.path.join(os.path.dirname(__file__), 'sample_logs')
        if db_type == 'mysql':
            filepath = os.path.join(sample_dir, 'mysql_sample.log')
        elif db_type == 'postgresql':
            filepath = os.path.join(sample_dir, 'postgresql_sample.log')
        else:
            return jsonify({'error': '不支持的数据库类型'}), 400

        if not os.path.exists(filepath):
            return jsonify({'error': '示例文件不存在'}), 404

        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        return jsonify({'success': True, 'content': content})

    except Exception as e:
        return jsonify({'error': f'读取示例失败: {str(e)}'}), 500


@app.route('/api/monitor/start', methods=['POST'])
def start_monitor():
    try:
        data = request.get_json() or {}
        db_type = data.get('db_type', 'mysql')
        db_config = data.get('db_config', {})

        if db_config:
            monitor.configure_database(
                db_type=db_type,
                host=db_config.get('host', 'localhost'),
                port=db_config.get('port', 3306 if db_type == 'mysql' else 5432),
                user=db_config.get('user', 'root'),
                password=db_config.get('password', ''),
                database=db_config.get('database', '')
            )

        with _monitor_lock:
            if not monitor.get_status().is_running:
                monitor.start()
                return jsonify({
                    'success': True,
                    'message': '实时监控已启动',
                    'status': monitor.get_status().to_dict()
                })
            else:
                return jsonify({
                    'success': True,
                    'message': '监控已经在运行',
                    'status': monitor.get_status().to_dict()
                })

    except Exception as e:
        return jsonify({'error': f'启动监控失败: {str(e)}'}), 500


@app.route('/api/monitor/stop', methods=['POST'])
def stop_monitor():
    try:
        with _monitor_lock:
            if monitor.get_status().is_running:
                monitor.stop()
                return jsonify({
                    'success': True,
                    'message': '实时监控已停止',
                    'status': monitor.get_status().to_dict()
                })
            else:
                return jsonify({
                    'success': True,
                    'message': '监控未运行',
                    'status': monitor.get_status().to_dict()
                })

    except Exception as e:
        return jsonify({'error': f'停止监控失败: {str(e)}'}), 500


@app.route('/api/monitor/status', methods=['GET'])
def get_monitor_status():
    try:
        status = monitor.get_status()
        return jsonify({
            'success': True,
            'status': status.to_dict()
        })
    except Exception as e:
        return jsonify({'error': f'获取状态失败: {str(e)}'}), 500


@app.route('/api/monitor/check', methods=['POST'])
def check_monitor_now():
    try:
        status = monitor.check_now()
        alerts = monitor.get_current_alerts(limit=50)
        lock_waits = monitor.get_current_lock_waits()

        wait_graph = monitor.get_wait_graph()
        graph_data = {
            'nodes': [{'id': n, **wait_graph.nodes[n]} for n in wait_graph.nodes()],
            'edges': [{'from': e[0], 'to': e[1], **wait_graph.edges[e]} for e in wait_graph.edges()]
        }

        return jsonify({
            'success': True,
            'status': status.to_dict(),
            'alerts': [a.to_dict() for a in alerts],
            'lock_waits': [
                {
                    'waiting_txn_id': w.waiting_txn_id,
                    'holding_txn_id': w.holding_txn_id,
                    'lock_type': w.lock_type,
                    'lock_mode': w.lock_mode,
                    'table_name': w.table_name,
                    'wait_duration': round(w.wait_duration, 2),
                    'index_name': w.index_name
                }
                for w in lock_waits
            ],
            'wait_graph': graph_data
        })
    except Exception as e:
        return jsonify({'error': f'检查失败: {str(e)}'}), 500


@app.route('/api/monitor/alerts', methods=['GET'])
def get_monitor_alerts():
    try:
        level = request.args.get('level')
        limit = int(request.args.get('limit', 100))
        alerts = monitor.get_current_alerts(level=level, limit=limit)

        return jsonify({
            'success': True,
            'alerts': [a.to_dict() for a in alerts]
        })
    except Exception as e:
        return jsonify({'error': f'获取告警失败: {str(e)}'}), 500


@app.route('/api/monitor/alerts/clear', methods=['POST'])
def clear_monitor_alerts():
    try:
        monitor.clear_alerts()
        return jsonify({
            'success': True,
            'message': '告警已清除'
        })
    except Exception as e:
        return jsonify({'error': f'清除告警失败: {str(e)}'}), 500


@app.route('/api/simulate/<int:deadlock_index>', methods=['POST'])
def simulate_deadlock(deadlock_index):
    try:
        data = request.get_json() or {}
        custom_order = data.get('custom_order')

        if _parsed_deadlocks_cache is None or deadlock_index >= len(_parsed_deadlocks_cache):
            return jsonify({'error': '请先解析死锁日志'}), 400

        deadlock = _parsed_deadlocks_cache[deadlock_index]

        if custom_order:
            result = simulator.simulate_deadlock(deadlock, custom_order=custom_order)
        else:
            result = simulator.simulate_deadlock(deadlock)

        order_tests = simulator.test_multiple_orders(deadlock)

        return jsonify({
            'success': True,
            'simulation_result': result.to_dict(),
            'order_tests': order_tests,
            'original_steps': [
                {
                    'step_number': s.step_number,
                    'time': s.time,
                    'description': s.description,
                    'is_deadlock': s.is_deadlock,
                    'operations': [
                        {
                            'txn_id': op.txn_id,
                            'operation_type': op.operation_type,
                            'table_name': op.table_name,
                            'lock_mode': op.lock_mode,
                            'is_waiting': op.is_waiting
                        }
                        for op in s.operations
                    ]
                }
                for s in result.original_steps
            ],
            'optimized_steps': [
                {
                    'step_number': s.step_number,
                    'time': s.time,
                    'description': s.description,
                    'is_deadlock': s.is_deadlock,
                    'operations': [
                        {
                            'txn_id': op.txn_id,
                            'operation_type': op.operation_type,
                            'table_name': op.table_name,
                            'lock_mode': op.lock_mode,
                            'is_waiting': op.is_waiting
                        }
                        for op in s.operations
                    ]
                }
                for s in result.optimized_steps
            ]
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'模拟失败: {str(e)}'}), 500


@app.route('/api/explain/analyze', methods=['POST'])
def analyze_explain():
    try:
        data = request.get_json() or {}
        sql = data.get('sql', '')
        explain_output = data.get('explain_output')
        db_type = data.get('db_type', 'mysql')

        if not sql:
            return jsonify({'error': '请提供SQL语句'}), 400

        if db_type == 'mysql':
            analyzer = explain_analyzer_mysql
        else:
            analyzer = explain_analyzer_pg

        result = analyzer.analyze_sql(sql, explain_output)

        return jsonify({
            'success': True,
            'analysis': {
                'sql': result.sql,
                'table_name': result.table_name,
                'has_index': result.has_index,
                'used_index': result.used_index,
                'type': result.type,
                'rows_examined': result.rows_examined,
                'rows_expected': result.rows_expected,
                'extra': result.extra,
                'has_full_table_scan': result.has_full_table_scan,
                'has_filesort': result.has_filesort,
                'has_temporary': result.has_temporary,
                'warnings': result.warnings,
                'recommendations': [
                    {
                        'table_name': rec.table_name,
                        'index_columns': rec.index_columns,
                        'index_name': rec.index_name,
                        'reason': rec.reason,
                        'estimated_benefit': rec.estimated_benefit,
                        'create_statement': rec.create_statement
                    }
                    for rec in result.recommendations
                ]
            }
        })

    except Exception as e:
        return jsonify({'error': f'EXPLAIN分析失败: {str(e)}'}), 500


@app.route('/api/apm/configure', methods=['POST'])
def configure_apm():
    global apm_integration
    try:
        data = request.get_json() or {}
        apm_type = data.get('apm_type', 'mock')
        config = data.get('config', {})

        apm_integration = APMIntegration(
            apm_type=apm_type,
            base_url=config.get('base_url', ''),
            api_key=config.get('api_key', ''),
            service_name=config.get('service_name', '')
        )

        return jsonify({
            'success': True,
            'message': f'APM已配置为 {apm_type}'
        })
    except Exception as e:
        return jsonify({'error': f'配置APM失败: {str(e)}'}), 500


@app.route('/api/apm/correlate/<int:deadlock_index>', methods=['GET'])
def correlate_apm(deadlock_index):
    try:
        if _parsed_deadlocks_cache is None or deadlock_index >= len(_parsed_deadlocks_cache):
            return jsonify({'error': '请先解析死锁日志'}), 400

        deadlock = _parsed_deadlocks_cache[deadlock_index]
        time_window_before = int(request.args.get('before', 60))
        time_window_after = int(request.args.get('after', 10))

        correlations = apm_integration.correlate_deadlock_with_traces(
            deadlock,
            time_window_before=time_window_before,
            time_window_after=time_window_after
        )

        trace_links = apm_integration.generate_trace_links(correlations)

        return jsonify({
            'success': True,
            'correlations': [c.to_dict() for c in correlations],
            'trace_links': trace_links
        })

    except Exception as e:
        return jsonify({'error': f'APM关联失败: {str(e)}'}), 500


@app.route('/api/apm/trace/<string:trace_id>', methods=['GET'])
def get_apm_trace(trace_id):
    try:
        trace_info = apm_integration.query_trace_detail(trace_id)
        if trace_info:
            return jsonify({
                'success': True,
                'trace': trace_info.to_dict()
            })
        else:
            return jsonify({'error': '未找到trace'}), 404
    except Exception as e:
        return jsonify({'error': f'获取trace失败: {str(e)}'}), 500


@app.route('/api/apm/traces', methods=['GET'])
def get_apm_traces():
    try:
        start_time_str = request.args.get('start_time')
        end_time_str = request.args.get('end_time')
        service_name = request.args.get('service_name')

        now = datetime.now()
        if start_time_str:
            start_time = datetime.fromisoformat(start_time_str)
        else:
            start_time = now - timedelta(hours=1)

        if end_time_str:
            end_time = datetime.fromisoformat(end_time_str)
        else:
            end_time = now

        traces = apm_integration.query_traces(start_time, end_time, service_name)

        return jsonify({
            'success': True,
            'traces': [t.to_dict() for t in traces[:50]]
        })

    except Exception as e:
        return jsonify({'error': f'查询traces失败: {str(e)}'}), 500


@app.route('/api/version/detect', methods=['POST'])
def detect_version():
    try:
        data = request.get_json() or {}
        log_content = data.get('log_content', '')
        db_type = data.get('db_type', 'mysql')

        if not log_content:
            return jsonify({'error': '请提供日志内容'}), 400

        if db_type == 'mysql':
            parser = MySQLDeadlockParser()
        else:
            parser = PostgreSQLDeadlockParser()

        parser.parse(log_content)
        detected_version = getattr(parser, 'get_detected_version', lambda: 'unknown')()

        return jsonify({
            'success': True,
            'detected_version': detected_version,
            'db_type': db_type
        })

    except Exception as e:
        return jsonify({'error': f'版本检测失败: {str(e)}'}), 500


@app.route('/static/<path:path>')
def send_static(path):
    return send_from_directory('static', path)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
