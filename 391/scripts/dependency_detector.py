from celery import shared_task
from celery.utils.log import get_task_logger
from models.task_model import get_db_session, TaskDependency, DAGDefinition, TaskDefinition
from datetime import datetime
from collections import defaultdict

logger = get_task_logger(__name__)


@shared_task(bind=True, name='scripts.dependency.detect_new_dependencies')
def detect_new_dependencies(self, dag_id=None, **kwargs):
    logger.info(f"Starting incremental dependency detection, dag_id={dag_id}")
    session = get_db_session()
    try:
        query = session.query(TaskDependency).filter_by(is_detected=False)
        if dag_id:
            query = query.filter_by(dag_id=dag_id)

        new_deps = query.all()
        detected_count = 0

        for dep in new_deps:
            upstream = session.query(TaskDefinition).filter_by(task_id=dep.upstream_task_id).first()
            downstream = session.query(TaskDefinition).filter_by(task_id=dep.downstream_task_id).first()

            if upstream and downstream:
                dep.is_detected = True
                dep.detected_at = datetime.now()
                dep.source = 'AUTO_DETECT'
                detected_count += 1
                logger.info(
                    f"New dependency detected: {dep.upstream_task_id} -> {dep.downstream_task_id} "
                    f"in DAG {dep.dag_id} (type: {dep.dependency_type})"
                )
            else:
                logger.warning(
                    f"Skipping dependency {dep.upstream_task_id} -> {dep.downstream_task_id}: "
                    f"upstream or downstream task not found"
                )

        session.commit()
        logger.info(f"Incremental dependency detection completed: {detected_count} new dependencies detected")
        return {'status': 'success', 'detected_count': detected_count}

    except Exception as e:
        logger.error(f"Error in dependency detection: {e}")
        session.rollback()
        return {'status': 'error', 'error': str(e)}
    finally:
        session.close()


@shared_task(bind=True, name='scripts.dependency.validate_dag_graph')
def validate_dag_graph(self, dag_id, **kwargs):
    logger.info(f"Validating DAG graph for: {dag_id}")
    session = get_db_session()
    try:
        deps = session.query(TaskDependency).filter_by(dag_id=dag_id, is_detected=True).all()
        if not deps:
            return {'status': 'warning', 'message': f'No detected dependencies for DAG {dag_id}'}

        adj = defaultdict(list)
        in_degree = defaultdict(int)
        task_ids = set()

        for dep in deps:
            adj[dep.upstream_task_id].append(dep.downstream_task_id)
            in_degree[dep.downstream_task_id] += 1
            task_ids.add(dep.upstream_task_id)
            task_ids.add(dep.downstream_task_id)

        queue = [t for t in task_ids if in_degree[t] == 0]
        visited = 0
        topo_order = []

        while queue:
            node = queue.pop(0)
            topo_order.append(node)
            visited += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        has_cycle = visited != len(task_ids)

        if has_cycle:
            cycle_tasks = [t for t in task_ids if in_degree[t] > 0]
            logger.error(f"Cycle detected in DAG {dag_id}: {cycle_tasks}")
            return {
                'status': 'error',
                'dag_id': dag_id,
                'has_cycle': True,
                'cycle_tasks': cycle_tasks,
            }

        logger.info(f"DAG {dag_id} validation passed, topo order: {topo_order}")
        return {
            'status': 'success',
            'dag_id': dag_id,
            'has_cycle': False,
            'task_count': len(task_ids),
            'topo_order': topo_order,
        }

    except Exception as e:
        logger.error(f"Error validating DAG graph {dag_id}: {e}")
        return {'status': 'error', 'error': str(e)}
    finally:
        session.close()


@shared_task(bind=True, name='scripts.dependency.get_incremental_dag_changes')
def get_incremental_dag_changes(self, dag_id, **kwargs):
    logger.info(f"Getting incremental DAG changes for: {dag_id}")
    session = get_db_session()
    try:
        all_deps = session.query(TaskDependency).filter_by(dag_id=dag_id).all()
        new_deps = [d for d in all_deps if not d.is_detected]
        existing_deps = [d for d in all_deps if d.is_detected]

        return {
            'status': 'success',
            'dag_id': dag_id,
            'total_dependencies': len(all_deps),
            'new_dependencies': len(new_deps),
            'existing_dependencies': len(existing_deps),
            'new_edges': [
                {
                    'from': d.upstream_task_id,
                    'to': d.downstream_task_id,
                    'type': d.dependency_type,
                    'created_at': str(d.created_at),
                }
                for d in new_deps
            ],
        }

    except Exception as e:
        logger.error(f"Error getting incremental changes for {dag_id}: {e}")
        return {'status': 'error', 'error': str(e)}
    finally:
        session.close()


@shared_task(bind=True, name='scripts.dependency.add_dependency')
def add_dependency(self, dag_id, upstream_task_id, downstream_task_id, dependency_type='all_success', **kwargs):
    logger.info(f"Adding dependency: {upstream_task_id} -> {downstream_task_id} in {dag_id}")
    session = get_db_session()
    try:
        existing = session.query(TaskDependency).filter_by(
            dag_id=dag_id,
            upstream_task_id=upstream_task_id,
            downstream_task_id=downstream_task_id,
        ).first()

        if existing:
            logger.warning(f"Dependency already exists: {upstream_task_id} -> {downstream_task_id}")
            return {'status': 'already_exists', 'dep_id': existing.id}

        dep = TaskDependency(
            dag_id=dag_id,
            upstream_task_id=upstream_task_id,
            downstream_task_id=downstream_task_id,
            dependency_type=dependency_type,
            is_detected=False,
            detected_at=None,
            source='MANUAL',
        )
        session.add(dep)
        session.commit()

        logger.info(f"Dependency added: {upstream_task_id} -> {downstream_task_id}, will be detected incrementally")
        return {'status': 'added', 'dep_id': dep.id}

    except Exception as e:
        logger.error(f"Error adding dependency: {e}")
        session.rollback()
        return {'status': 'error', 'error': str(e)}
    finally:
        session.close()
