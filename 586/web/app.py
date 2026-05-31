import os
import json
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory, Response
from config import REPORTS_DIR, TEMPLATES_DIR
from core import TestEngine


test_engine = None
active_tests = {}
test_progress = {}


def create_app():
    app = Flask(
        __name__,
        template_folder=TEMPLATES_DIR,
        static_folder='static'
    )
    
    app.config['SECRET_KEY'] = 'api-fuzzer-secret-key'
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
    
    global test_engine
    if test_engine is None:
        test_engine = TestEngine()
    
    @app.route('/')
    def index():
        return render_template('index.html')
    
    @app.route('/api/test', methods=['POST'])
    def run_test():
        data = request.get_json()
        
        test_type = data.get('test_type', 'single')
        api_config = data.get('api_config')
        workflow_config = data.get('workflow_config')
        test_mode = data.get('test_mode', 'single')
        max_combinations = data.get('max_combinations', 100)
        report_format = data.get('report_format', 'json')
        
        if not api_config and not workflow_config:
            return jsonify({'error': 'Either api_config or workflow_config is required'}), 400
        
        test_id = f"test_{int(time.time() * 1000)}"
        
        def progress_callback(current, total, message):
            test_progress[test_id] = {
                'current': current,
                'total': total,
                'message': message,
                'percent': (current / total * 100) if total > 0 else 0
            }
        
        test_engine.set_progress_callback(progress_callback)
        
        def run_background_test():
            try:
                test_progress[test_id] = {
                    'current': 0,
                    'total': 0,
                    'message': 'Initializing test...',
                    'percent': 0
                }
                
                if test_type == 'workflow' and workflow_config:
                    result = test_engine.run_workflow_test(workflow_config)
                else:
                    result = test_engine.run_test(api_config, test_mode, max_combinations)
                
                json_path = test_engine.save_report(result, 'json')
                if report_format == 'html' or report_format == 'both':
                    test_engine.save_report(result, 'html')
                
                active_tests[test_id] = {
                    'status': 'completed',
                    'result': result.to_dict(),
                    'json_path': json_path,
                    'test_run_id': result.test_run_id
                }
                
                test_progress[test_id] = {
                    'current': result.total_tests,
                    'total': result.total_tests,
                    'message': 'Test completed',
                    'percent': 100
                }
                
            except Exception as e:
                active_tests[test_id] = {
                    'status': 'failed',
                    'error': str(e)
                }
                test_progress[test_id] = {
                    'current': 0,
                    'total': 0,
                    'message': f'Test failed: {str(e)}',
                    'percent': 0
                }
        
        thread = threading.Thread(target=run_background_test, daemon=True)
        thread.start()
        
        return jsonify({
            'test_id': test_id,
            'status': 'running',
            'message': 'Test started successfully'
        })
    
    @app.route('/api/test/<test_id>/progress')
    def get_test_progress(test_id):
        progress = test_progress.get(test_id, {
            'current': 0,
            'total': 0,
            'message': 'Waiting for test to start...',
            'percent': 0
        })
        
        test_info = active_tests.get(test_id)
        if test_info:
            progress['status'] = test_info.get('status', 'running')
        
        return jsonify(progress)
    
    @app.route('/api/test/<test_id>/result')
    def get_test_result(test_id):
        test_info = active_tests.get(test_id)
        
        if not test_info:
            return jsonify({'error': 'Test not found'}), 404
        
        if test_info.get('status') != 'completed':
            return jsonify({
                'status': test_info.get('status', 'running'),
                'message': 'Test not completed yet'
            }), 202
        
        return jsonify(test_info['result'])
    
    @app.route('/api/reports')
    def list_reports():
        reports = test_engine.list_reports()
        return jsonify(reports)
    
    @app.route('/api/reports/<test_run_id>')
    def get_report(test_run_id):
        report = test_engine.load_report(test_run_id)
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        return jsonify(report)
    
    @app.route('/api/reports/<test_run_id>/download')
    def download_report(test_run_id):
        format = request.args.get('format', 'json')
        filename = f"{test_run_id}.{format}"
        filepath = os.path.join(REPORTS_DIR, filename)
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Report not found'}), 404
        
        return send_from_directory(
            REPORTS_DIR,
            filename,
            as_attachment=True,
            download_name=filename
        )
    
    @app.route('/api/reports/<test_run_id>/html')
    def view_html_report(test_run_id):
        filename = f"{test_run_id}.html"
        filepath = os.path.join(REPORTS_DIR, filename)
        
        if not os.path.exists(filepath):
            json_report = test_engine.load_report(test_run_id)
            if not json_report:
                return jsonify({'error': 'Report not found'}), 404
        
        return send_from_directory(REPORTS_DIR, filename)
    
    @app.route('/api/params/generate', methods=['POST'])
    def generate_params():
        data = request.get_json()
        param_name = data.get('param_name', 'param')
        param_type = data.get('param_type', 'string')
        include_edge_cases = data.get('include_edge_cases', True)
        include_injections = data.get('include_injections', True)
        include_type_mismatch = data.get('include_type_mismatch', True)
        injection_types = data.get('injection_types', ['all'])
        max_values = data.get('max_values', 50)
        
        values = test_engine.param_generator.generate_values(
            param_name=param_name,
            param_type=param_type,
            include_edge_cases=include_edge_cases,
            include_injections=include_injections,
            include_type_mismatch=include_type_mismatch,
            injection_types=injection_types,
            max_values=max_values
        )
        
        return jsonify({
            'param_name': param_name,
            'param_type': param_type,
            'total_values': len(values),
            'values': values
        })
    
    @app.route('/api/workflow/validate', methods=['POST'])
    def validate_workflow():
        data = request.get_json()
        workflow_config = data.get('workflow_config', {})
        steps = workflow_config.get('steps', [])
        
        validation = test_engine.dependency_resolver.validate_dependencies(steps)
        
        return jsonify(validation)
    
    @app.route('/api/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'active_tests': len(active_tests)
        })
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app


app = create_app()


if __name__ == '__main__':
    os.makedirs(REPORTS_DIR, exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)
