import os
import sys
import hashlib
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from collections import defaultdict, deque

from models.task_model import (
    get_db_session,
    TaskLineage,
    TaskDependency,
    TaskDefinition,
)


def record_lineage(dag_id, task_id, run_id, source_dataset=None,
                   target_dataset=None, transformation_type=None,
                   row_count=None, parent_lineage_ids=None,
                   data_sample=None, metadata=None):
    """Record a task's data lineage entry after successful execution."""
    session = get_db_session()
    try:
        data_hash = None
        if data_sample:
            if isinstance(data_sample, (dict, list)):
                data_sample = json.dumps(data_sample, sort_keys=True, default=str)
            data_hash = hashlib.md5(str(data_sample).encode('utf-8')).hexdigest()

        if isinstance(parent_lineage_ids, list):
            parent_lineage_ids = ','.join(str(x) for x in parent_lineage_ids)

        entry = TaskLineage(
            dag_id=dag_id,
            task_id=task_id,
            run_id=run_id,
            source_dataset=source_dataset,
            target_dataset=target_dataset,
            transformation_type=transformation_type,
            row_count=row_count,
            data_hash=data_hash,
            parent_lineage_ids=parent_lineage_ids,
            execution_time=datetime.utcnow(),
            metadata=metadata,
        )
        session.add(entry)
        session.commit()
        return {'status': 'ok', 'lineage_id': entry.lineage_id}
    except Exception as e:
        session.rollback()
        return {'status': 'error', 'message': str(e)}
    finally:
        session.close()


def _resolve_parent_lineages(session, dag_id, task_id, run_id):
    """Find lineage records produced by upstream tasks in the same DAG run."""
    deps = session.query(TaskDependency).filter(
        TaskDependency.dag_id == dag_id,
        TaskDependency.downstream_task_id == task_id,
    ).all()
    upstream_task_ids = [d.upstream_task_id for d in deps]
    if not upstream_task_ids:
        return []
    rows = session.query(TaskLineage).filter(
        TaskLineage.dag_id == dag_id,
        TaskLineage.task_id.in_(upstream_task_ids),
        TaskLineage.run_id == run_id,
    ).all()
    return rows


def get_upstream_lineage(dag_id, task_id, run_id=None, max_depth=10):
    """Trace lineage upstream to find source tasks/datasets feeding the given task."""
    session = get_db_session()
    try:
        deps = session.query(TaskDependency).filter(
            TaskDependency.dag_id == dag_id
        ).all()
        up_graph = defaultdict(list)
        for d in deps:
            up_graph[d.downstream_task_id].append(d.upstream_task_id)

        visited = set()
        queue = deque([(task_id, 0)])
        upstream_tasks = []
        while queue:
            cur, depth = queue.popleft()
            if cur in visited or depth > max_depth:
                continue
            visited.add(cur)
            parents = up_graph.get(cur, [])
            for p in parents:
                upstream_tasks.append((cur, p))
                queue.append((p, depth + 1))

        query_filters = [TaskLineage.dag_id == dag_id, TaskLineage.task_id.in_(list(visited))]
        if run_id:
            query_filters.append(TaskLineage.run_id == run_id)
        lineage_rows = session.query(TaskLineage).filter(*query_filters).order_by(
            TaskLineage.execution_time.desc()
        ).all()

        return {
            'dag_id': dag_id,
            'task_id': task_id,
            'upstream_tasks': sorted(visited - {task_id}),
            'lineage_entries': [
                {
                    'lineage_id': r.lineage_id,
                    'task_id': r.task_id,
                    'run_id': r.run_id,
                    'source_dataset': r.source_dataset,
                    'target_dataset': r.target_dataset,
                    'transformation_type': r.transformation_type,
                    'row_count': r.row_count,
                    'data_hash': r.data_hash,
                    'execution_time': r.execution_time.isoformat(),
                }
                for r in lineage_rows
            ],
        }
    finally:
        session.close()


def get_downstream_lineage(dag_id, task_id, run_id=None, max_depth=10):
    """Trace lineage downstream to find tasks consuming the output of a given task."""
    session = get_db_session()
    try:
        deps = session.query(TaskDependency).filter(
            TaskDependency.dag_id == dag_id
        ).all()
        down_graph = defaultdict(list)
        for d in deps:
            down_graph[d.upstream_task_id].append(d.downstream_task_id)

        visited = set()
        queue = deque([(task_id, 0)])
        while queue:
            cur, depth = queue.popleft()
            if cur in visited or depth > max_depth:
                continue
            visited.add(cur)
            for nxt in down_graph.get(cur, []):
                queue.append((nxt, depth + 1))

        query_filters = [TaskLineage.dag_id == dag_id, TaskLineage.task_id.in_(list(visited))]
        if run_id:
            query_filters.append(TaskLineage.run_id == run_id)
        lineage_rows = session.query(TaskLineage).filter(*query_filters).order_by(
            TaskLineage.execution_time.desc()
        ).all()

        return {
            'dag_id': dag_id,
            'task_id': task_id,
            'downstream_tasks': sorted(visited - {task_id}),
            'lineage_entries': [
                {
                    'lineage_id': r.lineage_id,
                    'task_id': r.task_id,
                    'run_id': r.run_id,
                    'source_dataset': r.source_dataset,
                    'target_dataset': r.target_dataset,
                    'transformation_type': r.transformation_type,
                    'row_count': r.row_count,
                    'data_hash': r.data_hash,
                    'execution_time': r.execution_time.isoformat(),
                }
                for r in lineage_rows
            ],
        }
    finally:
        session.close()


def get_dataset_lineage(dataset_name, direction='BOTH'):
    """Find all tasks that read/write a given dataset, build the dataset graph."""
    session = get_db_session()
    try:
        filters = []
        if direction == 'SOURCE':
            filters.append(TaskLineage.source_dataset == dataset_name)
        elif direction == 'TARGET':
            filters.append(TaskLineage.target_dataset == dataset_name)
        else:
            from sqlalchemy import or_
            filters.append(or_(
                TaskLineage.source_dataset == dataset_name,
                TaskLineage.target_dataset == dataset_name,
            ))
        rows = session.query(TaskLineage).filter(*filters).order_by(
            TaskLineage.execution_time.desc()
        ).limit(200).all()

        readers = set()
        writers = set()
        for r in rows:
            if r.source_dataset == dataset_name:
                readers.add(r.task_id)
            if r.target_dataset == dataset_name:
                writers.add(r.task_id)

        return {
            'dataset': dataset_name,
            'reader_tasks': sorted(readers),
            'writer_tasks': sorted(writers),
            'lineage_entries': [
                {
                    'lineage_id': r.lineage_id,
                    'dag_id': r.dag_id,
                    'task_id': r.task_id,
                    'run_id': r.run_id,
                    'source_dataset': r.source_dataset,
                    'target_dataset': r.target_dataset,
                    'execution_time': r.execution_time.isoformat(),
                    'row_count': r.row_count,
                    'data_hash': r.data_hash,
                }
                for r in rows
            ],
        }
    finally:
        session.close()


def get_full_dag_lineage_graph(dag_id, run_id=None):
    """Build full lineage graph for a DAG, returning nodes and edges."""
    session = get_db_session()
    try:
        query_filters = [TaskLineage.dag_id == dag_id]
        if run_id:
            query_filters.append(TaskLineage.run_id == run_id)
        rows = session.query(TaskLineage).filter(*query_filters).order_by(
            TaskLineage.execution_time.asc()
        ).all()

        nodes = {}
        edges = []
        for r in rows:
            nodes[r.task_id] = {'task_id': r.task_id, 'type': 'task'}
            if r.source_dataset:
                nodes[r.source_dataset] = {'dataset': r.source_dataset, 'type': 'dataset'}
                edges.append({'from': r.source_dataset, 'to': r.task_id, 'type': 'reads'})
            if r.target_dataset:
                nodes[r.target_dataset] = {'dataset': r.target_dataset, 'type': 'dataset'}
                edges.append({'from': r.task_id, 'to': r.target_dataset, 'type': 'writes'})

        return {
            'dag_id': dag_id,
            'run_id': run_id,
            'nodes': list(nodes.values()),
            'edges': edges,
            'lineage_count': len(rows),
        }
    finally:
        session.close()


def trace_data_flow(dag_id, task_id, run_id=None):
    """Combine upstream + downstream to show the full data flow through a task."""
    upstream = get_upstream_lineage(dag_id, task_id, run_id)
    downstream = get_downstream_lineage(dag_id, task_id, run_id)
    return {
        'task_id': task_id,
        'dag_id': dag_id,
        'run_id': run_id,
        'upstream': upstream,
        'downstream': downstream,
    }
