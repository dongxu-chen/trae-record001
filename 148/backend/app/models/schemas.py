from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any


class PipelineBase(BaseModel):
    name: str
    description: Optional[str] = None
    flow_config: Dict[str, Any]


class PipelineCreate(PipelineBase):
    pass


class PipelineUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    flow_config: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None
    quality_rules: Optional[Dict[str, Any]] = None
    max_concurrent_tasks: Optional[int] = None
    checkpoint_storage: Optional[str] = None
    s3_config: Optional[Dict[str, Any]] = None


class PipelineResponse(PipelineBase):
    id: int
    is_active: bool
    quality_rules: Optional[Dict[str, Any]] = None
    max_concurrent_tasks: Optional[int] = None
    checkpoint_storage: Optional[str] = None
    s3_config: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PipelineExecutionBase(BaseModel):
    pipeline_id: int
    status: str = "PENDING"


class PipelineExecutionResponse(BaseModel):
    id: int
    pipeline_id: int
    flow_run_id: Optional[str]
    status: str
    start_time: datetime
    end_time: Optional[datetime]
    error_message: Optional[str]
    resume_count: Optional[int] = 0
    last_resume_time: Optional[datetime] = None

    class Config:
        from_attributes = True


class TaskExecutionResponse(BaseModel):
    id: int
    task_name: str
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    result_data: Optional[Dict[str, Any]]
    error_message: Optional[str]
    checkpoint_saved: Optional[bool] = False

    class Config:
        from_attributes = True


class DataQualityRuleBase(BaseModel):
    name: str
    rule_type: str
    config: Dict[str, Any]
    pipeline_id: int
    severity: Optional[str] = "error"


class DataQualityRuleCreate(DataQualityRuleBase):
    pass


class DataQualityRuleResponse(DataQualityRuleBase):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class DataQualityResultResponse(BaseModel):
    id: int
    rule_id: int
    execution_id: int
    success: bool
    details: Dict[str, Any]
    executed_at: datetime

    class Config:
        from_attributes = True


class PipelineRunRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = None
    resume_from_checkpoint: Optional[int] = None
    max_concurrent_tasks: Optional[int] = None
