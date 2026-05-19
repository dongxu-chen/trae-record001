"""
DuckDB + Ibis 流批一体 Prefect任务集成
将DuckDB引擎封装为Prefect任务，支持流批一体管道编排
"""

from prefect import task, flow, get_run_logger
from prefect.runtime import flow_run
from typing import Dict, Any, Optional, List
from datetime import datetime
import time
import logging

from .duckdb_ibis_engine import DuckDBIbisEngine, create_engine, EngineConfig
from .connectors import (
    KafkaConfig, KafkaConnector,
    S3Config, S3Connector,
    ParquetMaterializer,
    DataFormat
)

logger = logging.getLogger(__name__)


class EngineManager:
    """DuckDB引擎管理器，支持在Prefect任务间共享引擎"""
    
    _engines: Dict[str, DuckDBIbisEngine] = {}
    
    @classmethod
    def get_engine(cls, db_path: str = ":memory:", **kwargs) -> DuckDBIbisEngine:
        """获取或创建DuckDB引擎"""
        key = db_path
        if key not in cls._engines:
            cls._engines[key] = create_engine(db_path=db_path, **kwargs)
        return cls._engines[key]
    
    @classmethod
    def close_engine(cls, db_path: str) -> None:
        """关闭引擎"""
        if db_path in cls._engines:
            cls._engines[db_path].close()
            del cls._engines[db_path]


# =============================================================================
# 核心 Prefect 任务
# =============================================================================

@task(name="init_duckdb_engine", description="初始化DuckDB + Ibis引擎")
def init_duckdb_engine_task(
    db_path: str = ":memory:",
    threads: int = 4,
    memory_limit: str = "8GB",
    **kwargs
) -> Dict[str, Any]:
    """
    初始化DuckDB引擎Prefect任务
    
    Args:
        db_path: 数据库路径
        threads: 线程数
        memory_limit: 内存限制
    """
    logger = get_run_logger()
    logger.info(f"Initializing DuckDB engine: {db_path}")
    
    engine = create_engine(
        db_path=db_path,
        threads=threads,
        memory_limit=memory_limit,
        **kwargs
    )
    
    return {
        "success": True,
        "db_path": db_path,
        "engine_config": {
            "threads": threads,
            "memory_limit": memory_limit,
            **kwargs
        }
    }


@task(name="execute_sql", description="在DuckDB中执行SQL查询")
def execute_sql_task(
    sql: str,
    db_path: str = ":memory:",
    params: Dict[str, Any] = None,
    output_table: Optional[str] = None
) -> Dict[str, Any]:
    """
    执行SQL查询Prefect任务
    
    Args:
        sql: SQL语句
        db_path: 数据库路径
        params: 查询参数
        output_table: 结果输出的表名
    """
    logger = get_run_logger()
    logger.info(f"Executing SQL: {sql[:100]}...")
    
    engine = EngineManager.get_engine(db_path)
    start_time = time.time()
    
    result = engine.execute_sql(sql, params)
    
    if result.success and output_table:
        engine.create_table(output_table, result.data)
    
    return {
        "success": result.success,
        "row_count": result.row_count,
        "execution_time_ms": result.execution_time_ms,
        "output_table": output_table,
        "error": result.error_message
    }


@task(name="execute_ibis_expression", description="执行Ibis表达式")
def execute_ibis_task(
    table_name: str,
    expression_builder: str = None,
    db_path: str = ":memory:",
    output_table: Optional[str] = None
) -> Dict[str, Any]:
    """
    执行Ibis表达式Prefect任务
    
    Args:
        table_name: 源表名
        expression_builder: 表达式构建代码（简化版）
        db_path: 数据库路径
        output_table: 输出表名
    """
    logger = get_run_logger()
    logger.info(f"Executing Ibis expression on table: {table_name}")
    
    engine = EngineManager.get_engine(db_path)
    start_time = time.time()
    
    # 简化版：直接执行SQL，实际场景可以构建Ibis表达式
    sql = f"SELECT * FROM {table_name}"
    if expression_builder:
        sql = expression_builder
    
    result = engine.execute_sql(sql)
    
    if result.success and output_table:
        engine.create_table(output_table, result.data)
    
    return {
        "success": result.success,
        "row_count": result.row_count,
        "execution_time_ms": (time.time() - start_time) * 1000,
        "output_table": output_table
    }


@task(name="kafka_streaming_read", description="从Kafka流式读取数据")
def kafka_streaming_read_task(
    bootstrap_servers: str,
    topics: List[str],
    target_table: str,
    db_path: str = ":memory:",
    max_messages: Optional[int] = 1000,
    max_duration_seconds: int = 60,
    batch_size: int = 100,
    group_id: str = "duckdb_group",
    data_format: str = "json",
    **kwargs
) -> Dict[str, Any]:
    """
    Kafka流式数据读取Prefect任务
    
    Args:
        bootstrap_servers: Kafka服务器地址
        topics: 主题列表
        target_table: 目标DuckDB表名
        max_messages: 最大消息数
        max_duration_seconds: 最大运行时长
        batch_size: 批大小
        group_id: 消费者组ID
        data_format: 数据格式
    """
    logger = get_run_logger()
    logger.info(f"Starting Kafka streaming: {topics} -> {target_table}")
    
    engine = EngineManager.get_engine(db_path)
    
    config = KafkaConfig(
        bootstrap_servers=bootstrap_servers,
        topics=topics,
        group_id=group_id,
        data_format=DataFormat(data_format),
        batch_size=batch_size,
        **kwargs
    )
    
    connector = KafkaConnector(engine, config)
    stats = connector.start_streaming(
        target_table=target_table,
        max_messages=max_messages,
        max_duration_seconds=max_duration_seconds
    )
    
    return stats


@task(name="s3_read_parquet", description="从S3读取Parquet文件")
def s3_read_parquet_task(
    bucket: str,
    prefix: str,
    target_table: str,
    db_path: str = ":memory:",
    access_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    region: str = "us-east-1",
    endpoint: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    S3 Parquet文件读取Prefect任务
    
    Args:
        bucket: S3桶名
        prefix: 文件前缀/路径
        target_table: 目标DuckDB表名
        access_key: 访问密钥
        secret_key: 密钥
        region: 区域
        endpoint: 端点URL（用于MinIO等）
    """
    logger = get_run_logger()
    logger.info(f"Reading Parquet from S3: {bucket}/{prefix} -> {target_table}")
    
    engine = EngineManager.get_engine(db_path)
    
    config = S3Config(
        bucket=bucket,
        prefix=prefix,
        access_key=access_key,
        secret_key=secret_key,
        region=region,
        endpoint=endpoint
    )
    
    connector = S3Connector(engine, config)
    result = connector.read_parquet(target_table=target_table, **kwargs)
    
    return result


@task(name="s3_read_csv", description="从S3读取CSV文件")
def s3_read_csv_task(
    bucket: str,
    prefix: str,
    target_table: str,
    db_path: str = ":memory:",
    **kwargs
) -> Dict[str, Any]:
    """S3 CSV文件读取Prefect任务"""
    logger = get_run_logger()
    logger.info(f"Reading CSV from S3: {bucket}/{prefix} -> {target_table}")
    
    engine = EngineManager.get_engine(db_path)
    
    config = S3Config(
        bucket=bucket,
        prefix=prefix,
        access_key=kwargs.get("access_key"),
        secret_key=kwargs.get("secret_key"),
        region=kwargs.get("region", "us-east-1"),
        endpoint=kwargs.get("endpoint")
    )
    
    connector = S3Connector(engine, config)
    result = connector.read_csv(target_table=target_table, **kwargs)
    
    return result


@task(name="materialize_parquet", description="将DuckDB表物化为Parquet文件")
def materialize_parquet_task(
    source_table: str,
    output_path: str,
    db_path: str = ":memory:",
    partition_by: Optional[List[str]] = None,
    compression: str = "snappy",
    row_group_size: int = 100000,
    is_s3_path: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Parquet物化Prefect任务
    
    Args:
        source_table: 源DuckDB表名
        output_path: 输出路径（本地路径或S3路径）
        partition_by: 分区列列表
        compression: 压缩格式
        row_group_size: 行组大小
        is_s3_path: 是否是S3路径
    """
    logger = get_run_logger()
    logger.info(f"Materializing {source_table} to {output_path}")
    
    engine = EngineManager.get_engine(db_path)
    materializer = ParquetMaterializer(engine)
    
    if is_s3_path:
        # S3输出
        config = S3Config(
            bucket=kwargs.get("bucket", ""),
            prefix="",
            access_key=kwargs.get("access_key"),
            secret_key=kwargs.get("secret_key"),
            region=kwargs.get("region", "us-east-1"),
            endpoint=kwargs.get("endpoint")
        )
        connector = S3Connector(engine, config)
        result = connector.write_parquet(
            source_table=source_table,
            s3_path=output_path,
            partition_by=partition_by,
            compression=compression
        )
    else:
        # 本地输出
        result = materializer.materialize_table(
            source_table=source_table,
            output_path=output_path,
            partition_by=partition_by,
            compression=compression,
            row_group_size=row_group_size
        )
    
    return result


@task(name="transform_data", description="数据转换任务（聚合、过滤、Join等）")
def transform_data_task(
    source_table: str,
    target_table: str,
    transform_type: str = "aggregate",
    db_path: str = ":memory:",
    columns: List[str] = None,
    where: str = None,
    group_by: List[str] = None,
    aggregations: Dict[str, str] = None,
    join_table: str = None,
    join_condition: str = None,
    join_type: str = "inner",
    **kwargs
) -> Dict[str, Any]:
    """
    数据转换Prefect任务
    支持：聚合、过滤、Join、投影等操作
    
    Args:
        source_table: 源表名
        target_table: 目标表名
        transform_type: 转换类型（select/filter/aggregate/join）
        columns: 列列表
        where: WHERE条件
        group_by: 分组列
        aggregations: 聚合函数字典 {alias: expression}
        join_table: Join表名
        join_condition: Join条件
        join_type: Join类型
    """
    logger = get_run_logger()
    logger.info(f"Transforming {source_table} -> {target_table} (type: {transform_type})")
    
    engine = EngineManager.get_engine(db_path)
    start_time = time.time()
    
    # 构建SQL
    cols = ", ".join(columns) if columns else "*"
    
    if transform_type == "select":
        sql = f"SELECT {cols} FROM {source_table}"
        if where:
            sql += f" WHERE {where}"
    
    elif transform_type == "filter":
        sql = f"SELECT {cols} FROM {source_table}"
        if where:
            sql += f" WHERE {where}"
    
    elif transform_type == "aggregate":
        if not group_by or not aggregations:
            raise ValueError("Aggregate requires group_by and aggregations")
        
        group_cols = ", ".join(group_by)
        agg_exprs = []
        for alias, expr in aggregations.items():
            agg_exprs.append(f"{expr} AS {alias}")
        
        sql = f"""
        SELECT {group_cols}, {", ".join(agg_exprs)}
        FROM {source_table}
        GROUP BY {group_cols}
        """
        if where:
            sql += f" WHERE {where}"
    
    elif transform_type == "join":
        if not join_table or not join_condition:
            raise ValueError("Join requires join_table and join_condition")
        
        join_type_upper = join_type.upper()
        sql = f"""
        SELECT {cols}
        FROM {source_table}
        {join_type_upper} JOIN {join_table} ON {join_condition}
        """
        if where:
            sql += f" WHERE {where}"
    else:
        raise ValueError(f"Unknown transform_type: {transform_type}")
    
    # 创建目标表
    create_sql = f"CREATE TABLE {target_table} AS {sql}"
    result = engine.execute_sql(create_sql)
    
    return {
        "success": result.success,
        "source_table": source_table,
        "target_table": target_table,
        "transform_type": transform_type,
        "row_count": result.row_count,
        "execution_time_ms": result.execution_time_ms,
        "sql": sql,
        "error": result.error_message
    }


@task(name="create_table_from_data", description="从数据创建表")
def create_table_task(
    table_name: str,
    data: Dict[str, Any] = None,
    data_path: str = None,
    db_path: str = ":memory:",
    if_exists: str = "replace"
) -> Dict[str, Any]:
    """
    创建DuckDB表Prefect任务
    
    Args:
        table_name: 表名
        data: 数据字典（列 -> 值列表）
        data_path: 数据文件路径（Parquet/CSV）
        if_exists: 存在时的处理方式
    """
    logger = get_run_logger()
    logger.info(f"Creating table: {table_name}")
    
    engine = EngineManager.get_engine(db_path)
    start_time = time.time()
    
    if data_path:
        # 从文件创建
        if data_path.endswith('.parquet'):
            sql = f"CREATE TABLE {table_name} AS SELECT * FROM read_parquet('{data_path}')"
        elif data_path.endswith('.csv'):
            sql = f"CREATE TABLE {table_name} AS SELECT * FROM read_csv('{data_path}')"
        else:
            raise ValueError(f"Unsupported file format: {data_path}")
        
        if if_exists == "replace":
            engine.execute_sql(f"DROP TABLE IF EXISTS {table_name}")
        
        result = engine.execute_sql(sql)
    elif data:
        # 从数据创建
        import pandas as pd
        df = pd.DataFrame(data)
        engine.create_table(table_name, df)
        result = type('Result', (), {'success': True, 'row_count': len(df), 'execution_time_ms': 0})()
    else:
        raise ValueError("Either data or data_path must be provided")
    
    return {
        "success": result.success,
        "table_name": table_name,
        "row_count": result.row_count,
        "execution_time_ms": (time.time() - start_time) * 1000
    }


@task(name="get_table_info", description="获取表信息")
def get_table_info_task(
    table_name: str,
    db_path: str = ":memory:"
) -> Dict[str, Any]:
    """
    获取表信息Prefect任务
    
    Args:
        table_name: 表名
    """
    logger = get_run_logger()
    logger.info(f"Getting table info: {table_name}")
    
    engine = EngineManager.get_engine(db_path)
    
    # 获取行数
    count_result = engine.execute_sql(f"SELECT COUNT(*) as count FROM {table_name}")
    row_count = count_result.data.iloc[0]['count'] if count_result.success else 0
    
    # 获取schema
    schema_result = engine.execute_sql(f"DESCRIBE {table_name}")
    schema = schema_result.data.to_dict('records') if schema_result.success else []
    
    return {
        "success": True,
        "table_name": table_name,
        "row_count": row_count,
        "schema": schema
    }


@task(name="list_tables", description="列出所有表")
def list_tables_task(
    db_path: str = ":memory:"
) -> Dict[str, Any]:
    """列出数据库所有表"""
    engine = EngineManager.get_engine(db_path)
    tables = engine.list_tables()
    
    return {
        "success": True,
        "tables": tables,
        "count": len(tables)
    }


# =============================================================================
# 预定义流批一体 Flow
# =============================================================================

@flow(name="s3_batch_pipeline", description="S3批处理管道")
def s3_batch_pipeline_flow(
    s3_bucket: str,
    s3_prefix: str,
    source_format: str = "parquet",
    intermediate_table: str = "raw_data",
    target_table: str = "processed_data",
    output_path: str = "./output/result.parquet",
    db_path: str = ":memory:",
    **kwargs
):
    """
    S3批处理管道Flow
    
    流程：
        1. 从S3读取数据
        2. 数据转换（聚合）
        3. 物化为Parquet文件
    """
    logger = get_run_logger()
    flow_run_id = flow_run.id or str(datetime.now().timestamp())
    logger.info(f"Starting S3 batch pipeline: {flow_run_id}")
    
    # 1. 从S3读取数据
    if source_format == "parquet":
        read_result = s3_read_parquet_task(
            bucket=s3_bucket,
            prefix=s3_prefix,
            target_table=intermediate_table,
            db_path=db_path,
            **kwargs
        )
    else:
        read_result = s3_read_csv_task(
            bucket=s3_bucket,
            prefix=s3_prefix,
            target_table=intermediate_table,
            db_path=db_path,
            **kwargs
        )
    
    if not read_result["success"]:
        raise Exception(f"Failed to read from S3: {read_result.get('error')}")
    
    # 2. 数据转换（示例：聚合）
    transform_result = transform_data_task(
        source_table=intermediate_table,
        target_table=target_table,
        transform_type="aggregate",
        db_path=db_path,
        group_by=kwargs.get("group_by", ["1"]),
        aggregations=kwargs.get("aggregations", {"count": "COUNT(*)"})
    )
    
    if not transform_result["success"]:
        raise Exception(f"Failed to transform data: {transform_result.get('error')}")
    
    # 3. 物化输出
    materialize_result = materialize_parquet_task(
        source_table=target_table,
        output_path=output_path,
        db_path=db_path,
        is_s3_path=output_path.startswith("s3://"),
        **kwargs
    )
    
    # 获取最终表信息
    table_info = get_table_info_task(target_table, db_path)
    
    return {
        "flow_run_id": flow_run_id,
        "read_result": read_result,
        "transform_result": transform_result,
        "materialize_result": materialize_result,
        "final_table_info": table_info
    }


@flow(name="kafka_streaming_pipeline", description="Kafka流处理管道")
def kafka_streaming_pipeline_flow(
    bootstrap_servers: str,
    kafka_topics: List[str],
    raw_table: str = "kafka_raw_data",
    processed_table: str = "kafka_processed_data",
    output_path: str = "./output/kafka_result.parquet",
    max_messages: int = 1000,
    max_duration_seconds: int = 60,
    db_path: str = ":memory:",
    **kwargs
):
    """
    Kafka流处理管道Flow
    
    流程：
        1. 从Kafka流式读取数据
        2. 数据转换
        3. 物化输出
    """
    logger = get_run_logger()
    flow_run_id = flow_run.id or str(datetime.now().timestamp())
    logger.info(f"Starting Kafka streaming pipeline: {flow_run_id}")
    
    # 1. 流式读取Kafka
    stream_result = kafka_streaming_read_task(
        bootstrap_servers=bootstrap_servers,
        topics=kafka_topics,
        target_table=raw_table,
        db_path=db_path,
        max_messages=max_messages,
        max_duration_seconds=max_duration_seconds,
        **kwargs
    )
    
    # 2. 数据转换（示例：解析JSON值并聚合）
    transform_sql = f"""
    SELECT 
        COUNT(*) as message_count,
        MAX(timestamp) as latest_timestamp
    FROM {raw_table}
    """
    
    transform_result = execute_sql_task(
        sql=f"CREATE TABLE {processed_table} AS {transform_sql}",
        db_path=db_path
    )
    
    # 3. 物化输出
    materialize_result = materialize_parquet_task(
        source_table=processed_table,
        output_path=output_path,
        db_path=db_path
    )
    
    return {
        "flow_run_id": flow_run_id,
        "streaming_stats": stream_result,
        "transform_result": transform_result,
        "materialize_result": materialize_result
    }


@flow(name="stream_batch_unified", description="流批一体统一管道")
def stream_batch_unified_flow(
    execution_mode: str = "batch",  # batch, streaming, auto
    kafka_config: Dict[str, Any] = None,
    s3_config: Dict[str, Any] = None,
    transform_config: Dict[str, Any] = None,
    output_config: Dict[str, Any] = None,
    db_path: str = ":memory:",
    **kwargs
):
    """
    流批一体统一管道Flow
    
    根据execution_mode自动选择：
        - batch: S3批处理
        - streaming: Kafka流处理
    """
    logger = get_run_logger()
    flow_run_id = flow_run.id or str(datetime.now().timestamp())
    logger.info(f"Starting stream-batch unified pipeline: {flow_run_id}, mode: {execution_mode}")
    
    if execution_mode == "streaming":
        if not kafka_config:
            raise ValueError("Kafka config required for streaming mode")
        
        return kafka_streaming_pipeline_flow(
            bootstrap_servers=kafka_config["bootstrap_servers"],
            kafka_topics=kafka_config["topics"],
            raw_table=kafka_config.get("raw_table", "kafka_raw"),
            processed_table=kafka_config.get("processed_table", "kafka_processed"),
            output_path=kafka_config.get("output_path", "./output/streaming_result.parquet"),
            max_messages=kafka_config.get("max_messages", 1000),
            max_duration_seconds=kafka_config.get("max_duration_seconds", 60),
            db_path=db_path,
            **kwargs
        )
    else:  # batch mode
        if not s3_config:
            raise ValueError("S3 config required for batch mode")
        
        return s3_batch_pipeline_flow(
            s3_bucket=s3_config["bucket"],
            s3_prefix=s3_config["prefix"],
            source_format=s3_config.get("format", "parquet"),
            intermediate_table=s3_config.get("intermediate_table", "s3_raw"),
            target_table=s3_config.get("target_table", "s3_processed"),
            output_path=s3_config.get("output_path", "./output/batch_result.parquet"),
            db_path=db_path,
            **kwargs
        )
