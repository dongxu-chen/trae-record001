import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from sqlalchemy import and_

from models.task_model import (
    get_db_session,
    TaskDefinition,
    WorkerNode,
    ResourceAllocation,
    SchedulingDecision,
    TaskExecutionLog,
)


RESOURCE_PROFILES = {
    'SMALL': {'cpu': 10.0, 'memory': 256, 'duration': 120},
    'MEDIUM': {'cpu': 25.0, 'memory': 512, 'duration': 300},
    'LARGE': {'cpu': 50.0, 'memory': 1024, 'duration': 600},
    'XLARGE': {'cpu': 80.0, 'memory': 2048, 'duration': 1200},
}

BUSINESS_CRIT_WEIGHTS = {
    'CRITICAL': 1.0,
    'HIGH': 0.75,
    'MEDIUM': 0.5,
    'LOW': 0.25,
}


def _estimate_task_resources(task_def):
    """Estimate required CPU/memory for a task based on profile or explicit values."""
    profile = task_def.resource_profile or 'MEDIUM'
    p = RESOURCE_PROFILES.get(profile, RESOURCE_PROFILES['MEDIUM'])
    cpu = task_def.estimated_cpu_percent if task_def.estimated_cpu_percent > 0 else p['cpu']
    mem = task_def.estimated_memory_mb if task_def.estimated_memory_mb > 0 else p['memory']
    return cpu, mem


def _compute_priority_score(task_def, waiting_minutes=0):
    """Combined priority score: business criticality * time_weight + base priority."""
    crit = BUSINESS_CRIT_WEIGHTS.get(task_def.business_criticality or 'MEDIUM', 0.5)
    time_pressure = min(waiting_minutes / 60.0, 1.0)
    base_prio = (task_def.priority or 5) / 10.0
    return round(crit * 0.4 + time_pressure * 0.3 + base_prio * 0.3, 4)


def _compute_resource_score(worker, required_cpu, required_memory):
    """Resource fit score: higher is better (0..1)."""
    available_cpu = max(0.0, 100.0 - worker.current_cpu_percent)
    available_mem = max(0, worker.total_memory_mb - worker.current_memory_mb)
    cpu_ratio = required_cpu / available_cpu if available_cpu > 0 else 999
    mem_ratio = required_memory / available_mem if available_mem > 0 else 999
    if cpu_ratio > 1.0 or mem_ratio > 1.0:
        return 0.0
    concurrency_ratio = worker.active_task_count / max(worker.max_concurrent_tasks, 1)
    fit = (1.0 - cpu_ratio * 0.4 - mem_ratio * 0.4 - concurrency_ratio * 0.2)
    return round(max(0.0, min(1.0, fit)), 4)


def _select_best_worker(task_def, session):
    """Select the best worker for a task given current resource utilization."""
    required_cpu, required_mem = _estimate_task_resources(task_def)
    queue_name = task_def.queue or 'celery'

    workers = session.query(WorkerNode).filter(
        WorkerNode.status == 'ONLINE',
        WorkerNode.queues.contains(queue_name),
    ).all()

    if not workers:
        return None, 'NO_AVAILABLE_WORKER'

    best_worker = None
    best_score = -1.0
    reason = None

    for w in workers:
        if w.active_task_count >= w.max_concurrent_tasks:
            continue
        score = _compute_resource_score(w, required_cpu, required_mem)
        if score <= 0:
            continue
        if score > best_score:
            best_score = score
            best_worker = w

    if best_worker is None:
        return None, 'NO_WORKER_WITH_ENOUGH_RESOURCES'

    reason = (
        f"Selected worker {best_worker.worker_id} "
        f"(cpu={best_worker.current_cpu_percent}%, mem={best_worker.current_memory_mb}MB, "
        f"active={best_worker.active_task_count}/{best_worker.max_concurrent_tasks}) "
        f"with resource fit score={best_score}"
    )
    return best_worker, reason


def smart_schedule_task(dag_id, task_id, celery_task_id, run_id=None):
    """Make a smart scheduling decision and persist allocation."""
    session = get_db_session()
    try:
        task_def = session.query(TaskDefinition).filter(
            TaskDefinition.task_id == task_id
        ).first()
        if not task_def:
            return {'status': 'error', 'message': f'Task {task_id} not found'}

        waiting_logs = session.query(TaskExecutionLog).filter(
            TaskExecutionLog.task_id == task_id,
            TaskExecutionLog.status == 'PENDING',
        ).all()
        waiting_minutes = 0
        if waiting_logs:
            earliest = min(l.execution_date for l in waiting_logs)
            waiting_minutes = int((datetime.utcnow() - earliest).total_seconds() / 60)

        priority_score = _compute_priority_score(task_def, waiting_minutes)

        best_worker, reason = _select_best_worker(task_def, session)

        if best_worker is None:
            decision = SchedulingDecision(
                task_id=task_id,
                dag_id=dag_id,
                worker_id=None,
                queue_name=task_def.queue,
                decision_type='DEFER',
                priority_score=priority_score,
                resource_score=0.0,
                business_score=BUSINESS_CRIT_WEIGHTS.get(task_def.business_criticality or 'MEDIUM', 0.5),
                waiting_minutes=waiting_minutes,
                reason=f'Deferred: {reason}',
                decision_time=datetime.utcnow(),
                status='PENDING',
            )
            session.add(decision)
            session.commit()
            return {
                'status': 'deferred',
                'decision_id': decision.decision_id,
                'reason': reason,
                'priority_score': priority_score,
            }

        required_cpu, required_mem = _estimate_task_resources(task_def)
        resource_score = _compute_resource_score(best_worker, required_cpu, required_mem)

        decision = SchedulingDecision(
            task_id=task_id,
            dag_id=dag_id,
            worker_id=best_worker.worker_id,
            queue_name=task_def.queue,
            decision_type='SCHEDULE',
            priority_score=priority_score,
            resource_score=resource_score,
            business_score=BUSINESS_CRIT_WEIGHTS.get(task_def.business_criticality or 'MEDIUM', 0.5),
            waiting_minutes=waiting_minutes,
            reason=reason,
            decision_time=datetime.utcnow(),
            status='EXECUTED',
        )
        session.add(decision)

        allocation = ResourceAllocation(
            celery_task_id=celery_task_id or '',
            dag_id=dag_id,
            task_id=task_id,
            worker_id=best_worker.worker_id,
            queue_name=task_def.queue,
            allocated_cpu_percent=required_cpu,
            allocated_memory_mb=required_mem,
            allocation_strategy='SMART',
            decision_reason=reason,
            allocation_time=datetime.utcnow(),
            status='ALLOCATED',
        )
        session.add(allocation)

        best_worker.current_cpu_percent += required_cpu
        best_worker.current_memory_mb += required_mem
        best_worker.active_task_count += 1
        best_worker.updated_at = datetime.utcnow()

        session.commit()
        return {
            'status': 'scheduled',
            'decision_id': decision.decision_id,
            'worker_id': best_worker.worker_id,
            'priority_score': priority_score,
            'resource_score': resource_score,
        }
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()


def release_task_resources(celery_task_id):
    """Release allocated resources after a task finishes."""
    session = get_db_session()
    try:
        allocations = session.query(ResourceAllocation).filter(
            ResourceAllocation.celery_task_id == celery_task_id,
            ResourceAllocation.status == 'ALLOCATED',
        ).all()
        for alloc in allocations:
            worker = session.query(WorkerNode).filter(
                WorkerNode.worker_id == alloc.worker_id
            ).first()
            if worker:
                worker.current_cpu_percent = max(0.0, worker.current_cpu_percent - alloc.allocated_cpu_percent)
                worker.current_memory_mb = max(0, worker.current_memory_mb - alloc.allocated_memory_mb)
                worker.active_task_count = max(0, worker.active_task_count - 1)
                worker.updated_at = datetime.utcnow()
            alloc.status = 'RELEASED'
            alloc.release_time = datetime.utcnow()
        session.commit()
        return {'status': 'ok', 'released_count': len(allocations)}
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()


def update_worker_heartbeat(worker_id, hostname, queues=None, cpu_percent=None,
                            memory_mb=None, active_count=None, region=None, labels=None):
    """Register or update a worker node's resource snapshot."""
    session = get_db_session()
    try:
        worker = session.query(WorkerNode).filter(WorkerNode.worker_id == worker_id).first()
        now = datetime.utcnow()
        if not worker:
            worker = WorkerNode(
                worker_id=worker_id,
                hostname=hostname,
                queues=queues or 'celery',
                status='ONLINE',
                last_heartbeat=now,
                created_at=now,
                updated_at=now,
            )
            if region:
                worker.region = region
            if labels:
                worker.labels = labels
            session.add(worker)
        else:
            if cpu_percent is not None:
                worker.current_cpu_percent = cpu_percent
            if memory_mb is not None:
                worker.current_memory_mb = memory_mb
            if active_count is not None:
                worker.active_task_count = active_count
            if queues is not None:
                worker.queues = queues
            worker.status = 'ONLINE'
            worker.last_heartbeat = now
            worker.updated_at = now
        session.commit()
        return {'status': 'ok', 'worker_id': worker_id}
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()


def mark_workers_offline(timeout_sec=300):
    """Mark workers that haven't sent a heartbeat recently as OFFLINE."""
    session = get_db_session()
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(seconds=timeout_sec)
        workers = session.query(WorkerNode).filter(
            WorkerNode.status == 'ONLINE',
            WorkerNode.last_heartbeat < cutoff,
        ).all()
        for w in workers:
            w.status = 'OFFLINE'
            w.updated_at = datetime.utcnow()
        session.commit()
        return {'status': 'ok', 'marked_offline': len(workers)}
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()


def get_cluster_resource_snapshot():
    """Return overall cluster resource utilization snapshot."""
    session = get_db_session()
    try:
        workers = session.query(WorkerNode).filter(WorkerNode.status == 'ONLINE').all()
        if not workers:
            return {
                'total_workers': 0,
                'total_cpu_cores': 0,
                'total_memory_mb': 0,
                'avg_cpu_percent': 0.0,
                'avg_memory_percent': 0.0,
                'total_active_tasks': 0,
                'bottleneck_workers': [],
            }
        total_cpu = sum(w.total_cpu_cores for w in workers)
        total_mem = sum(w.total_memory_mb for w in workers)
        avg_cpu = round(sum(w.current_cpu_percent for w in workers) / len(workers), 2)
        avg_mem_percent = round(
            sum(w.current_memory_mb / max(w.total_memory_mb, 1) * 100 for w in workers) / len(workers),
            2,
        )
        total_active = sum(w.active_task_count for w in workers)
        bottlenecks = [
            {'worker_id': w.worker_id, 'cpu_percent': w.current_cpu_percent,
             'memory_mb': w.current_memory_mb, 'active': w.active_task_count}
            for w in workers
            if w.current_cpu_percent > 80 or w.active_task_count >= w.max_concurrent_tasks
        ]
        return {
            'total_workers': len(workers),
            'total_cpu_cores': total_cpu,
            'total_memory_mb': total_mem,
            'avg_cpu_percent': avg_cpu,
            'avg_memory_percent': avg_mem_percent,
            'total_active_tasks': total_active,
            'bottleneck_workers': bottlenecks,
        }
    finally:
        session.close()


def get_pending_scheduling_queue(limit=50):
    """Return the current scheduling priority queue of pending tasks."""
    session = get_db_session()
    try:
        from models.task_model import TaskDependency
        logs = session.query(TaskExecutionLog).filter(
            TaskExecutionLog.status == 'PENDING',
        ).order_by(TaskExecutionLog.execution_date.asc()).limit(limit).all()
        result = []
        for log in logs:
            task_def = session.query(TaskDefinition).filter(
                TaskDefinition.task_id == log.task_id
            ).first()
            if task_def:
                result.append({
                    'log_id': log.log_id,
                    'dag_id': log.dag_id,
                    'task_id': log.task_id,
                    'task_name': task_def.task_name,
                    'business_criticality': task_def.business_criticality,
                    'priority': task_def.priority,
                    'waiting_since': log.execution_date.isoformat(),
                })
        return result
    finally:
        session.close()
