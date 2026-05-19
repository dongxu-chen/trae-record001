from typing import Dict, Any, List, Optional
import logging
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    BATCH = "batch"
    STREAMING = "streaming"
    UNIFIED = "unified"  # 流批一体


class SourceType(Enum):
    KAFKA = "kafka"
    MYSQL = "mysql"
    POSTGRESQL = "postgres"
    CSV = "csv"
    JSON = "json"
    JDBC = "jdbc"
    DATAGEN = "datagen"  # 数据生成器


class SinkType(Enum):
    KAFKA = "kafka"
    JDBC = "jdbc"
    PRINT = "print"
    CSV = "csv"
    ELASTICSEARCH = "elasticsearch"
    REDIS = "redis"


@dataclass
class FlinkJobConfig:
    job_name: str
    execution_mode: ExecutionMode
    source_config: Dict[str, Any]
    sink_config: Dict[str, Any]
    transform_sql: List[str]
    checkpoint_interval: int = 60000
    parallelism: int = 1
    state_backend: str = "filesystem"
    checkpoint_path: Optional[str] = None


class FlinkTableExecutor:
    """
    Flink Table API 执行器 - 流批一体
    使用Flink Python API (PyFlink)
    """

    def __init__(self):
        self.t_env = None
        self.env = None

    def _build_source_ddl(self, source_config: Dict[str, Any], mode: ExecutionMode) -> str:
        """构建Source表DDL"""
        source_type = source_config.get("type", "datagen")
        table_name = source_config.get("table_name", "source_table")
        columns = source_config.get("columns", [])

        columns_def = ",\n  ".join([
            f"{col['name']} {col['type']}" for col in columns
        ])

        if source_type == SourceType.KAFKA.value:
            connector_props = [
                f"'connector' = 'kafka'",
                f"'topic' = '{source_config.get('topic', 'default_topic')}'",
                f"'properties.bootstrap.servers' = '{source_config.get('bootstrap_servers', 'localhost:9092')}'",
                f"'properties.group.id' = '{source_config.get('group_id', 'flink_group')}'",
                f"'scan.startup.mode' = '{source_config.get('startup_mode', 'earliest-offset')}'",
                f"'format' = '{source_config.get('format', 'json')}'"
            ]
        elif source_type == SourceType.JDBC.value:
            connector_props = [
                f"'connector' = 'jdbc'",
                f"'url' = '{source_config.get('url', 'jdbc:mysql://localhost:3306/db')}'",
                f"'table-name' = '{source_config.get('table_name', 'source_table')}'",
                f"'username' = '{source_config.get('username', 'root')}'",
                f"'password' = '{source_config.get('password', '')}'"
            ]
        elif source_type == SourceType.DATAGEN.value:
            connector_props = [
                f"'connector' = 'datagen'",
                f"'rows-per-second' = '{source_config.get('rows_per_second', 10)}'"
            ]
        else:
            connector_props = [f"'connector' = '{source_type}'"]

        connector_str = ",\n  ".join(connector_props)

        return f"""
        CREATE TABLE {table_name} (
          {columns_def}
        ) WITH (
          {connector_str}
        )
        """

    def _build_sink_ddl(self, sink_config: Dict[str, Any], mode: ExecutionMode) -> str:
        """构建Sink表DDL"""
        sink_type = sink_config.get("type", "print")
        table_name = sink_config.get("table_name", "sink_table")
        columns = sink_config.get("columns", [])

        columns_def = ",\n  ".join([
            f"{col['name']} {col['type']}" for col in columns
        ])

        if sink_type == SinkType.KAFKA.value:
            connector_props = [
                f"'connector' = 'kafka'",
                f"'topic' = '{sink_config.get('topic', 'sink_topic')}'",
                f"'properties.bootstrap.servers' = '{sink_config.get('bootstrap_servers', 'localhost:9092')}'",
                f"'format' = '{sink_config.get('format', 'json')}'"
            ]
        elif sink_type == SinkType.JDBC.value:
            connector_props = [
                f"'connector' = 'jdbc'",
                f"'url' = '{sink_config.get('url', 'jdbc:mysql://localhost:3306/db')}'",
                f"'table-name' = '{sink_config.get('table_name', 'sink_table')}'",
                f"'username' = '{sink_config.get('username', 'root')}'",
                f"'password' = '{sink_config.get('password', '')}'"
            ]
        elif sink_type == SinkType.PRINT.value:
            connector_props = [f"'connector' = 'print'"]
        else:
            connector_props = [f"'connector' = '{sink_type}'"]

        connector_str = ",\n  ".join(connector_props)

        return f"""
        CREATE TABLE {table_name} (
          {columns_def}
        ) WITH (
          {connector_str}
        )
        """

    def generate_job_code(self, config: FlinkJobConfig) -> str:
        """
        生成Flink Python作业代码
        返回可执行的PyFlink脚本
        """
        source_ddl = self._build_source_ddl(config.source_config, config.execution_mode)
        sink_ddl = self._build_sink_ddl(config.sink_config, config.execution_mode)
        transform_sqls = "\n        ".join([f"t_env.execute_sql(\"{sql}\")" for sql in config.transform_sql])

        checkpoint_config = ""
        if config.checkpoint_path:
            checkpoint_config = f"""
        # 配置Checkpoint
        t_env.get_config().set('execution.checkpointing.interval', '{config.checkpoint_interval}')
        t_env.get_config().set('state.backend', '{config.state_backend}')
        t_env.get_config().set('state.checkpoints.dir', '{config.checkpoint_path}')
        """

        execution_mode_config = f"""
        # 设置执行模式（流批一体）
        from pyflink.table import EnvironmentSettings
        if config.execution_mode == ExecutionMode.BATCH.value:
            env_settings = EnvironmentSettings.in_batch_mode()
        elif config.execution_mode == ExecutionMode.STREAMING.value:
            env_settings = EnvironmentSettings.in_streaming_mode()
        else:
            # 统一模式：自动根据数据源推断
            env_settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
        """

        return f'''
# -*- coding: utf-8 -*-
"""
Flink流批一体处理作业
作业名称: {config.job_name}
执行模式: {config.execution_mode.value}
生成时间: 自动生成
"""

from pyflink.table import TableEnvironment, EnvironmentSettings
from pyflink.common.typeinfo import Types

def run():
    # 1. 创建执行环境
    {execution_mode_config.strip()}

    t_env = TableEnvironment.create(env_settings)

    # 设置并行度
    t_env.get_config().set('parallelism.default', '{config.parallelism}')

    {checkpoint_config.strip()}

    # 2. 创建Source表
    {source_ddl.strip()}

    # 3. 创建Sink表
    {sink_ddl.strip()}

    # 4. 执行转换SQL
    {transform_sqls}

    print("Flink作业提交成功!")

if __name__ == "__main__":
    run()
'''

    def validate_config(self, config: FlinkJobConfig) -> Dict[str, bool]:
        """验证Flink作业配置"""
        errors = []

        if not config.source_config:
            errors.append("缺少source配置")

        if not config.sink_config:
            errors.append("缺少sink配置")

        if config.transform_sql == 0:
            errors.append("缺少转换SQL")

        return {
            "valid": len(errors) == 0,
            "errors": errors
        }


class FlinkSQLTemplate:
    """常用Flink SQL模板库"""

    @staticmethod
    def filter_template(condition: str) -> str:
        """过滤模板"""
        return f"SELECT * FROM source_table WHERE {condition}"

    @staticmethod
    def select_template(columns: List[str]) -> str:
        """选择列模板"""
        cols_str = ", ".join(columns)
        return f"SELECT {cols_str} FROM source_table"

    @staticmethod
    def aggregate_template(group_by: List[str], aggregations: Dict[str, str]) -> str:
        """聚合模板"""
        group_str = ", ".join(group_by)
        agg_str = ", ".join([f"{v} AS {k}" for k, v in aggregations.items()])
        return f"SELECT {group_str}, {agg_str} FROM source_table GROUP BY {group_str}"

    @staticmethod
    def join_template(left_table: str, right_table: str, join_type: str, join_condition: str, select_columns: List[str]) -> str:
        """Join模板"""
        cols_str = ", ".join(select_columns)
        return f"""
        SELECT {cols_str}
        FROM {left_table}
        {join_type} JOIN {right_table}
        ON {join_condition}
        """

    @staticmethod
    def window_template(window_type: str, time_col: str, duration: str, group_by: List[str], aggregations: Dict[str, str]) -> str:
        """窗口模板 - 流处理窗口"""
        group_str = ", ".join(group_by)
        agg_str = ", ".join([f"{v} AS {k}" for k, v in aggregations.items()]

        if window_type.upper() == "TUMBLE":
            window_func = f"TUMBLE({time_col, INTERVAL '{duration}')"
        elif window_type.upper() == "HOP":
            window_func = f"HOP({time_col}, INTERVAL '{duration}')"
        elif window_type.upper() == "SESSION":
            window_func = f"SESSION({time_col}, INTERVAL '{duration}')"
        else:
            window_func = f"TUMBLE({time_col}, INTERVAL '{duration}')"

        return f"""
        SELECT
            {group_str},
            {window_func}.start AS window_start,
            {window_func}.end AS window_end,
            {agg_str}
        FROM source_table
        GROUP BY {group_str}, {window_func}
        """


def create_flink_job_config(
    job_name: str,
    source_type: str,
    sink_type: str,
    transform_sql: List[str],
    execution_mode: str = "streaming",
    source_props: Dict = None,
    sink_props: Dict = None,
    parallelism: int = 1
) -> Dict[str, Any]:
    """
    创建Flink作业配置的便捷函数"""
    source_config = {
        "type": source_type,
        "table_name": "source_table",
        **(source_props or {}),
        "columns": source_props.get("columns", [{"name": "id", "type": "INT"}])
    }

    sink_config = {
        "type": sink_type,
        "table_name": "sink_table",
        **(sink_props or {}),
        "columns": sink_props.get("columns", [{"name": "id", "type": "INT"}])
    }

    config = FlinkJobConfig(
        job_name=job_name,
        execution_mode=ExecutionMode(execution_mode),
        source_config=source_config,
        sink_config=sink_config,
        transform_sql=transform_sql,
        parallelism=parallelism
    )

    executor = FlinkTableExecutor()
    job_code = executor.generate_job_code(config)

    return {
        "config": config.__dict__,
        "job_code": job_code,
        "execution_mode": execution_mode
    }
