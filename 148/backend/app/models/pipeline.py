from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    flow_config = Column(JSON, nullable=False)
    quality_rules = Column(JSON)  # 新增：数据质量规则JSON配置
    max_concurrent_tasks = Column(Integer, default=4)  # 新增：最大并发任务数
    checkpoint_storage = Column(String(50), default="database")  # 新增：checkpoint存储类型
    s3_config = Column(JSON)  # 新增：S3存储配置
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    executions = relationship("PipelineExecution", back_populates="pipeline", cascade="all, delete-orphan")
    quality_rule_definitions = relationship("DataQualityRule", back_populates="pipeline", cascade="all, delete-orphan")


class PipelineExecution(Base):
    __tablename__ = "pipeline_executions"

    id = Column(Integer, primary_key=True, index=True)
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"))
    flow_run_id = Column(String(255), unique=True)
    status = Column(String(50), default="PENDING")
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)
    checkpoint_data = Column(JSON)
    error_message = Column(Text)
    resume_count = Column(Integer, default=0)  # 新增：续跑次数
    last_resume_time = Column(DateTime)  # 新增：上次续跑时间

    pipeline = relationship("Pipeline", back_populates="executions")
    task_executions = relationship("TaskExecution", back_populates="pipeline_execution", cascade="all, delete-orphan")
    quality_results = relationship("DataQualityResult", back_populates="execution", cascade="all, delete-orphan")


class TaskExecution(Base):
    __tablename__ = "task_executions"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(Integer, ForeignKey("pipeline_executions.id"))
    task_name = Column(String(255), nullable=False)
    status = Column(String(50), default="PENDING")
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    result_data = Column(JSON)
    error_message = Column(Text)
    checkpoint_saved = Column(Boolean, default=False)  # 新增：是否已保存checkpoint

    pipeline_execution = relationship("PipelineExecution", back_populates="task_executions")


class DataQualityRule(Base):
    __tablename__ = "data_quality_rules"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    rule_type = Column(String(50), nullable=False)
    config = Column(JSON, nullable=False)  # JSON配置
    pipeline_id = Column(Integer, ForeignKey("pipelines.id"))
    severity = Column(String(20), default="error")  # 严重级别: warning, error
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    pipeline = relationship("Pipeline", back_populates="quality_rule_definitions")
    results = relationship("DataQualityResult", back_populates="rule")


class DataQualityResult(Base):
    __tablename__ = "data_quality_results"

    id = Column(Integer, primary_key=True, index=True)
    rule_id = Column(Integer, ForeignKey("data_quality_rules.id"))
    execution_id = Column(Integer, ForeignKey("pipeline_executions.id"))
    success = Column(Boolean)
    details = Column(JSON)
    executed_at = Column(DateTime, default=datetime.utcnow)

    rule = relationship("DataQualityRule", back_populates="results")
    execution = relationship("PipelineExecution", back_populates="quality_results")
