from flask import Flask, jsonify, request
from prometheus_client import generate_latest, Gauge, CONTENT_TYPE_LATEST
import pandas as pd
import yaml
import os
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cloud_collector import MockCollector
from analyzers import (
    ResourceAnalyzer, IdleResourceDetector, CostOptimizer,
    SpotInstanceAnalyzer, ResourcePacker, MultiCloudComparer
)
from database import DatabaseManager
from webhook_manager import WebhookEventType

app = Flask(__name__)

cloud_cost_current_monthly = Gauge('cloud_cost_current_monthly', 'Current monthly cloud cost')
cloud_cost_optimized_monthly = Gauge('cloud_cost_optimized_monthly', 'Optimized monthly cloud cost')
cloud_cost_savings_monthly = Gauge('cloud_cost_savings_monthly', 'Monthly savings')
cloud_savings_percentage = Gauge('cloud_savings_percentage', 'Savings percentage')
cloud_optimization_candidates = Gauge('cloud_optimization_candidates', 'Number of optimization candidates')
cloud_cpu_utilization = Gauge('cloud_cpu_utilization', 'CPU utilization by instance', ['instance'])
cloud_memory_utilization = Gauge('cloud_memory_utilization', 'Memory utilization by instance', ['instance'])
cloud_cpu_p99 = Gauge('cloud_cpu_p99', 'P99 CPU utilization by instance', ['instance'])
cloud_periodic_instances = Gauge('cloud_periodic_instances', 'Number of instances with periodic patterns')
cloud_buffer_required = Gauge('cloud_buffer_required', 'Number of instances requiring buffer')
cloud_spot_candidates = Gauge('cloud_spot_candidates', 'Number of spot instance candidates')
cloud_spot_savings = Gauge('cloud_spot_savings', 'Potential savings from spot instances')
cloud_packing_savings = Gauge('cloud_packing_savings', 'Potential savings from resource packing')
cloud_migration_savings = Gauge('cloud_migration_savings', 'Potential savings from cloud migration')

current_data = {}


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def run_analysis():
    config = load_config()
    collector = MockCollector(config['cloud_providers']['aliyun'])
    
    resources = collector.collect_all_resources()
    ecs_df = resources['ecs']
    eip_df = resources['eip']
    
    instance_ids = ecs_df['instance_id'].tolist()
    metrics_df = collector.collect_metrics_for_instances(instance_ids, days=7)
    
    analyzer = ResourceAnalyzer(config)
    idle_detector = IdleResourceDetector(config)
    cost_optimizer = CostOptimizer(config)
    spot_analyzer = SpotInstanceAnalyzer(config)
    resource_packer = ResourcePacker(config)
    cloud_comparer = MultiCloudComparer(config)
    
    idle_resources = idle_detector.detect_all_idle_resources(ecs_df, metrics_df, eip_df)
    analysis_df = idle_resources['utilization_analysis']
    
    spot_df = spot_analyzer.analyze_spot_candidates(analysis_df, metrics_df)
    spot_summary = spot_analyzer.get_spot_summary(spot_df)
    
    packing_results = resource_packer.optimize_by_family(ecs_df, analysis_df)
    packing_summary = resource_packer.get_packing_summary(packing_results)
    
    workload_types = dict(zip(
        spot_df['instance_id'],
        spot_df['workload_type']
    )) if not spot_df.empty else {}
    
    migration_results = cloud_comparer.analyze_portfolio(
        ecs_df, analysis_df, workload_types
    )
    
    current_cost = cost_optimizer.calculate_current_monthly_cost(ecs_df, eip_df)
    optimization_plan = cost_optimizer.generate_optimization_plan(idle_resources, analysis_df)
    cost_comparison = cost_optimizer.calculate_cost_comparison(current_cost, optimization_plan)
    
    global current_data
    current_data = {
        'ecs_df': ecs_df,
        'eip_df': eip_df,
        'metrics_df': metrics_df,
        'analysis_df': analysis_df,
        'idle_resources': idle_resources,
        'current_cost': current_cost,
        'optimization_plan': optimization_plan,
        'cost_comparison': cost_comparison,
        'spot_df': spot_df,
        'spot_summary': spot_summary,
        'packing_results': packing_results,
        'packing_summary': packing_summary,
        'migration_results': migration_results
    }
    
    update_metrics()
    
    return current_data


def get_db_manager():
    config = load_config()
    webhook_config = config.get('webhooks', {})
    db = DatabaseManager(webhook_config=webhook_config)
    
    def execute_optimization(request_id):
        return db.execute_request(request_id, 'success')
    
    db.set_execute_callback(execute_optimization)
    return db


def update_metrics():
    if 'cost_comparison' in current_data:
        cc = current_data['cost_comparison']
        cloud_cost_current_monthly.set(cc['current_monthly_cost'])
        cloud_cost_optimized_monthly.set(cc['optimized_monthly_cost'])
        cloud_cost_savings_monthly.set(cc['monthly_savings'])
        cloud_savings_percentage.set(cc['savings_percentage'])
    
    if 'optimization_plan' in current_data:
        cloud_optimization_candidates.set(current_data['optimization_plan']['optimization_count'])
    
    if 'analysis_df' in current_data:
        df = current_data['analysis_df']
        periodic_count = 0
        buffer_count = 0
        
        for _, row in df.iterrows():
            instance_name = row.get('instance_name', row['instance_id'])
            cloud_cpu_utilization.labels(instance=instance_name).set(row['cpu_avg'])
            cloud_memory_utilization.labels(instance=instance_name).set(row['memory_avg'])
            cloud_cpu_p99.labels(instance=instance_name).set(row.get('cpu_p99', 0))
            
            if row.get('is_periodic', False):
                periodic_count += 1
            if row.get('needs_buffer', False):
                buffer_count += 1
        
        cloud_periodic_instances.set(periodic_count)
        cloud_buffer_required.set(buffer_count)
    
    if 'spot_summary' in current_data:
        ss = current_data['spot_summary']
        cloud_spot_candidates.set(ss.get('recommended_count', 0))
        cloud_spot_savings.set(ss.get('total_monthly_savings', 0))
    
    if 'packing_summary' in current_data:
        ps = current_data['packing_summary']
        cloud_packing_savings.set(ps.get('total_monthly_savings', 0))
    
    if 'migration_results' in current_data:
        mr = current_data['migration_results']
        cloud_migration_savings.set(mr.get('total_monthly_savings', 0))


@app.route('/metrics')
def metrics():
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}


@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'timestamp': datetime.now().isoformat()})


@app.route('/api/analysis')
def get_analysis():
    if not current_data:
        run_analysis()
    
    return jsonify({
        'cost_comparison': current_data.get('cost_comparison', {}),
        'optimization_count': current_data.get('optimization_plan', {}).get('optimization_count', 0),
        'total_savings': current_data.get('optimization_plan', {}).get('total_monthly_savings', 0)
    })


@app.route('/api/resources/ecs')
def get_ecs_resources():
    if not current_data:
        run_analysis()
    
    ecs_df = current_data.get('analysis_df', pd.DataFrame())
    return jsonify(ecs_df.to_dict('records'))


@app.route('/api/resources/eip')
def get_eip_resources():
    if not current_data:
        run_analysis()
    
    eip_df = current_data.get('eip_df', pd.DataFrame())
    return jsonify(eip_df.to_dict('records'))


@app.route('/api/idle-resources')
def get_idle_resources():
    if not current_data:
        run_analysis()
    
    idle_res = current_data.get('idle_resources', {})
    return jsonify({
        'idle_ecs': idle_res.get('idle_ecs', pd.DataFrame()).to_dict('records'),
        'stopped_ecs': idle_res.get('stopped_ecs', pd.DataFrame()).to_dict('records'),
        'unused_eips': idle_res.get('unused_eips', pd.DataFrame()).to_dict('records')
    })


@app.route('/api/optimization-plan')
def get_optimization_plan():
    if not current_data:
        run_analysis()
    
    opt_plan = current_data.get('optimization_plan', {})
    return jsonify({
        'all_recommendations': opt_plan.get('all_recommendations', pd.DataFrame()).to_dict('records'),
        'total_monthly_savings': opt_plan.get('total_monthly_savings', 0),
        'total_annual_savings': opt_plan.get('total_annual_savings', 0),
        'optimization_count': opt_plan.get('optimization_count', 0)
    })


@app.route('/api/requests', methods=['GET'])
def get_requests():
    db = get_db_manager()
    status = request.args.get('status')
    requests_df = db.get_requests_dataframe(status)
    db.close()
    return jsonify(requests_df.to_dict('records'))


@app.route('/api/requests', methods=['POST'])
def create_requests():
    if not current_data:
        run_analysis()
    
    db = get_db_manager()
    opt_plan = current_data.get('optimization_plan', {})
    all_recs = opt_plan.get('all_recommendations', pd.DataFrame())
    
    if not all_recs.empty:
        request_ids = db.batch_create_requests(all_recs)
        db.close()
        return jsonify({'request_ids': request_ids, 'count': len(request_ids)})
    
    db.close()
    return jsonify({'message': 'No recommendations found'})


@app.route('/api/requests/<request_id>/approve', methods=['POST'])
def approve_request(request_id):
    data = request.json or {}
    approver = data.get('approver', 'api-user')
    auto_execute = data.get('auto_execute', None)
    
    db = get_db_manager()
    success = db.approve_request(request_id, approver, auto_execute)
    db.close()
    
    if success:
        return jsonify({'status': 'approved', 'request_id': request_id, 'auto_execute': auto_execute})
    return jsonify({'error': 'Failed to approve request'}), 400


@app.route('/api/requests/<request_id>/reject', methods=['POST'])
def reject_request(request_id):
    data = request.json or {}
    approver = data.get('approver', 'api-user')
    reason = data.get('reason', '')
    
    db = get_db_manager()
    success = db.reject_request(request_id, approver, reason)
    db.close()
    
    if success:
        return jsonify({'status': 'rejected', 'request_id': request_id})
    return jsonify({'error': 'Failed to reject request'}), 400


@app.route('/api/requests/auto-approve', methods=['POST'])
def auto_approve():
    data = request.json or {}
    threshold = data.get('threshold', 100)
    auto_execute = data.get('auto_execute', None)
    
    db = get_db_manager()
    pending = db.get_all_requests(status='pending')
    count = 0
    
    for req in pending:
        if req.monthly_savings < threshold:
            if db.approve_request(req.request_id, 'auto-approve', auto_execute):
                count += 1
    
    db.close()
    return jsonify({'auto_approved': count, 'threshold': threshold})


@app.route('/api/refresh', methods=['POST'])
def refresh_data():
    run_analysis()
    return jsonify({'status': 'refreshed', 'timestamp': datetime.now().isoformat()})


@app.route('/api/requests/<request_id>/execute', methods=['POST'])
def execute_request(request_id):
    db = get_db_manager()
    success = db.execute_request(request_id, 'success')
    db.close()
    
    if success:
        return jsonify({'status': 'executed', 'request_id': request_id})
    return jsonify({'error': 'Failed to execute request'}), 400


@app.route('/api/webhooks', methods=['GET'])
def list_webhooks():
    config = load_config()
    webhooks = config.get('webhooks', {}).get('endpoints', [])
    return jsonify({'webhooks': webhooks})


@app.route('/api/webhooks', methods=['POST'])
def add_webhook():
    data = request.json or {}
    url = data.get('url')
    events = data.get('events')
    secret = data.get('secret')
    method = data.get('method', 'POST')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    db = get_db_manager()
    webhook = db.add_webhook(url, events, secret, method)
    db.close()
    
    return jsonify({'status': 'added', 'webhook': webhook})


@app.route('/api/webhooks/test', methods=['POST'])
def test_webhook():
    data = request.json or {}
    url = data.get('url')
    method = data.get('method', 'POST')
    
    if not url:
        return jsonify({'error': 'URL is required'}), 400
    
    db = get_db_manager()
    result = db.test_webhook(url, method)
    db.close()
    
    return jsonify(result)


@app.route('/api/periodicity-analysis', methods=['GET'])
def get_periodicity_analysis():
    if not current_data:
        run_analysis()
    
    analysis_df = current_data.get('analysis_df', pd.DataFrame())
    if analysis_df.empty:
        return jsonify({'periodic_instances': [], 'buffer_instances': []})
    
    periodic = analysis_df[analysis_df.get('is_periodic', False)].to_dict('records')
    buffer = analysis_df[analysis_df.get('needs_buffer', False)].to_dict('records')
    
    return jsonify({
        'periodic_instances': periodic,
        'buffer_instances': buffer,
        'periodic_count': len(periodic),
        'buffer_count': len(buffer)
    })


@app.route('/api/optimization-plan')
def get_optimization_plan():
    if not current_data:
        run_analysis()
    
    opt_plan = current_data.get('optimization_plan', {})
    buffer_recs = opt_plan.get('buffer_recommendations', pd.DataFrame())
    
    return jsonify({
        'all_recommendations': opt_plan.get('all_recommendations', pd.DataFrame()).to_dict('records'),
        'buffer_recommendations': buffer_recs.to_dict('records') if not buffer_recs.empty else [],
        'excluded_due_to_periodicity': opt_plan.get('excluded_due_to_periodicity', []),
        'total_monthly_savings': opt_plan.get('total_monthly_savings', 0),
        'total_annual_savings': opt_plan.get('total_annual_savings', 0),
        'optimization_count': opt_plan.get('optimization_count', 0),
        'buffer_aware_count': opt_plan.get('buffer_aware_count', 0)
    })


@app.route('/api/spot-instances')
def get_spot_instance_analysis():
    if not current_data:
        run_analysis()
    
    spot_df = current_data.get('spot_df', pd.DataFrame())
    spot_summary = current_data.get('spot_summary', {})
    
    return jsonify({
        'candidates': spot_df.to_dict('records') if not spot_df.empty else [],
        'summary': spot_summary
    })


@app.route('/api/resource-packing')
def get_resource_packing():
    if not current_data:
        run_analysis()
    
    packing_results = current_data.get('packing_results', {})
    packing_summary = current_data.get('packing_summary', {})
    
    return jsonify({
        'recommendations': packing_results.get('recommendations', []),
        'summary': packing_summary,
        'by_provider': packing_results.get('by_provider', {})
    })


@app.route('/api/multi-cloud-comparison')
def get_multi_cloud_comparison():
    if not current_data:
        run_analysis()
    
    migration_results = current_data.get('migration_results', {})
    recommendations = migration_results.get('recommendations', pd.DataFrame())
    best_options = migration_results.get('best_migration_options', pd.DataFrame())
    
    return jsonify({
        'migration_candidates': recommendations.to_dict('records') if not recommendations.empty else [],
        'best_options': best_options.to_dict('records') if not best_options.empty else [],
        'provider_summary': migration_results.get('provider_summary', {}),
        'total_candidates': migration_results.get('migration_candidate_count', 0),
        'total_monthly_savings': migration_results.get('total_monthly_savings', 0),
        'total_net_savings': migration_results.get('total_net_savings', 0)
    })


@app.route('/api/migration-plan/<provider>')
def get_migration_plan(provider):
    if not current_data:
        run_analysis()
    
    migration_results = current_data.get('migration_results', {})
    
    config = load_config()
    cloud_comparer = MultiCloudComparer(config)
    plan = cloud_comparer.get_migration_plan(migration_results, provider)
    
    return jsonify(plan)


@app.route('/api/comprehensive-optimization')
def get_comprehensive_optimization():
    if not current_data:
        run_analysis()
    
    cost_comp = current_data.get('cost_comparison', {})
    spot_summary = current_data.get('spot_summary', {})
    packing_summary = current_data.get('packing_summary', {})
    migration_results = current_data.get('migration_results', {})
    
    total_savings = (
        cost_comp.get('monthly_savings', 0) +
        spot_summary.get('total_monthly_savings', 0) +
        packing_summary.get('total_monthly_savings', 0) +
        migration_results.get('total_monthly_savings', 0)
    )
    
    current_cost = cost_comp.get('current_monthly_cost', 1)
    
    return jsonify({
        'current_monthly_cost': current_cost,
        'optimization_breakdown': {
            'idle_resource_release': cost_comp.get('monthly_savings', 0),
            'spot_instances': spot_summary.get('total_monthly_savings', 0),
            'resource_packing': packing_summary.get('total_monthly_savings', 0),
            'cloud_migration': migration_results.get('total_monthly_savings', 0)
        },
        'total_potential_savings': total_savings,
        'savings_percentage': round((total_savings / current_cost * 100) if current_cost > 0 else 0, 1),
        'optimization_candidates': {
            'idle_resources': current_data.get('optimization_plan', {}).get('optimization_count', 0),
            'spot_candidates': spot_summary.get('recommended_count', 0),
            'packing_bins': packing_summary.get('total_bins', 0),
            'migration_candidates': migration_results.get('migration_candidate_count', 0)
        }
    })


if __name__ == '__main__':
    run_analysis()
    app.run(host='0.0.0.0', port=5000, debug=True)
