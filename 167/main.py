from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List
import uvicorn

from database import engine, get_db, Base
import models
import schemas
import crud
from scheduler import scheduler_manager
from executor import TaskExecutor
from webhook import WebhookNotifier

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Scheduler API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def enrich_task_with_dependencies(task, db: Session):
    deps = crud.get_task_dependencies(db, task.id)
    task.dependency_ids = [d.depends_on_task_id for d in deps]
    return task


@app.on_event("startup")
def startup_event():
    scheduler_manager.start()
    scheduler_manager.load_tasks_from_db()
    scheduler_manager.add_log_cleanup_job()


@app.on_event("shutdown")
def shutdown_event():
    scheduler_manager.shutdown()


@app.post("/tasks/", response_model=schemas.Task)
def create_task(task: schemas.TaskCreate, db: Session = Depends(get_db)):
    db_task = crud.create_task(db, task)
    if db_task.is_active:
        scheduler_manager.add_task(db_task.id, db_task.cron_expression)
    return enrich_task_with_dependencies(db_task, db)


@app.get("/tasks/", response_model=List[schemas.Task])
def read_tasks(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    tasks = crud.get_tasks(db, skip=skip, limit=limit)
    return [enrich_task_with_dependencies(task, db) for task in tasks]


@app.get("/tasks/{task_id}", response_model=schemas.TaskWithLogs)
def read_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return enrich_task_with_dependencies(db_task, db)


@app.put("/tasks/{task_id}", response_model=schemas.Task)
def update_task(task_id: int, task: schemas.TaskUpdate, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    updated_task = crud.update_task(db, task_id, task)

    if task.is_active is not None:
        if task.is_active:
            scheduler_manager.add_task(updated_task.id, updated_task.cron_expression)
        else:
            scheduler_manager.remove_task(task_id)
    elif task.cron_expression is not None and updated_task.is_active:
        scheduler_manager.add_task(updated_task.id, updated_task.cron_expression)

    return enrich_task_with_dependencies(updated_task, db)


@app.delete("/tasks/{task_id}")
def delete_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    scheduler_manager.remove_task(task_id)
    crud.delete_task(db, task_id)
    return {"message": "Task deleted successfully"}


@app.post("/tasks/{task_id}/dependencies/{depends_on_id}")
def add_task_dependency(task_id: int, depends_on_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    db_dep = crud.get_task(db, depends_on_id)
    if db_dep is None:
        raise HTTPException(status_code=404, detail="Dependency task not found")
    
    try:
        crud.add_dependency(db, task_id, depends_on_id)
        return {"message": f"Dependency added: task {task_id} depends on {depends_on_id}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/tasks/{task_id}/dependencies/{depends_on_id}")
def remove_task_dependency(task_id: int, depends_on_id: int, db: Session = Depends(get_db)):
    crud.remove_dependency(db, task_id, depends_on_id)
    return {"message": f"Dependency removed: task {task_id} no longer depends on {depends_on_id}"}


@app.get("/tasks/{task_id}/dependencies")
def get_task_dependencies(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    deps = crud.get_task_dependencies(db, task_id)
    return {
        "task_id": task_id,
        "dependencies": [
            {"task_id": d.depends_on_task_id, "created_at": d.created_at}
            for d in deps
        ]
    }


@app.get("/tasks/{task_id}/dependents")
def get_task_dependents(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    
    dependents = crud.get_dependent_tasks(db, task_id)
    return {
        "task_id": task_id,
        "dependents": [
            {"task_id": d.task_id, "created_at": d.created_at}
            for d in dependents
        ]
    }


@app.post("/tasks/{task_id}/execute")
def execute_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    scheduler_manager.schedule_immediate_execution(task_id)
    return {
        "task_id": task_id,
        "message": "Task execution scheduled",
        "task_name": db_task.name
    }


@app.post("/webhook/test")
async def test_webhook(request: schemas.WebhookTestRequest):
    success, response = await WebhookNotifier.send_notification(
        url=request.url,
        method=request.method,
        headers=request.headers,
        payload={"test": True, "message": "Webhook test from Task Scheduler"}
    )
    return {
        "success": success,
        "response": response
    }


@app.post("/logs/cleanup")
def cleanup_logs(db: Session = Depends(get_db)):
    from crud import cleanup_old_logs
    cleanup_old_logs(db)
    return {"message": "Log cleanup performed successfully"}


@app.get("/logs/stats")
def get_log_stats(db: Session = Depends(get_db)):
    from sqlalchemy import func
    total_logs = db.query(func.count(models.TaskLog.id)).scalar()
    success_logs = db.query(func.count(models.TaskLog.id)).filter(
        models.TaskLog.status == "success"
    ).scalar()
    failed_logs = db.query(func.count(models.TaskLog.id)).filter(
        models.TaskLog.status == "failed"
    ).scalar()
    
    return {
        "total_logs": total_logs,
        "success_logs": success_logs,
        "failed_logs": failed_logs,
        "success_rate": round(success_logs / total_logs * 100, 2) if total_logs > 0 else 0
    }


@app.post("/tasks/{task_id}/pause")
def pause_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    scheduler_manager.pause_task(task_id)
    return {"message": f"Task {task_id} paused"}


@app.post("/tasks/{task_id}/resume")
def resume_task(task_id: int, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    scheduler_manager.resume_task(task_id)
    return {"message": f"Task {task_id} resumed"}


@app.get("/logs/", response_model=List[schemas.TaskLog])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logs = crud.get_all_logs(db, skip=skip, limit=limit)
    return logs


@app.get("/tasks/{task_id}/logs/", response_model=List[schemas.TaskLog])
def read_task_logs(task_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    db_task = crud.get_task(db, task_id)
    if db_task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    logs = crud.get_task_logs(db, task_id, skip=skip, limit=limit)
    return logs


@app.get("/scheduler/jobs")
def get_scheduler_jobs():
    jobs = scheduler_manager.get_jobs()
    return {
        "jobs": [
            {
                "id": job.id,
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)