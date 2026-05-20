from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class TaskDependency(Base):
    __tablename__ = "task_dependencies"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), index=True)
    depends_on_task_id = Column(Integer, ForeignKey("tasks.id"), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True)
    description = Column(Text, nullable=True)
    task_type = Column(String(20))
    script_content = Column(Text)
    cron_expression = Column(String(100))
    timeout = Column(Integer, default=300)
    
    retry_count = Column(Integer, default=0)
    retry_delay = Column(Integer, default=60)
    
    webhook_url = Column(String(500), nullable=True)
    webhook_method = Column(String(10), default="POST")
    webhook_headers = Column(JSON, nullable=True)
    
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    logs = relationship("TaskLog", back_populates="task", cascade="all, delete-orphan")
    dependencies = relationship(
        "Task",
        secondary="task_dependencies",
        primaryjoin="Task.id==TaskDependency.task_id",
        secondaryjoin="Task.id==TaskDependency.depends_on_task_id",
        backref="dependent_tasks"
    )


class TaskLog(Base):
    __tablename__ = "task_logs"

    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    status = Column(String(20))
    output = Column(Text)
    error = Column(Text)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    execution_time = Column(Integer, nullable=True)
    retry_attempt = Column(Integer, default=0)
    triggered_by = Column(Integer, nullable=True)

    task = relationship("Task", back_populates="logs")