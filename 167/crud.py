from sqlalchemy.orm import Session
from datetime import datetime
import models
import schemas
from log_rotation import LogRotationManager


def get_task(db: Session, task_id: int):
    return db.query(models.Task).filter(models.Task.id == task_id).first()


def get_tasks(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Task).order_by(models.Task.created_at.desc()).offset(skip).limit(limit).all()


def get_task_dependencies(db: Session, task_id: int):
    return db.query(models.TaskDependency).filter(
        models.TaskDependency.task_id == task_id
    ).all()


def get_dependent_tasks(db: Session, task_id: int):
    return db.query(models.TaskDependency).filter(
        models.TaskDependency.depends_on_task_id == task_id
    ).all()


def add_dependency(db: Session, task_id: int, depends_on_task_id: int):
    if task_id == depends_on_task_id:
        raise ValueError("Task cannot depend on itself")
    
    existing = db.query(models.TaskDependency).filter(
        models.TaskDependency.task_id == task_id,
        models.TaskDependency.depends_on_task_id == depends_on_task_id
    ).first()
    
    if existing:
        return existing
    
    dependency = models.TaskDependency(
        task_id=task_id,
        depends_on_task_id=depends_on_task_id
    )
    db.add(dependency)
    db.commit()
    db.refresh(dependency)
    return dependency


def remove_dependency(db: Session, task_id: int, depends_on_task_id: int):
    dependency = db.query(models.TaskDependency).filter(
        models.TaskDependency.task_id == task_id,
        models.TaskDependency.depends_on_task_id == depends_on_task_id
    ).first()
    
    if dependency:
        db.delete(dependency)
        db.commit()
    return dependency


def check_dependencies_met(db: Session, task_id: int) -> tuple[bool, list[int]]:
    dependencies = get_task_dependencies(db, task_id)
    failed_deps = []
    
    for dep in dependencies:
        latest_log = db.query(models.TaskLog).filter(
            models.TaskLog.task_id == dep.depends_on_task_id,
            models.TaskLog.status.in_(["success", "failed"])
        ).order_by(models.TaskLog.completed_at.desc()).first()
        
        if not latest_log or latest_log.status != "success":
            failed_deps.append(dep.depends_on_task_id)
    
    return len(failed_deps) == 0, failed_deps


def create_task(db: Session, task: schemas.TaskCreate):
    task_data = task.model_dump()
    dependency_ids = task_data.pop('dependency_ids', [])
    
    db_task = models.Task(**task_data)
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    
    for dep_id in dependency_ids:
        if dep_id != db_task.id:
            try:
                add_dependency(db, db_task.id, dep_id)
            except:
                pass
    
    return db_task


def update_task(db: Session, task_id: int, task: schemas.TaskUpdate):
    db_task = get_task(db, task_id)
    if db_task:
        update_data = task.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(db_task, key, value)
        db_task.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(db_task)
    return db_task


def delete_task(db: Session, task_id: int):
    db_task = get_task(db, task_id)
    if db_task:
        db.delete(db_task)
        db.commit()
    return db_task


def create_task_log(db: Session, log: schemas.TaskLogCreate):
    db_log = models.TaskLog(**log.model_dump())
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    LogRotationManager.on_log_created(db, log.task_id)
    return db_log


def get_task_logs(db: Session, task_id: int, skip: int = 0, limit: int = 100):
    return db.query(models.TaskLog).filter(models.TaskLog.task_id == task_id).order_by(
        models.TaskLog.started_at.desc()).offset(skip).limit(limit).all()


def get_all_logs(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.TaskLog).order_by(models.TaskLog.started_at.desc()).offset(skip).limit(limit).all()


def update_task_log(db: Session, log_id: int, **kwargs):
    db_log = db.query(models.TaskLog).filter(models.TaskLog.id == log_id).first()
    if db_log:
        for key, value in kwargs.items():
            setattr(db_log, key, value)
        db.commit()
        db.refresh(db_log)
    return db_log


def cleanup_old_logs(db: Session):
    LogRotationManager.rotate_all_logs(db)
    db.commit()