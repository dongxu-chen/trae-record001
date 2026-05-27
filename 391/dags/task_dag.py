from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
import importlib
import json

default_args = {
    'owner': 'admin',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(seconds=60),
    'execution_timeout': timedelta(hours=2),
}


def execute_celery_task(task_module, task_function, dag_id, run_id, task_id, **context):
    queue_map = {
        'extract_data': 'etl',
        'transform_data': 'etl',
        'load_data': 'etl',
        'generate_daily_report': 'report',
        'generate_weekly_report': 'report',
        'send_report_notification': 'report',
        'prepare_training_data': 'ml',
        'train_model': 'ml',
        'evaluate_model': 'ml',
        'deploy_model': 'ml',
    }

    task_params = {
        'dag_id': dag_id,
        'run_id': str(run_id),
        'task_id': task_id,
        'execution_date': str(context['execution_date']),
    }

    module = importlib.import_module(task_module)
    task_func = getattr(module, task_function)
    result = task_func(**task_params)

    context['ti'].xcom_push(key=f'{task_id}_result', value=result)
    return result


def incremental_dependency_check(dag_id, **context):
    from models.task_model import get_db_session, TaskDependency, TaskDefinition
    from datetime import datetime

    session = get_db_session()
    try:
        new_deps = session.query(TaskDependency).filter_by(
            dag_id=dag_id,
            is_detected=False,
        ).all()

        detected = []
        for dep in new_deps:
            upstream = session.query(TaskDefinition).filter_by(task_id=dep.upstream_task_id).first()
            downstream = session.query(TaskDefinition).filter_by(task_id=dep.downstream_task_id).first()
            if upstream and downstream:
                dep.is_detected = True
                dep.detected_at = datetime.now()
                dep.source = 'INCREMENTAL_CHECK'
                detected.append(f'{dep.upstream_task_id} -> {dep.downstream_task_id}')

        session.commit()

        all_deps = session.query(TaskDependency).filter_by(dag_id=dag_id, is_detected=True).all()

        from collections import defaultdict
        adj = defaultdict(list)
        in_degree = defaultdict(int)
        task_ids = set()

        for dep in all_deps:
            adj[dep.upstream_task_id].append(dep.downstream_task_id)
            in_degree[dep.downstream_task_id] += 1
            task_ids.add(dep.upstream_task_id)
            task_ids.add(dep.downstream_task_id)

        queue = [t for t in task_ids if in_degree[t] == 0]
        visited = 0

        while queue:
            node = queue.pop(0)
            visited += 1
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        has_cycle = visited != len(task_ids)

        if has_cycle:
            cycle_tasks = [t for t in task_ids if in_degree[t] > 0]
            raise Exception(f"Cycle detected in DAG {dag_id}: {cycle_tasks}")

        ti = context['ti']
        task_results = {}
        for task_instance in context.get('dag_run').get_task_instances():
            if task_instance.task_id != ti.task_id:
                try:
                    result = ti.xcom_pull(task_ids=task_instance.task_id, key=f'{task_instance.task_id}_result')
                    task_results[task_instance.task_id] = result
                    if dep.dependency_type == 'all_success':
                        if not result or result.get('status') != 'success':
                            raise Exception(
                                f"Task {task_instance.task_id} did not succeed (status: "
                                f"{result.get('status') if result else 'None'}), "
                                f"stopping downstream tasks"
                            )
                except Exception as e:
                    if 'stopping downstream' in str(e):
                        raise
                    pass

        return {
            'newly_detected': len(detected),
            'detected_edges': detected,
            'task_results': task_results,
        }

    finally:
        session.close()


with DAG(
    dag_id='etl_data_pipeline',
    default_args=default_args,
    description='ETL数据处理管道 - 抽取→转换→加载→日报 (增量依赖检测)',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['etl', 'data', 'incremental'],
) as etl_dag:

    extract_task = PythonOperator(
        task_id='extract_data',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.etl',
            'task_function': 'extract_data',
            'dag_id': 'etl_data_pipeline',
            'task_id': 'extract_data',
        },
        provide_context=True,
    )

    transform_task = PythonOperator(
        task_id='transform_data',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.etl',
            'task_function': 'transform_data',
            'dag_id': 'etl_data_pipeline',
            'task_id': 'transform_data',
        },
        provide_context=True,
    )

    load_task = PythonOperator(
        task_id='load_data',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.etl',
            'task_function': 'load_data',
            'dag_id': 'etl_data_pipeline',
            'task_id': 'load_data',
        },
        provide_context=True,
    )

    trigger_report = TriggerDagRunOperator(
        task_id='trigger_report_generation',
        trigger_dag_id='report_generation',
        conf={'source_dag': 'etl_data_pipeline', 'source_run_id': '{{ run_id }}'},
        wait_for_completion=False,
    )

    incremental_check = PythonOperator(
        task_id='incremental_dependency_check',
        python_callable=incremental_dependency_check,
        op_kwargs={'dag_id': 'etl_data_pipeline'},
        provide_context=True,
    )

    extract_task >> transform_task >> load_task >> incremental_check >> trigger_report


with DAG(
    dag_id='report_generation',
    default_args=default_args,
    description='报表生成流水线 - 生成日报→周报→通知 (增量依赖检测)',
    schedule_interval='@daily',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['report', 'analytics', 'incremental'],
) as report_dag:

    generate_daily = PythonOperator(
        task_id='generate_daily_report',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.report',
            'task_function': 'generate_daily_report',
            'dag_id': 'report_generation',
            'task_id': 'generate_daily_report',
        },
        provide_context=True,
    )

    generate_weekly = PythonOperator(
        task_id='generate_weekly_report',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.report',
            'task_function': 'generate_weekly_report',
            'dag_id': 'report_generation',
            'task_id': 'generate_weekly_report',
        },
        provide_context=True,
    )

    send_notification = PythonOperator(
        task_id='send_report_notification',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.report',
            'task_function': 'send_report_notification',
            'dag_id': 'report_generation',
            'task_id': 'send_report_notification',
        },
        provide_context=True,
    )

    incremental_check = PythonOperator(
        task_id='incremental_dependency_check',
        python_callable=incremental_dependency_check,
        op_kwargs={'dag_id': 'report_generation'},
        provide_context=True,
    )

    generate_daily >> generate_weekly >> incremental_check >> send_notification


with DAG(
    dag_id='ml_training_pipeline',
    default_args=default_args,
    description='ML模型训练流水线 - 数据准备→训练→评估→部署 (增量依赖检测)',
    schedule_interval='@weekly',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['ml', 'training', 'incremental'],
) as ml_dag:

    prepare_data = PythonOperator(
        task_id='prepare_training_data',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.ml',
            'task_function': 'prepare_training_data',
            'dag_id': 'ml_training_pipeline',
            'task_id': 'prepare_training_data',
        },
        provide_context=True,
    )

    train = PythonOperator(
        task_id='train_model',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.ml',
            'task_function': 'train_model',
            'dag_id': 'ml_training_pipeline',
            'task_id': 'train_model',
        },
        provide_context=True,
    )

    evaluate = PythonOperator(
        task_id='evaluate_model',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.ml',
            'task_function': 'evaluate_model',
            'dag_id': 'ml_training_pipeline',
            'task_id': 'evaluate_model',
        },
        provide_context=True,
    )

    deploy = PythonOperator(
        task_id='deploy_model',
        python_callable=execute_celery_task,
        op_kwargs={
            'task_module': 'celery_app.tasks.ml',
            'task_function': 'deploy_model',
            'dag_id': 'ml_training_pipeline',
            'task_id': 'deploy_model',
        },
        provide_context=True,
    )

    incremental_check = PythonOperator(
        task_id='incremental_dependency_check',
        python_callable=incremental_dependency_check,
        op_kwargs={'dag_id': 'ml_training_pipeline'},
        provide_context=True,
    )

    prepare_data >> train >> evaluate >> incremental_check >> deploy


with DAG(
    dag_id='dependency_detection_job',
    default_args=default_args,
    description='增量依赖检测定时任务 - 每小时检测新增依赖关系',
    schedule_interval='@hourly',
    start_date=datetime(2024, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=['system', 'dependency', 'incremental'],
) as detection_dag:

    def detect_all_new_dependencies(**context):
        from scripts.dependency_detector import detect_new_dependencies, validate_dag_graph
        from models.task_model import get_db_session, DAGDefinition

        session = get_db_session()
        try:
            dags = session.query(DAGDefinition).filter_by(enabled=True).all()
            results = []
            for dag in dags:
                r = detect_new_dependencies(dag_id=dag.dag_id)
                v = validate_dag_graph(dag_id=dag.dag_id)
                results.append({
                    'dag_id': dag.dag_id,
                    'detection': r,
                    'validation': v,
                })
            return results
        finally:
            session.close()

    detect_task = PythonOperator(
        task_id='detect_new_dependencies',
        python_callable=detect_all_new_dependencies,
        provide_context=True,
    )
