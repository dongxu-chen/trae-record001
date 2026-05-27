from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, JSON, BigInteger, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os

Base = declarative_base()

DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'mysql+pymysql://scheduler:scheduler123@localhost:3306/task_scheduler'
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TaskDefinition(Base):
    __tablename__ = 'task_definitions'

    task_id = Column(String(128), primary_key=True)
    task_name = Column(String(256), nullable=False)
    task_type = Column(String(64), nullable=False, default='celery')
    task_module = Column(String(512), nullable=False)
    task_function = Column(String(128), nullable=False)
    description = Column(Text, nullable=True)
    queue = Column(String(64), nullable=False, default='celery')
    priority = Column(Integer, nullable=False, default=5)
    max_retries = Column(Integer, nullable=False, default=3)
    retry_delay_sec = Column(Integer, nullable=False, default=60)
    retry_backoff = Column(Boolean, nullable=False, default=True)
    retry_backoff_max_sec = Column(Integer, nullable=False, default=3600)
    timeout_sec = Column(Integer, nullable=False, default=3600)
    enabled = Column(Boolean, nullable=False, default=True)
    resource_profile = Column(String(32), nullable=False, default='MEDIUM')
    estimated_cpu_percent = Column(Float, nullable=False, default=20.0)
    estimated_memory_mb = Column(Integer, nullable=False, default=512)
    estimated_duration_sec = Column(Integer, nullable=False, default=300)
    business_criticality = Column(String(16), nullable=False, default='MEDIUM')
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class TaskDependency(Base):
    __tablename__ = 'task_dependencies'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    dag_id = Column(String(128), nullable=False)
    upstream_task_id = Column(String(128), nullable=False)
    downstream_task_id = Column(String(128), nullable=False)
    dependency_type = Column(String(32), nullable=False, default='all_success')
    is_detected = Column(Boolean, nullable=False, default=False)
    detected_at = Column(DateTime, nullable=True)
    source = Column(String(32), nullable=False, default='MANUAL')
    created_at = Column(DateTime, nullable=False)


class DAGDefinition(Base):
    __tablename__ = 'dag_definitions'

    dag_id = Column(String(128), primary_key=True)
    dag_name = Column(String(256), nullable=False)
    description = Column(Text, nullable=True)
    schedule_interval = Column(String(64), nullable=False, default='@daily')
    owner = Column(String(64), nullable=False, default='admin')
    enabled = Column(Boolean, nullable=False, default=True)
    max_active_runs = Column(Integer, nullable=False, default=1)
    catchup = Column(Boolean, nullable=False, default=False)
    tags = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class TaskExecutionLog(Base):
    __tablename__ = 'task_execution_logs'

    log_id = Column(BigInteger, primary_key=True, autoincrement=True)
    dag_id = Column(String(128), nullable=False)
    task_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    celery_task_id = Column(String(128), nullable=True)
    execution_date = Column(DateTime, nullable=False)
    duration_sec = Column(Float, nullable=True)
    status = Column(String(32), nullable=False, default='PENDING')
    attempt = Column(Integer, nullable=False, default=1)
    worker_name = Column(String(128), nullable=True)
    input_params = Column(JSON, nullable=True)
    output_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, nullable=False, default=0)
    next_retry_time = Column(DateTime, nullable=True)
    is_dead_letter = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False)


class DeadLetterQueue(Base):
    __tablename__ = 'dead_letter_queue'

    dlq_id = Column(BigInteger, primary_key=True, autoincrement=True)
    celery_task_id = Column(String(128), nullable=False)
    dag_id = Column(String(128), nullable=False)
    task_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    task_module = Column(String(512), nullable=False)
    task_function = Column(String(128), nullable=False)
    input_params = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    total_retries = Column(Integer, nullable=False, default=0)
    original_queued_at = Column(DateTime, nullable=False)
    dead_lettered_at = Column(DateTime, nullable=False)
    ttl_seconds = Column(Integer, nullable=False, default=604800)
    expires_at = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default='PENDING')
    reprocessed_at = Column(DateTime, nullable=True)
    reprocessed_by = Column(String(64), nullable=True)
    notes = Column(Text, nullable=True)


class TaskRerunRecord(Base):
    __tablename__ = 'task_rerun_records'

    rerun_id = Column(BigInteger, primary_key=True, autoincrement=True)
    original_log_id = Column(BigInteger, nullable=False)
    original_celery_id = Column(String(128), nullable=False)
    dag_id = Column(String(128), nullable=False)
    task_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    rerun_type = Column(String(32), nullable=False, default='MANUAL')
    rerun_celery_id = Column(String(128), nullable=True)
    rerun_status = Column(String(32), nullable=False, default='PENDING')
    triggered_by = Column(String(64), nullable=False, default='system')
    triggered_at = Column(DateTime, nullable=False)


class WorkerNode(Base):
    __tablename__ = 'worker_nodes'

    worker_id = Column(String(128), primary_key=True)
    hostname = Column(String(256), nullable=False)
    queues = Column(String(512), nullable=False, default='celery')
    total_cpu_cores = Column(Integer, nullable=False, default=4)
    total_memory_mb = Column(Integer, nullable=False, default=8192)
    current_cpu_percent = Column(Float, nullable=False, default=0.0)
    current_memory_mb = Column(Integer, nullable=False, default=0)
    active_task_count = Column(Integer, nullable=False, default=0)
    max_concurrent_tasks = Column(Integer, nullable=False, default=8)
    status = Column(String(32), nullable=False, default='ONLINE')
    last_heartbeat = Column(DateTime, nullable=True)
    region = Column(String(64), nullable=True)
    labels = Column(String(512), nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)


class ResourceAllocation(Base):
    __tablename__ = 'resource_allocations'

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    celery_task_id = Column(String(128), nullable=False)
    dag_id = Column(String(128), nullable=False)
    task_id = Column(String(128), nullable=False)
    worker_id = Column(String(128), nullable=False)
    queue_name = Column(String(64), nullable=False)
    allocated_cpu_percent = Column(Float, nullable=False, default=0.0)
    allocated_memory_mb = Column(Integer, nullable=False, default=0)
    allocation_strategy = Column(String(32), nullable=False, default='SMART')
    decision_reason = Column(Text, nullable=True)
    allocation_time = Column(DateTime, nullable=False)
    release_time = Column(DateTime, nullable=True)
    status = Column(String(32), nullable=False, default='ALLOCATED')


class TaskLineage(Base):
    __tablename__ = 'task_lineage'

    lineage_id = Column(BigInteger, primary_key=True, autoincrement=True)
    dag_id = Column(String(128), nullable=False)
    task_id = Column(String(128), nullable=False)
    run_id = Column(String(128), nullable=False)
    source_dataset = Column(String(512), nullable=True)
    target_dataset = Column(String(512), nullable=True)
    transformation_type = Column(String(64), nullable=True)
    row_count = Column(BigInteger, nullable=True)
    data_hash = Column(String(128), nullable=True)
    parent_lineage_ids = Column(String(1024), nullable=True)
    execution_time = Column(DateTime, nullable=False)
    metadata = Column(JSON, nullable=True)


class ImpactAnalysis(Base):
    __tablename__ = 'impact_analyses'

    analysis_id = Column(BigInteger, primary_key=True, autoincrement=True)
    dag_id = Column(String(128), nullable=False)
    task_id = Column(String(128), nullable=False)
    analysis_type = Column(String(32), nullable=False, default='FAILURE_PREDICTION')
    failure_probability = Column(Float, nullable=False, default=0.0)
    affected_downstream_count = Column(Integer, nullable=False, default=0)
    affected_task_list = Column(Text, nullable=True)
    affected_dataset_list = Column(Text, nullable=True)
    estimated_recovery_minutes = Column(Integer, nullable=True)
    business_impact_level = Column(String(16), nullable=False, default='LOW')
    recommended_actions = Column(Text, nullable=True)
    analysis_time = Column(DateTime, nullable=False)
    metadata = Column(JSON, nullable=True)


class SchedulingDecision(Base):
    __tablename__ = 'scheduling_decisions'

    decision_id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(String(128), nullable=False)
    dag_id = Column(String(128), nullable=False)
    worker_id = Column(String(128), nullable=True)
    queue_name = Column(String(64), nullable=True)
    decision_type = Column(String(32), nullable=False, default='SCHEDULE')
    priority_score = Column(Float, nullable=False, default=0.0)
    resource_score = Column(Float, nullable=False, default=0.0)
    business_score = Column(Float, nullable=False, default=0.0)
    waiting_minutes = Column(Integer, nullable=False, default=0)
    reason = Column(Text, nullable=True)
    decision_time = Column(DateTime, nullable=False)
    status = Column(String(32), nullable=False, default='PENDING')


def get_db_session():
    return SessionLocal()
