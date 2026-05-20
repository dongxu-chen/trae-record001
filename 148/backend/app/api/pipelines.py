from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
import asyncio

from app.core.database import get_db
from app.models.pipeline import Pipeline, PipelineExecution, TaskExecution
from app.models.schemas import (
    PipelineCreate, PipelineUpdate, PipelineResponse,
    PipelineExecutionResponse, TaskExecutionResponse,
    PipelineRunRequest
)
from app.pipelines.executor import run_pipeline, validate_pipeline_dag

router = APIRouter(prefix="/api/pipelines", tags=["pipelines"])


@router.get("/", response_model=List[PipelineResponse])
def list_pipelines(db: Session = Depends(get_db)):
    return db.query(Pipeline).order_by(Pipeline.created_at.desc()).all()


@router.get("/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


@router.post("/", response_model=PipelineResponse)
def create_pipeline(pipeline: PipelineCreate, db: Session = Depends(get_db)):
    db_pipeline = Pipeline(
        name=pipeline.name,
        description=pipeline.description,
        flow_config=pipeline.flow_config
    )
    db.add(db_pipeline)
    db.commit()
    db.refresh(db_pipeline)
    return db_pipeline


@router.put("/{pipeline_id}", response_model=PipelineResponse)
def update_pipeline(pipeline_id: int, pipeline_update: PipelineUpdate, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    update_data = pipeline_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pipeline, key, value)

    pipeline.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pipeline)
    return pipeline


@router.delete("/{pipeline_id}")
def delete_pipeline(pipeline_id: int, db: Session = Depends(get_db)):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    db.delete(pipeline)
    db.commit()
    return {"message": "Pipeline deleted successfully"}


@router.post("/{pipeline_id}/validate-dag")
def validate_dag_endpoint(pipeline_id: int, db: Session = Depends(get_db)):
    """验证管道DAG是否有循环依赖"""
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    result = validate_pipeline_dag(pipeline.flow_config)
    return result


@router.post("/{pipeline_id}/run")
async def run_pipeline_endpoint(
    pipeline_id: int,
    run_request: PipelineRunRequest,
    db: Session = Depends(get_db)
):
    """运行管道，支持断点续跑"""
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # 验证DAG
    validation_result = validate_pipeline_dag(pipeline.flow_config)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"管道DAG存在循环依赖: {validation_result['cycle_nodes']}"
        )

    checkpoint_data = None
    resume_execution = None

    # 如果指定了断点续跑的执行ID
    if run_request.resume_from_checkpoint:
        resume_execution = db.query(PipelineExecution).filter(
            PipelineExecution.id == run_request.resume_from_checkpoint
        ).first()
        if resume_execution:
            checkpoint_data = resume_execution.checkpoint_data
            if resume_execution.status != "FAILED":
                raise HTTPException(
                    status_code=400,
                    detail="只有失败的执行才能进行断点续跑"
                )

    # 创建新的执行记录
    execution = PipelineExecution(
        pipeline_id=pipeline_id,
        status="RUNNING"
    )

    # 如果是续跑，更新续跑信息
    if resume_execution:
        execution.resume_count = resume_execution.resume_count + 1
        execution.last_resume_time = datetime.utcnow()

    db.add(execution)
    db.commit()
    db.refresh(execution)

    try:
        # 获取管道配置的并发设置
        max_concurrent = pipeline.max_concurrent_tasks or 4
        checkpoint_storage = pipeline.checkpoint_storage or "database"
        s3_config = pipeline.s3_config

        # 运行管道
        result = await run_pipeline(
            flow_config=pipeline.flow_config,
            checkpoint_data=checkpoint_data,
            max_concurrent_tasks=run_request.max_concurrent_tasks or max_concurrent,
            checkpoint_storage=checkpoint_storage,
            s3_config=s3_config,
            db=db,
            execution_id=execution.id
        )

        # 更新执行状态
        execution.flow_run_id = result.get("flow_run_id")
        execution.status = result.get("status", "COMPLETED")
        execution.end_time = datetime.utcnow()

        # 保存checkpoint数据
        if result.get("status") == "COMPLETED":
            execution.checkpoint_data = result.get("task_results", {})

        db.commit()

        return {
            "execution_id": execution.id,
            "flow_run_id": result.get("flow_run_id"),
            "status": result.get("status"),
            "topological_order": result.get("topological_order"),
            "resumed_from": run_request.resume_from_checkpoint
        }

    except Exception as e:
        execution.status = "FAILED"
        execution.error_message = str(e)
        execution.end_time = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/executions/{execution_id}/resume")
async def resume_execution(
    execution_id: int,
    db: Session = Depends(get_db)
):
    """从指定执行进行断点续跑"""
    execution = db.query(PipelineExecution).filter(
        PipelineExecution.id == execution_id
    ).first()

    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    if execution.status != "FAILED":
        raise HTTPException(
            status_code=400,
            detail="只有失败的执行才能进行断点续跑"
        )

    pipeline = db.query(Pipeline).filter(Pipeline.id == execution.pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    # 验证DAG
    validation_result = validate_pipeline_dag(pipeline.flow_config)
    if not validation_result["valid"]:
        raise HTTPException(
            status_code=400,
            detail=f"管道DAG存在循环依赖: {validation_result['cycle_nodes']}"
        )

    # 创建新的执行记录
    new_execution = PipelineExecution(
        pipeline_id=execution.pipeline_id,
        status="RUNNING",
        resume_count=execution.resume_count + 1,
        last_resume_time=datetime.utcnow()
    )
    db.add(new_execution)
    db.commit()
    db.refresh(new_execution)

    try:
        result = await run_pipeline(
            flow_config=pipeline.flow_config,
            checkpoint_data=execution.checkpoint_data,
            max_concurrent_tasks=pipeline.max_concurrent_tasks or 4,
            checkpoint_storage=pipeline.checkpoint_storage or "database",
            s3_config=pipeline.s3_config,
            db=db,
            execution_id=new_execution.id
        )

        new_execution.flow_run_id = result.get("flow_run_id")
        new_execution.status = result.get("status", "COMPLETED")
        new_execution.end_time = datetime.utcnow()

        if result.get("status") == "COMPLETED":
            new_execution.checkpoint_data = result.get("task_results", {})

        db.commit()

        return {
            "execution_id": new_execution.id,
            "flow_run_id": result.get("flow_run_id"),
            "status": result.get("status"),
            "resumed_from_execution": execution_id,
            "topological_order": result.get("topological_order")
        }

    except Exception as e:
        new_execution.status = "FAILED"
        new_execution.error_message = str(e)
        new_execution.end_time = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{pipeline_id}/executions", response_model=List[PipelineExecutionResponse])
def list_pipeline_executions(pipeline_id: int, db: Session = Depends(get_db)):
    return db.query(PipelineExecution).filter(
        PipelineExecution.pipeline_id == pipeline_id
    ).order_by(PipelineExecution.start_time.desc()).all()


@router.get("/executions/{execution_id}/tasks", response_model=List[TaskExecutionResponse])
def get_execution_tasks(execution_id: int, db: Session = Depends(get_db)):
    return db.query(TaskExecution).filter(
        TaskExecution.execution_id == execution_id
    ).order_by(TaskExecution.start_time).all()


@router.get("/executions/{execution_id}/checkpoint")
def get_checkpoint(execution_id: int, db: Session = Depends(get_db)):
    """获取执行的checkpoint数据"""
    execution = db.query(PipelineExecution).filter(
        PipelineExecution.id == execution_id
    ).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return {
        "execution_id": execution.id,
        "checkpoint_data": execution.checkpoint_data,
        "can_resume": execution.status == "FAILED",
        "resume_count": execution.resume_count,
        "completed_tasks": list(execution.checkpoint_data.keys()) if execution.checkpoint_data else []
    }


@router.post("/{pipeline_id}/configure")
def configure_pipeline(
    pipeline_id: int,
    config: dict,
    db: Session = Depends(get_db)
):
    """配置管道的高级选项（并发数、存储等）"""
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    if "max_concurrent_tasks" in config:
        pipeline.max_concurrent_tasks = config["max_concurrent_tasks"]
    if "checkpoint_storage" in config:
        pipeline.checkpoint_storage = config["checkpoint_storage"]
    if "s3_config" in config:
        pipeline.s3_config = config["s3_config"]
    if "quality_rules" in config:
        pipeline.quality_rules = config["quality_rules"]

    pipeline.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pipeline)

    return {
        "message": "配置更新成功",
        "pipeline_id": pipeline_id,
        "config": {
            "max_concurrent_tasks": pipeline.max_concurrent_tasks,
            "checkpoint_storage": pipeline.checkpoint_storage,
            "has_s3_config": pipeline.s3_config is not None,
            "has_quality_rules": pipeline.quality_rules is not None
        }
    }
