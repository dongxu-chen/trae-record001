import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from collections import defaultdict, deque

from models.task_model import (
    get_db_session,
    TaskDefinition,
    TaskDependency,
    TaskExecutionLog,
    ImpactAnalysis,
    TaskLineage,
)


def _build_dag_graph(session, dag_id):
    """Build adjacency list for downstream propagation (upstream -> [downstream])."""
    deps = session.query(TaskDependency).filter(
        TaskDependency.dag_id == dag_id
    ).all()
    graph = defaultdict(list)
    all_tasks = set()
    for d in deps:
        graph[d.upstream_task_id].append(d.downstream_task_id)
        all_tasks.add(d.upstream_task_id)
        all_tasks.add(d.downstream_task_id)
    return graph, all_tasks


def _traverse_downstream(graph, start_task):
    """Return all reachable downstream tasks from start_task (BFS)."""
    visited = set()
    queue = deque([start_task])
    while queue:
        cur = queue.popleft()
        for nxt in graph.get(cur, []):
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    return visited


def _get_affected_datasets(session, task_ids):
    """Collect datasets written by affected tasks via lineage."""
    datasets = set()
    if not task_ids:
        return datasets
    lineage_rows = session.query(TaskLineage).filter(
        TaskLineage.task_id.in_(list(task_ids))
    ).all()
    for r in lineage_rows:
        if r.target_dataset:
            datasets.add(r.target_dataset)
    return datasets


def _estimate_failure_probability(session, task_id, lookback_days=30):
    """Estimate failure probability from recent execution history."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=lookback_days)
    logs = session.query(TaskExecutionLog).filter(
        TaskExecutionLog.task_id == task_id,
        TaskExecutionLog.execution_date >= cutoff,
    ).all()
    if not logs:
        task_def = session.query(TaskDefinition).filter(
            TaskDefinition.task_id == task_id
        ).first()
        if task_def and task_def.business_criticality == 'CRITICAL':
            return 0.10
        return 0.05
    total = len(logs)
    failed = sum(1 for l in logs if l.status in ('FAILURE', 'DEAD_LETTER'))
    p = failed / total
    if total < 5:
        p = p * 0.6 + 0.05 * 0.4
    return round(min(p, 0.95), 4)


def _estimate_recovery_minutes(session, task_id, affected_count):
    """Estimate recovery time based on average duration + downstream fan-out."""
    from datetime import timedelta
    logs = session.query(TaskExecutionLog).filter(
        TaskExecutionLog.task_id == task_id,
        TaskExecutionLog.duration_sec.isnot(None),
    ).order_by(TaskExecutionLog.execution_date.desc()).limit(10).all()
    avg_duration = 0
    if logs:
        avg_duration = sum(l.duration_sec for l in logs) / len(logs)
    return int(avg_duration / 60) + affected_count * 5


def analyze_task_impact(dag_id, task_id, analysis_type='FAILURE_PREDICTION'):
    """Perform impact analysis for a given task. Persist result to impact_analyses."""
    session = get_db_session()
    try:
        graph, _ = _build_dag_graph(session, dag_id)
        affected_tasks = _traverse_downstream(graph, task_id)
        affected_count = len(affected_tasks)
        affected_datasets = _get_affected_datasets(session, affected_tasks | {task_id})

        failure_prob = _estimate_failure_probability(session, task_id)

        task_def = session.query(TaskDefinition).filter(
            TaskDefinition.task_id == task_id
        ).first()
        crit = task_def.business_criticality if task_def else 'MEDIUM'

        if crit == 'CRITICAL' or affected_count >= 5:
            impact_level = 'CRITICAL'
        elif crit == 'HIGH' or affected_count >= 3 or failure_prob >= 0.3:
            impact_level = 'HIGH'
        elif affected_count >= 1 or failure_prob >= 0.15:
            impact_level = 'MEDIUM'
        else:
            impact_level = 'LOW'

        recovery_min = _estimate_recovery_minutes(session, task_id, affected_count)

        recommendations = []
        if impact_level in ('HIGH', 'CRITICAL'):
            recommendations.append('优先人工介入，避免下游级联失败')
        if failure_prob >= 0.3:
            recommendations.append('历史失败率较高，建议检查任务逻辑和依赖资源')
        if affected_count >= 3:
            recommendations.append(f'影响 {affected_count} 个下游任务，建议延迟发布或分批执行')
        if not recommendations:
            recommendations.append('当前风险可控，按常规流程处理')

        analysis = ImpactAnalysis(
            dag_id=dag_id,
            task_id=task_id,
            analysis_type=analysis_type,
            failure_probability=failure_prob,
            affected_downstream_count=affected_count,
            affected_task_list=','.join(sorted(affected_tasks)),
            affected_dataset_list=','.join(sorted(affected_datasets)),
            estimated_recovery_minutes=recovery_min,
            business_impact_level=impact_level,
            recommended_actions='; '.join(recommendations),
            analysis_time=datetime.utcnow(),
            metadata={
                'business_criticality': crit,
                'affected_tasks': sorted(affected_tasks),
                'affected_datasets': sorted(affected_datasets),
            },
        )
        session.add(analysis)
        session.commit()

        return {
            'analysis_id': analysis.analysis_id,
            'dag_id': dag_id,
            'task_id': task_id,
            'failure_probability': failure_prob,
            'affected_downstream_count': affected_count,
            'affected_tasks': sorted(affected_tasks),
            'affected_datasets': sorted(affected_datasets),
            'business_impact_level': impact_level,
            'estimated_recovery_minutes': recovery_min,
            'recommendations': recommendations,
        }
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()


def get_impact_history(task_id=None, dag_id=None, limit=20):
    """Retrieve recent impact analyses for a task / DAG."""
    session = get_db_session()
    try:
        q = session.query(ImpactAnalysis)
        if task_id:
            q = q.filter(ImpactAnalysis.task_id == task_id)
        if dag_id:
            q = q.filter(ImpactAnalysis.dag_id == dag_id)
        rows = q.order_by(ImpactAnalysis.analysis_time.desc()).limit(limit).all()
        return [
            {
                'analysis_id': r.analysis_id,
                'dag_id': r.dag_id,
                'task_id': r.task_id,
                'failure_probability': r.failure_probability,
                'affected_downstream_count': r.affected_downstream_count,
                'business_impact_level': r.business_impact_level,
                'recommended_actions': r.recommended_actions,
                'analysis_time': r.analysis_time.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


def get_high_risk_tasks(dag_id=None, threshold_prob=0.25, threshold_impact='MEDIUM'):
    """Return tasks whose most recent impact analysis exceeds risk thresholds."""
    session = get_db_session()
    try:
        q = session.query(ImpactAnalysis)
        if dag_id:
            q = q.filter(ImpactAnalysis.dag_id == dag_id)
        q = q.filter(ImpactAnalysis.failure_probability >= threshold_prob)
        if threshold_impact == 'HIGH':
            q = q.filter(ImpactAnalysis.business_impact_level.in_(['HIGH', 'CRITICAL']))
        elif threshold_impact == 'CRITICAL':
            q = q.filter(ImpactAnalysis.business_impact_level == 'CRITICAL')
        rows = q.order_by(ImpactAnalysis.analysis_time.desc()).limit(50).all()
        seen = set()
        result = []
        for r in rows:
            key = (r.dag_id, r.task_id)
            if key in seen:
                continue
            seen.add(key)
            result.append({
                'dag_id': r.dag_id,
                'task_id': r.task_id,
                'failure_probability': r.failure_probability,
                'business_impact_level': r.business_impact_level,
                'affected_downstream_count': r.affected_downstream_count,
                'recommended_actions': r.recommended_actions,
                'analysis_time': r.analysis_time.isoformat(),
            })
        return result
    finally:
        session.close()


def cascade_failure_simulation(dag_id, failed_task_id):
    """Simulate cascade failure path, returning downstream tasks and datasets."""
    session = get_db_session()
    try:
        graph, _ = _build_dag_graph(session, dag_id)
        affected = _traverse_downstream(graph, failed_task_id)
        datasets = _get_affected_datasets(session, affected | {failed_task_id})
        return {
            'failed_task': failed_task_id,
            'downstream_cascade_count': len(affected),
            'downstream_tasks': sorted(affected),
            'affected_datasets': sorted(datasets),
        }
    finally:
        session.close()
