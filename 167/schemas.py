from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import Optional, List, Dict, Any
import re


class TaskBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    task_type: str = Field(..., pattern="^(shell|python)$")
    script_content: str
    cron_expression: str
    timeout: Optional[int] = Field(300, ge=1, le=3600)
    
    retry_count: Optional[int] = Field(0, ge=0, le=10)
    retry_delay: Optional[int] = Field(60, ge=1, le=3600)
    
    webhook_url: Optional[str] = Field(None, max_length=500)
    webhook_method: Optional[str] = Field("POST", pattern="^(GET|POST|PUT|PATCH)$")
    webhook_headers: Optional[Dict[str, str]] = None
    
    is_active: Optional[bool] = True

    @field_validator('cron_expression')
    @classmethod
    def validate_cron_expression(cls, v):
        parts = v.strip().split()
        if len(parts) != 6:
            raise ValueError('Cron expression must have exactly 6 fields (second minute hour day month weekday)')
        
        patterns = [
            r'^(\*|([0-5]?\d)(-[0-5]?\d)?(,([0-5]?\d)(-[0-5]?\d)?)*)(/\d+)?$',
            r'^(\*|([0-5]?\d)(-[0-5]?\d)?(,([0-5]?\d)(-[0-5]?\d)?)*)(/\d+)?$',
            r'^(\*|([01]?\d|2[0-3])(-([01]?\d|2[0-3]))?(,([01]?\d|2[0-3])(-([01]?\d|2[0-3]))?)*)(/\d+)?$',
            r'^(\*|([1-9]|[12]\d|3[01])(-([1-9]|[12]\d|3[01]))?(,([1-9]|[12]\d|3[01])(-([1-9]|[12]\d|3[01]))?)*)(/\d+)?$',
            r'^(\*|(1[0-2]|[1-9])(-(1[0-2]|[1-9]))?(,(1[0-2]|[1-9])(-(1[0-2]|[1-9]))?)*)(/\d+)?$',
            r'^(\*|[0-6])(-[0-6])?(,([0-6])(-[0-6])?)*$'
        ]
        
        for i, (part, pattern) in enumerate(zip(parts, patterns)):
            if not re.match(pattern, part):
                field_names = ['second', 'minute', 'hour', 'day', 'month', 'weekday']
                raise ValueError(f'Invalid {field_names[i]} field in cron expression')
        
        return v


class TaskCreate(TaskBase):
    dependency_ids: Optional[List[int]] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    task_type: Optional[str] = Field(None, pattern="^(shell|python)$")
    script_content: Optional[str] = None
    cron_expression: Optional[str] = None
    timeout: Optional[int] = Field(None, ge=1, le=3600)
    
    retry_count: Optional[int] = Field(None, ge=0, le=10)
    retry_delay: Optional[int] = Field(None, ge=1, le=3600)
    
    webhook_url: Optional[str] = Field(None, max_length=500)
    webhook_method: Optional[str] = Field(None, pattern="^(GET|POST|PUT|PATCH)$")
    webhook_headers: Optional[Dict[str, str]] = None
    
    is_active: Optional[bool] = None

    @field_validator('cron_expression')
    @classmethod
    def validate_cron_expression(cls, v):
        if v is None:
            return v
        parts = v.strip().split()
        if len(parts) != 6:
            raise ValueError('Cron expression must have exactly 6 fields (second minute hour day month weekday)')
        
        patterns = [
            r'^(\*|([0-5]?\d)(-[0-5]?\d)?(,([0-5]?\d)(-[0-5]?\d)?)*)(/\d+)?$',
            r'^(\*|([0-5]?\d)(-[0-5]?\d)?(,([0-5]?\d)(-[0-5]?\d)?)*)(/\d+)?$',
            r'^(\*|([01]?\d|2[0-3])(-([01]?\d|2[0-3]))?(,([01]?\d|2[0-3])(-([01]?\d|2[0-3]))?)*)(/\d+)?$',
            r'^(\*|([1-9]|[12]\d|3[01])(-([1-9]|[12]\d|3[01]))?(,([1-9]|[12]\d|3[01])(-([1-9]|[12]\d|3[01]))?)*)(/\d+)?$',
            r'^(\*|(1[0-2]|[1-9])(-(1[0-2]|[1-9]))?(,(1[0-2]|[1-9])(-(1[0-2]|[1-9]))?)*)(/\d+)?$',
            r'^(\*|[0-6])(-[0-6])?(,([0-6])(-[0-6])?)*$'
        ]
        
        for i, (part, pattern) in enumerate(zip(parts, patterns)):
            if not re.match(pattern, part):
                field_names = ['second', 'minute', 'hour', 'day', 'month', 'weekday']
                raise ValueError(f'Invalid {field_names[i]} field in cron expression')
        
        return v


class TaskDependency(BaseModel):
    task_id: int
    depends_on_task_id: int

    class Config:
        from_attributes = True


class Task(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    dependency_ids: List[int] = []

    class Config:
        from_attributes = True


class TaskLogBase(BaseModel):
    task_id: int
    status: str
    output: Optional[str] = None
    error: Optional[str] = None


class TaskLogCreate(TaskLogBase):
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: Optional[int] = None
    retry_attempt: Optional[int] = 0
    triggered_by: Optional[int] = None


class TaskLog(TaskLogBase):
    id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_time: Optional[int] = None
    retry_attempt: int
    triggered_by: Optional[int] = None

    class Config:
        from_attributes = True


class TaskWithLogs(Task):
    logs: List[TaskLog] = []


class TaskExecuteRequest(BaseModel):
    task_id: int


class WebhookTestRequest(BaseModel):
    url: str
    method: Optional[str] = "POST"
    headers: Optional[Dict[str, Any]] = None