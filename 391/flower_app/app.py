from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_cors import CORS
from models.task_model import (
    get_db_session, DAGDefinition, TaskDefinition, TaskDependency,
    TaskExecutionLog, DeadLetterQueue, TaskRerunRecord,
    WorkerNode, ResourceAllocation, TaskLineage, ImpactAnalysis, SchedulingDecision,
)
from datetime import datetime, timedelta
import os
import json

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'task-scheduler-secret-key')


@app.route('/')
def index():
    session = get_db_session()
    try:
        dags = session.query(DAGDefinition).filter_by(enabled=True).all()
        dag_list = []
        for dag in dags:
            task_count = session.query(TaskDependency).filter_by(dag_id=dag.dag_id).count()
            recent_runs = session.query(TaskExecutionLog).filter_by(
                dag_id=dag.dag_id
            ).order_by(TaskExecutionLog.execution_date.desc()).limit(5).all()
            dag_list.append({
                'dag_id': dag.dag_id,
                'dag_name': dag.dag_name,
                'schedule_interval': dag.schedule_interval,
                'task_count': task_count,
                'recent_runs': recent_runs,
            })
        return render_template('index.html', dags=dag_list)
    finally:
        session.close()


@app.route('/logs')
def logs():
    session = get_db_session()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        dag_id = request.args.get('dag_id', '')
        task_id = request.args.get('task_id', '')
        status = request.args.get('status', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')

        query = session.query(TaskExecutionLog)
        if dag_id:
            query = query.filter_by(dag_id=dag_id)
        if task_id:
            query = query.filter_by(task_id=task_id)
        if status:
            query = query.filter_by(status=status)
        if date_from:
            query = query.filter(TaskExecutionLog.execution_date >= date_from)
        if date_to:
            query = query.filter(TaskExecutionLog.execution_date <= date_to)

        total = query.count()
        logs_data = query.order_by(TaskExecutionLog.execution_date.desc()
                                   ).offset((page - 1) * per_page).limit(per_page).all()

        dags = session.query(DAGDefinition).filter_by(enabled=True).all()
        tasks = session.query(TaskDefinition).filter_by(enabled=True).all()

        return render_template('logs.html',
                               logs=logs_data,
                               total=total,
                               page=page,
                               per_page=per_page,
                               total_pages=(total + per_page - 1) // per_page,
                               dags=dags,
                               tasks=tasks,
                               filter_dag_id=dag_id,
                               filter_task_id=task_id,
                               filter_status=status)
    finally:
        session.close()


@app.route('/log/<int:log_id>')
def log_detail(log_id):
    session = get_db_session()
    try:
        log = session.query(TaskExecutionLog).filter_by(log_id=log_id).first()
        reruns = session.query(TaskRerunRecord).filter_by(
            original_log_id=log_id
        ).order_by(TaskRerunRecord.triggered_at.desc()).all()
        return render_template('log_detail.html', log=log, reruns=reruns)
    finally:
        session.close()


@app.route('/dead-letter')
def dead_letter():
    session = get_db_session()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', 'PENDING')
        dag_id = request.args.get('dag_id', '')

        query = session.query(DeadLetterQueue)
        if status:
            query = query.filter_by(status=status)
        if dag_id:
            query = query.filter_by(dag_id=dag_id)

        total = query.count()
        dlq_data = query.order_by(DeadLetterQueue.dead_lettered_at.desc()
                                  ).offset((page - 1) * per_page).limit(per_page).all()

        return render_template('dead_letter.html',
                               dlq_entries=dlq_data,
                               total=total,
                               page=page,
                               per_page=per_page,
                               total_pages=(total + per_page - 1) // per_page,
                               filter_status=status,
                               filter_dag_id=dag_id)
    finally:
        session.close()


@app.route('/dead-letter/<int:dlq_id>')
def dead_letter_detail(dlq_id):
    session = get_db_session()
    try:
        entry = session.query(DeadLetterQueue).filter_by(dlq_id=dlq_id).first()
        return render_template('dead_letter_detail.html', entry=entry)
    finally:
        session.close()


@app.route('/api/dag/<dag_id>')
def api_dag_detail(dag_id):
    session = get_db_session()
    try:
        dag = session.query(DAGDefinition).filter_by(dag_id=dag_id).first()
        if not dag:
            return jsonify({'error': 'DAG not found'}), 404

        dependencies = session.query(TaskDependency).filter_by(dag_id=dag_id).all()
        task_ids = set()
        for dep in dependencies:
            task_ids.add(dep.upstream_task_id)
            task_ids.add(dep.downstream_task_id)

        task_defs = session.query(TaskDefinition).filter(
            TaskDefinition.task_id.in_(task_ids)
        ).all()

        task_map = {t.task_id: {
            'task_id': t.task_id,
            'task_name': t.task_name,
            'queue': t.queue,
            'max_retries': t.max_retries,
        } for t in task_defs}

        edges = [{'from': dep.upstream_task_id, 'to': dep.downstream_task_id}
                 for dep in dependencies]

        return jsonify({
            'dag': {
                'dag_id': dag.dag_id,
                'dag_name': dag.dag_name,
                'description': dag.description,
                'schedule_interval': dag.schedule_interval,
                'owner': dag.owner,
            },
            'tasks': list(task_map.values()),
            'edges': edges,
        })
    finally:
        session.close()


@app.route('/api/dags')
def api_dags():
    session = get_db_session()
    try:
        dags = session.query(DAGDefinition).filter_by(enabled=True).all()
        result = []
        for dag in dags:
            dep_count = session.query(TaskDependency).filter_by(dag_id=dag.dag_id).count()
            success_count = session.query(TaskExecutionLog).filter_by(
                dag_id=dag.dag_id, status='SUCCESS'
            ).count()
            fail_count = session.query(TaskExecutionLog).filter_by(
                dag_id=dag.dag_id, status='FAILURE'
            ).count()
            result.append({
                'dag_id': dag.dag_id,
                'dag_name': dag.dag_name,
                'schedule_interval': dag.schedule_interval,
                'task_count': dep_count,
                'success_count': success_count,
                'failure_count': fail_count,
            })
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/logs')
def api_logs():
    session = get_db_session()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        dag_id = request.args.get('dag_id', '')
        task_id = request.args.get('task_id', '')
        status = request.args.get('status', '')

        query = session.query(TaskExecutionLog)
        if dag_id:
            query = query.filter_by(dag_id=dag_id)
        if task_id:
            query = query.filter_by(task_id=task_id)
        if status:
            query = query.filter_by(status=status)

        total = query.count()
        logs_data = query.order_by(TaskExecutionLog.execution_date.desc()
                                   ).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            'total': total,
            'page': page,
            'per_page': per_page,
            'logs': [{
                'log_id': l.log_id,
                'dag_id': l.dag_id,
                'task_id': l.task_id,
                'run_id': l.run_id,
                'celery_task_id': l.celery_task_id,
                'execution_date': l.execution_date.isoformat() if l.execution_date else None,
                'duration_sec': l.duration_sec,
                'status': l.status,
                'attempt': l.attempt,
                'worker_name': l.worker_name,
                'error_message': l.error_message,
            } for l in logs_data],
        })
    finally:
        session.close()


@app.route('/api/dead-letter')
def api_dead_letter():
    session = get_db_session()
    try:
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        status = request.args.get('status', 'PENDING')

        query = session.query(DeadLetterQueue)
        if status:
            query = query.filter_by(status=status)

        total = query.count()
        entries = query.order_by(DeadLetterQueue.dead_lettered_at.desc()
                                 ).offset((page - 1) * per_page).limit(per_page).all()

        return jsonify({
            'total': total,
            'page': page,
            'per_page': per_page,
            'entries': [{
                'dlq_id': e.dlq_id,
                'celery_task_id': e.celery_task_id,
                'dag_id': e.dag_id,
                'task_id': e.task_id,
                'run_id': e.run_id,
                'error_message': e.error_message,
                'total_retries': e.total_retries,
                'dead_lettered_at': e.dead_lettered_at.isoformat() if e.dead_lettered_at else None,
                'status': e.status,
            } for e in entries],
        })
    finally:
        session.close()


@app.route('/api/rerun', methods=['POST'])
def api_rerun():
    from scripts.rerun import rerun_task
    data = request.get_json()
    log_id = data.get('log_id')
    triggered_by = data.get('triggered_by', 'system')

    if not log_id:
        return jsonify({'error': 'log_id is required'}), 400

    task = rerun_task.delay(log_id=log_id, triggered_by=triggered_by)
    return jsonify({
        'status': 'submitted',
        'log_id': log_id,
        'rerun_celery_id': task.id,
    })


@app.route('/api/dead-letter/reprocess/<int:dlq_id>', methods=['POST'])
def api_dlq_reprocess(dlq_id):
    from celery_app.tasks.dead_letter import process_dead_letter
    data = request.get_json() or {}
    triggered_by = data.get('triggered_by', 'system')

    task = process_dead_letter.delay(dlq_id=dlq_id, triggered_by=triggered_by)
    return jsonify({
        'status': 'submitted',
        'dlq_id': dlq_id,
        'rerun_celery_id': task.id,
    })


@app.route('/api/dead-letter/discard/<int:dlq_id>', methods=['POST'])
def api_dlq_discard(dlq_id):
    from celery_app.tasks.dead_letter import discard_dead_letter
    data = request.get_json() or {}
    reason = data.get('reason', '')

    task = discard_dead_letter.delay(dlq_id=dlq_id, reason=reason)
    return jsonify({
        'status': 'submitted',
        'dlq_id': dlq_id,
        'rerun_celery_id': task.id,
    })


@app.route('/api/statistics')
def api_statistics():
    session = get_db_session()
    try:
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        total_tasks = session.query(TaskDefinition).filter_by(enabled=True).count()
        total_dags = session.query(DAGDefinition).filter_by(enabled=True).count()
        total_logs = session.query(TaskExecutionLog).count()
        success_today = session.query(TaskExecutionLog).filter(
            TaskExecutionLog.status == 'SUCCESS',
            TaskExecutionLog.execution_date >= day_ago
        ).count()
        failure_today = session.query(TaskExecutionLog).filter(
            TaskExecutionLog.status == 'FAILURE',
            TaskExecutionLog.execution_date >= day_ago
        ).count()
        dlq_pending = session.query(DeadLetterQueue).filter_by(status='PENDING').count()
        running_now = session.query(TaskExecutionLog).filter_by(status='RUNNING').count()

        new_deps_pending = session.query(TaskDependency).filter_by(is_detected=False).count()
        dlq_expiring_soon = session.query(DeadLetterQueue).filter(
            DeadLetterQueue.status == 'PENDING',
            DeadLetterQueue.expires_at != None,
            DeadLetterQueue.expires_at < now + timedelta(hours=24)
        ).count()

        online_workers = session.query(WorkerNode).filter_by(status='ONLINE').count()
        avg_cpu = session.query(WorkerNode).filter_by(status='ONLINE').all()
        avg_cpu_percent = 0.0
        if avg_cpu:
            avg_cpu_percent = round(sum(w.current_cpu_percent for w in avg_cpu) / len(avg_cpu), 2)
        high_risk_count = session.query(ImpactAnalysis).filter(
            ImpactAnalysis.business_impact_level.in_(['HIGH', 'CRITICAL'])
        ).count()

        return jsonify({
            'total_tasks': total_tasks,
            'total_dags': total_dags,
            'total_logs': total_logs,
            'success_today': success_today,
            'failure_today': failure_today,
            'dlq_pending': dlq_pending,
            'running_now': running_now,
            'new_deps_pending': new_deps_pending,
            'dlq_expiring_soon': dlq_expiring_soon,
            'online_workers': online_workers,
            'cluster_avg_cpu_percent': avg_cpu_percent,
            'high_risk_tasks': high_risk_count,
        })
    finally:
        session.close()


@app.route('/api/dependencies/detect', methods=['POST'])
def api_detect_dependencies():
    from scripts.dependency_detector import detect_new_dependencies
    data = request.get_json() or {}
    dag_id = data.get('dag_id')

    task = detect_new_dependencies.delay(dag_id=dag_id)
    return jsonify({
        'status': 'submitted',
        'celery_task_id': task.id,
        'dag_id': dag_id or 'all',
    })


@app.route('/api/dependencies/<dag_id>/changes')
def api_dag_dependency_changes(dag_id):
    from scripts.dependency_detector import get_incremental_dag_changes
    result = get_incremental_dag_changes(dag_id=dag_id)
    return jsonify(result)


@app.route('/api/dependencies/add', methods=['POST'])
def api_add_dependency():
    from scripts.dependency_detector import add_dependency
    data = request.get_json() or {}

    required = ['dag_id', 'upstream_task_id', 'downstream_task_id']
    for field in required:
        if not data.get(field):
            return jsonify({'error': f'{field} is required'}), 400

    result = add_dependency(
        dag_id=data['dag_id'],
        upstream_task_id=data['upstream_task_id'],
        downstream_task_id=data['downstream_task_id'],
        dependency_type=data.get('dependency_type', 'all_success'),
    )
    return jsonify(result)


@app.route('/api/dead-letter/update-ttl/<int:dlq_id>', methods=['POST'])
def api_update_dlq_ttl(dlq_id):
    from celery_app.tasks.dead_letter import update_dlq_ttl
    data = request.get_json() or {}
    ttl_seconds = data.get('ttl_seconds')

    if ttl_seconds is None or ttl_seconds <= 0:
        return jsonify({'error': 'ttl_seconds must be positive'}), 400

    task = update_dlq_ttl.delay(dlq_id=dlq_id, ttl_seconds=ttl_seconds)
    return jsonify({
        'status': 'submitted',
        'dlq_id': dlq_id,
        'ttl_seconds': ttl_seconds,
        'rerun_celery_id': task.id,
    })


@app.route('/api/dead-letter/cleanup', methods=['POST'])
def api_cleanup_expired_dlq():
    from celery_app.tasks.dead_letter import cleanup_expired_dlq
    task = cleanup_expired_dlq.delay()
    return jsonify({
        'status': 'submitted',
        'rerun_celery_id': task.id,
    })


@app.route('/api/dead-letter/<int:dlq_id>/ttl')
def api_dlq_ttl_detail(dlq_id):
    session = get_db_session()
    try:
        entry = session.query(DeadLetterQueue).filter_by(dlq_id=dlq_id).first()
        if not entry:
            return jsonify({'error': 'DLQ entry not found'}), 404

        now = datetime.now()
        is_expired = entry.expires_at and entry.expires_at < now
        remaining_seconds = (entry.expires_at - now).total_seconds() if entry.expires_at and not is_expired else 0

        return jsonify({
            'dlq_id': entry.dlq_id,
            'ttl_seconds': entry.ttl_seconds,
            'dead_lettered_at': entry.dead_lettered_at.isoformat() if entry.dead_lettered_at else None,
            'expires_at': entry.expires_at.isoformat() if entry.expires_at else None,
            'is_expired': is_expired,
            'remaining_seconds': max(0, int(remaining_seconds)),
            'status': entry.status,
        })
    finally:
        session.close()


@app.route('/scheduler')
def scheduler_view():
    return render_template('scheduler.html')


@app.route('/lineage')
def lineage_view():
    return render_template('lineage.html')


@app.route('/impact')
def impact_view():
    return render_template('impact.html')


@app.route('/api/scheduler/resource-snapshot')
def api_resource_snapshot():
    from scheduler.smart_scheduler import get_cluster_resource_snapshot
    return jsonify(get_cluster_resource_snapshot())


@app.route('/api/scheduler/workers')
def api_workers():
    session = get_db_session()
    try:
        workers = session.query(WorkerNode).order_by(WorkerNode.last_heartbeat.desc()).all()
        return jsonify([
            {
                'worker_id': w.worker_id,
                'hostname': w.hostname,
                'queues': w.queues,
                'total_cpu_cores': w.total_cpu_cores,
                'total_memory_mb': w.total_memory_mb,
                'current_cpu_percent': w.current_cpu_percent,
                'current_memory_mb': w.current_memory_mb,
                'active_task_count': w.active_task_count,
                'max_concurrent_tasks': w.max_concurrent_tasks,
                'status': w.status,
                'last_heartbeat': w.last_heartbeat.isoformat() if w.last_heartbeat else None,
                'region': w.region,
            }
            for w in workers
        ])
    finally:
        session.close()


@app.route('/api/scheduler/pending-queue')
def api_pending_queue():
    from scheduler.smart_scheduler import get_pending_scheduling_queue
    return jsonify(get_pending_scheduling_queue())


@app.route('/api/scheduler/decisions')
def api_scheduler_decisions():
    session = get_db_session()
    try:
        limit = request.args.get('limit', 50, type=int)
        rows = session.query(SchedulingDecision).order_by(
            SchedulingDecision.decision_time.desc()
        ).limit(limit).all()
        return jsonify([
            {
                'decision_id': r.decision_id,
                'task_id': r.task_id,
                'dag_id': r.dag_id,
                'worker_id': r.worker_id,
                'queue_name': r.queue_name,
                'decision_type': r.decision_type,
                'priority_score': r.priority_score,
                'resource_score': r.resource_score,
                'business_score': r.business_score,
                'waiting_minutes': r.waiting_minutes,
                'reason': r.reason,
                'decision_time': r.decision_time.isoformat(),
                'status': r.status,
            }
            for r in rows
        ])
    finally:
        session.close()


@app.route('/api/scheduler/allocate', methods=['POST'])
def api_scheduler_allocate():
    data = request.get_json() or {}
    from scheduler.smart_scheduler import smart_schedule_task
    result = smart_schedule_task(
        dag_id=data.get('dag_id', ''),
        task_id=data.get('task_id', ''),
        celery_task_id=data.get('celery_task_id', ''),
        run_id=data.get('run_id'),
    )
    return jsonify(result)


@app.route('/api/scheduler/release/<celery_task_id>', methods=['POST'])
def api_scheduler_release(celery_task_id):
    from scheduler.smart_scheduler import release_task_resources
    return jsonify(release_task_resources(celery_task_id))


@app.route('/api/scheduler/worker-heartbeat', methods=['POST'])
def api_worker_heartbeat():
    data = request.get_json() or {}
    from scheduler.smart_scheduler import update_worker_heartbeat
    return jsonify(update_worker_heartbeat(
        worker_id=data.get('worker_id', ''),
        hostname=data.get('hostname', ''),
        queues=data.get('queues'),
        cpu_percent=data.get('cpu_percent'),
        memory_mb=data.get('memory_mb'),
        active_count=data.get('active_count'),
        region=data.get('region'),
        labels=data.get('labels'),
    ))


@app.route('/api/impact/analyze', methods=['POST'])
def api_impact_analyze():
    data = request.get_json() or {}
    from scheduler.impact_analyzer import analyze_task_impact
    result = analyze_task_impact(
        dag_id=data.get('dag_id', ''),
        task_id=data.get('task_id', ''),
        analysis_type=data.get('analysis_type', 'FAILURE_PREDICTION'),
    )
    return jsonify(result)


@app.route('/api/impact/history')
def api_impact_history():
    from scheduler.impact_analyzer import get_impact_history
    return jsonify(get_impact_history(
        task_id=request.args.get('task_id'),
        dag_id=request.args.get('dag_id'),
        limit=request.args.get('limit', 20, type=int),
    ))


@app.route('/api/impact/high-risk')
def api_impact_high_risk():
    from scheduler.impact_analyzer import get_high_risk_tasks
    return jsonify(get_high_risk_tasks(
        dag_id=request.args.get('dag_id'),
        threshold_prob=request.args.get('threshold_prob', 0.25, type=float),
        threshold_impact=request.args.get('threshold_impact', 'MEDIUM'),
    ))


@app.route('/api/impact/simulate-failure', methods=['POST'])
def api_simulate_failure():
    data = request.get_json() or {}
    from scheduler.impact_analyzer import cascade_failure_simulation
    return jsonify(cascade_failure_simulation(
        dag_id=data.get('dag_id', ''),
        failed_task_id=data.get('task_id', ''),
    ))


@app.route('/api/lineage/record', methods=['POST'])
def api_lineage_record():
    data = request.get_json() or {}
    from scheduler.task_lineage import record_lineage
    return jsonify(record_lineage(
        dag_id=data.get('dag_id', ''),
        task_id=data.get('task_id', ''),
        run_id=data.get('run_id', ''),
        source_dataset=data.get('source_dataset'),
        target_dataset=data.get('target_dataset'),
        transformation_type=data.get('transformation_type'),
        row_count=data.get('row_count'),
        parent_lineage_ids=data.get('parent_lineage_ids'),
        data_sample=data.get('data_sample'),
        metadata=data.get('metadata'),
    ))


@app.route('/api/lineage/upstream/<dag_id>/<task_id>')
def api_lineage_upstream(dag_id, task_id):
    from scheduler.task_lineage import get_upstream_lineage
    return jsonify(get_upstream_lineage(
        dag_id=dag_id,
        task_id=task_id,
        run_id=request.args.get('run_id'),
        max_depth=request.args.get('max_depth', 10, type=int),
    ))


@app.route('/api/lineage/downstream/<dag_id>/<task_id>')
def api_lineage_downstream(dag_id, task_id):
    from scheduler.task_lineage import get_downstream_lineage
    return jsonify(get_downstream_lineage(
        dag_id=dag_id,
        task_id=task_id,
        run_id=request.args.get('run_id'),
        max_depth=request.args.get('max_depth', 10, type=int),
    ))


@app.route('/api/lineage/dataset/<path:dataset_name>')
def api_lineage_dataset(dataset_name):
    from scheduler.task_lineage import get_dataset_lineage
    return jsonify(get_dataset_lineage(
        dataset_name=dataset_name,
        direction=request.args.get('direction', 'BOTH'),
    ))


@app.route('/api/lineage/dag-graph/<dag_id>')
def api_lineage_dag_graph(dag_id):
    from scheduler.task_lineage import get_full_dag_lineage_graph
    return jsonify(get_full_dag_lineage_graph(
        dag_id=dag_id,
        run_id=request.args.get('run_id'),
    ))


@app.route('/api/lineage/data-flow/<dag_id>/<task_id>')
def api_lineage_data_flow(dag_id, task_id):
    from scheduler.task_lineage import trace_data_flow
    return jsonify(trace_data_flow(
        dag_id=dag_id,
        task_id=task_id,
        run_id=request.args.get('run_id'),
    ))


@app.route('/api/lineage/list')
def api_lineage_list():
    session = get_db_session()
    try:
        limit = request.args.get('limit', 100, type=int)
        dag_id = request.args.get('dag_id')
        rows = session.query(TaskLineage)
        if dag_id:
            rows = rows.filter(TaskLineage.dag_id == dag_id)
        rows = rows.order_by(TaskLineage.execution_time.desc()).limit(limit).all()
        return jsonify([
            {
                'lineage_id': r.lineage_id,
                'dag_id': r.dag_id,
                'task_id': r.task_id,
                'run_id': r.run_id,
                'source_dataset': r.source_dataset,
                'target_dataset': r.target_dataset,
                'transformation_type': r.transformation_type,
                'row_count': r.row_count,
                'execution_time': r.execution_time.isoformat(),
            }
            for r in rows
        ])
    finally:
        session.close()


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
