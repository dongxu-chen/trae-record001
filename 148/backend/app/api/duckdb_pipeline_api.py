"""
DuckDB + Ibis 流批一体 API
提供S3批处理、Kafka流处理、Parquet物化等功能的REST接口
"""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import logging

from app.pipelines.duckdb_ibis_engine import create_engine
from app.pipelines.connectors import (
    KafkaConfig, KafkaConnector,
    S3Config, S3Connector,
    ParquetMaterializer,
    DataFormat
)
from app.pipelines.duckdb_prefect_tasks import (
    s3_batch_pipeline_flow,
    kafka_streaming_pipeline_flow,
    stream_batch_unified_flow,
    execute_sql_task,
    transform_data_task,
    EngineManager
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/duckdb", tags=["duckdb-pipeline"])

# 存储运行中的任务状态
running_tasks: Dict[str, Dict[str, Any]] = {}


@router.get("/health")
async def health_check():
    """DuckDB引擎健康检查"""
    try:
        engine = create_engine()
        result = engine.execute_sql("SELECT 1 as health")
        return {
            "status": "healthy",
            "duckdb_connected": result.success,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables")
async def list_tables(db_path: str = ":memory:"):
    """列出所有表"""
    try:
        engine = create_engine(db_path=db_path)
        tables = engine.list_tables()
        return {
            "db_path": db_path,
            "tables": tables,
            "count": len(tables)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}")
async def get_table_info(table_name: str, db_path: str = ":memory:"):
    """获取表详细信息"""
    try:
        engine = create_engine(db_path=db_path)
        
        # 获取行数
        count_result = engine.execute_sql(f"SELECT COUNT(*) as count FROM {table_name}")
        row_count = count_result.data.iloc[0]['count'] if count_result.success else 0
        
        # 获取schema
        schema_result = engine.execute_sql(f"DESCRIBE {table_name}")
        schema = schema_result.data.to_dict('records') if schema_result.success else []
        
        # 获取样例数据
        sample_result = engine.execute_sql(f"SELECT * FROM {table_name} LIMIT 10")
        sample_data = sample_result.data.to_dict('records') if sample_result.success else []
        
        return {
            "table_name": table_name,
            "db_path": db_path,
            "row_count": row_count,
            "schema": schema,
            "sample_data": sample_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sql/execute")
async def execute_sql_endpoint(
    sql: str,
    db_path: str = ":memory:",
    output_table: Optional[str] = None
):
    """执行SQL查询"""
    try:
        engine = create_engine(db_path=db_path)
        result = engine.execute_sql(sql)
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error_message)
        
        if output_table and result.success:
            engine.create_table(output_table, result.data)
        
        return {
            "success": True,
            "sql": sql,
            "row_count": result.row_count,
            "execution_time_ms": result.execution_time_ms,
            "output_table": output_table,
            "preview": result.data.head(20).to_dict('records') if result.success else None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pipeline/s3-batch")
async def run_s3_batch_pipeline(
    s3_bucket: str,
    s3_prefix: str,
    source_format: str = "parquet",
    intermediate_table: str = "raw_data",
    target_table: str = "processed_data",
    output_path: str = "./output/result.parquet",
    db_path: str = ":memory:",
    group_by: Optional[List[str]] = None,
    aggregations: Optional[Dict[str, str]] = None,
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    运行S3批处理管道
    
    流程：S3 -> DuckDB -> 转换 -> Parquet物化
    """
    task_id = f"s3_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # 异步运行Prefect Flow
    def run_flow():
        try:
            running_tasks[task_id] = {
                "status": "running",
                "task_type": "s3_batch",
                "started_at": datetime.now().isoformat()
            }
            
            result = s3_batch_pipeline_flow(
                s3_bucket=s3_bucket,
                s3_prefix=s3_prefix,
                source_format=source_format,
                intermediate_table=intermediate_table,
                target_table=target_table,
                output_path=output_path,
                db_path=db_path,
                group_by=group_by or ["1"],
                aggregations=aggregations or {"count": "COUNT(*)"}
            )
            
            running_tasks[task_id] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat()
            }
        except Exception as e:
            running_tasks[task_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
    
    background_tasks.add_task(run_flow)
    
    return {
        "task_id": task_id,
        "status": "submitted",
        "pipeline_type": "s3_batch",
        "message": "S3 batch pipeline has been submitted"
    }


@router.post("/pipeline/kafka-streaming")
async def run_kafka_streaming_pipeline(
    bootstrap_servers: str,
    topics: List[str],
    raw_table: str = "kafka_raw_data",
    processed_table: str = "kafka_processed_data",
    output_path: str = "./output/kafka_result.parquet",
    max_messages: int = 1000,
    max_duration_seconds: int = 60,
    db_path: str = ":memory:",
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    运行Kafka流处理管道
    
    流程：Kafka -> DuckDB -> 转换 -> Parquet物化
    """
    task_id = f"kafka_streaming_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def run_flow():
        try:
            running_tasks[task_id] = {
                "status": "running",
                "task_type": "kafka_streaming",
                "started_at": datetime.now().isoformat()
            }
            
            result = kafka_streaming_pipeline_flow(
                bootstrap_servers=bootstrap_servers,
                kafka_topics=topics,
                raw_table=raw_table,
                processed_table=processed_table,
                output_path=output_path,
                max_messages=max_messages,
                max_duration_seconds=max_duration_seconds,
                db_path=db_path
            )
            
            running_tasks[task_id] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat()
            }
        except Exception as e:
            running_tasks[task_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
    
    background_tasks.add_task(run_flow)
    
    return {
        "task_id": task_id,
        "status": "submitted",
        "pipeline_type": "kafka_streaming",
        "message": "Kafka streaming pipeline has been submitted"
    }


@router.post("/pipeline/unified")
async def run_unified_pipeline(
    execution_mode: str = "batch",
    kafka_config: Optional[Dict[str, Any]] = None,
    s3_config: Optional[Dict[str, Any]] = None,
    db_path: str = ":memory:",
    background_tasks: BackgroundTasks = BackgroundTasks()
):
    """
    运行流批一体统一管道
    
    根据execution_mode自动选择：
    - batch: S3批处理
    - streaming: Kafka流处理
    """
    task_id = f"unified_{execution_mode}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    def run_flow():
        try:
            running_tasks[task_id] = {
                "status": "running",
                "task_type": f"unified_{execution_mode}",
                "started_at": datetime.now().isoformat()
            }
            
            result = stream_batch_unified_flow(
                execution_mode=execution_mode,
                kafka_config=kafka_config,
                s3_config=s3_config,
                db_path=db_path
            )
            
            running_tasks[task_id] = {
                "status": "completed",
                "result": result,
                "completed_at": datetime.now().isoformat()
            }
        except Exception as e:
            running_tasks[task_id] = {
                "status": "failed",
                "error": str(e),
                "failed_at": datetime.now().isoformat()
            }
    
    background_tasks.add_task(run_flow)
    
    return {
        "task_id": task_id,
        "status": "submitted",
        "pipeline_type": f"unified_{execution_mode}",
        "message": "Unified stream-batch pipeline has been submitted"
    }


@router.post("/s3/read")
async def read_from_s3(
    bucket: str,
    prefix: str,
    target_table: str,
    format: str = "parquet",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "us-east-1",
    endpoint: Optional[str] = None,
    db_path: str = ":memory:"
):
    """从S3读取数据到DuckDB"""
    try:
        engine = create_engine(db_path=db_path)
        
        config = S3Config(
            bucket=bucket,
            prefix=prefix,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint=endpoint
        )
        
        connector = S3Connector(engine, config)
        
        if format == "parquet":
            result = connector.read_parquet(target_table=target_table)
        elif format == "csv":
            result = connector.read_csv(target_table=target_table)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
        
        return {
            "success": result.get("success", False),
            "target_table": target_table,
            "row_count": result.get("row_count", 0),
            "s3_path": f"s3://{bucket}/{prefix}",
            "format": format
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/s3/write")
async def write_to_s3(
    source_table: str,
    bucket: str,
    output_prefix: str,
    format: str = "parquet",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "us-east-1",
    endpoint: Optional[str] = None,
    db_path: str = ":memory:",
    partition_by: Optional[List[str]] = None,
    compression: str = "snappy"
):
    """将DuckDB表写入S3"""
    try:
        engine = create_engine(db_path=db_path)
        
        config = S3Config(
            bucket=bucket,
            prefix=output_prefix,
            access_key=access_key,
            secret_key=secret_key,
            region=region,
            endpoint=endpoint
        )
        
        connector = S3Connector(engine, config)
        output_path = f"s3://{bucket}/{output_prefix}"
        
        result = connector.write_parquet(
            source_table=source_table,
            s3_path=output_path,
            partition_by=partition_by,
            compression=compression
        )
        
        return {
            "success": result.get("success", False),
            "source_table": source_table,
            "output_path": output_path,
            "partition_by": partition_by,
            "compression": compression
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/materialize/parquet")
async def materialize_to_parquet(
    source_table: str,
    output_path: str,
    db_path: str = ":memory:",
    partition_by: Optional[List[str]] = None,
    compression: str = "snappy",
    row_group_size: int = 100000
):
    """将DuckDB表物化为Parquet文件"""
    try:
        engine = create_engine(db_path=db_path)
        materializer = ParquetMaterializer(engine)
        
        is_s3_path = output_path.startswith("s3://")
        
        result = materializer.materialize_table(
            source_table=source_table,
            output_path=output_path,
            partition_by=partition_by,
            compression=compression,
            row_group_size=row_group_size
        )
        
        return {
            "success": result["success"],
            "source_table": source_table,
            "output_path": output_path,
            "is_s3_path": is_s3_path,
            "execution_time_ms": result.get("execution_time_ms", 0)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transform")
async def transform_data(
    source_table: str,
    target_table: str,
    transform_type: str = "aggregate",
    db_path: str = ":memory:",
    columns: Optional[List[str]] = None,
    where: Optional[str] = None,
    group_by: Optional[List[str]] = None,
    aggregations: Optional[Dict[str, str]] = None,
    join_table: Optional[str] = None,
    join_condition: Optional[str] = None,
    join_type: str = "inner"
):
    """
    数据转换（使用Prefect任务）
    
    支持的转换类型：select, filter, aggregate, join
    """
    try:
        result = transform_data_task(
            source_table=source_table,
            target_table=target_table,
            transform_type=transform_type,
            db_path=db_path,
            columns=columns,
            where=where,
            group_by=group_by,
            aggregations=aggregations,
            join_table=join_table,
            join_condition=join_condition,
            join_type=join_type
        )
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail=result.get("error"))
        
        return {
            "success": True,
            "source_table": source_table,
            "target_table": target_table,
            "transform_type": transform_type,
            "row_count": result["row_count"],
            "execution_time_ms": result["execution_time_ms"]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """获取任务状态"""
    if task_id not in running_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {
        "task_id": task_id,
        **running_tasks[task_id]
    }


@router.get("/tasks")
async def list_tasks():
    """列出所有运行的任务"""
    return {
        "total": len(running_tasks),
        "tasks": [
            {"task_id": tid, "status": tinfo["status"], "task_type": tinfo.get("task_type")}
            for tid, tinfo in running_tasks.items()
        ]
    }


@router.get("/examples")
async def get_examples():
    """获取使用示例配置"""
    return {
        "examples": {
            "s3_batch_pipeline": {
                "description": "S3批处理管道示例",
                "request": {
                    "s3_bucket": "my-data-bucket",
                    "s3_prefix": "raw/events/*.parquet",
                    "source_format": "parquet",
                    "group_by": ["date", "region"],
                    "aggregations": {
                        "total_events": "COUNT(*)",
                        "avg_value": "AVG(value)"
                    },
                    "output_path": "./output/result.parquet"
                }
            },
            "kafka_streaming_pipeline": {
                "description": "Kafka流处理管道示例",
                "request": {
                    "bootstrap_servers": "localhost:9092",
                    "topics": ["click_events", "page_views"],
                    "max_messages": 1000,
                    "max_duration_seconds": 60,
                    "output_path": "./output/kafka_result.parquet"
                }
            },
            "data_transformations": {
                "aggregate": {
                    "source_table": "raw_data",
                    "target_table": "aggregated_data",
                    "transform_type": "aggregate",
                    "group_by": ["category", "date"],
                    "aggregations": {
                        "total_amount": "SUM(amount)",
                        "count": "COUNT(*)",
                        "avg_value": "AVG(value)"
                    }
                },
                "join": {
                    "source_table": "users",
                    "target_table": "user_orders",
                    "transform_type": "join",
                    "join_table": "orders",
                    "join_condition": "users.user_id = orders.user_id",
                    "columns": ["users.user_id", "users.name", "orders.order_id", "orders.amount"]
                }
            }
        }
    }
