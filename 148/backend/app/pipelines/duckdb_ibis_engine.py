"""
DuckDB + Ibis 流批一体核心引擎
提供统一的SQL查询接口，支持批处理和流处理
"""

import ibis
import duckdb
from typing import Dict, Any, Optional, Union, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import time
from pathlib import Path
import pandas as pd
import pyarrow as pa

logger = logging.getLogger(__name__)


class ExecutionMode(Enum):
    """执行模式"""
    BATCH = "batch"           # 批处理模式
    STREAMING = "streaming"   # 流处理模式
    AUTO = "auto"             # 自动检测


@dataclass
class EngineConfig:
    """引擎配置"""
    db_path: str = ":memory:"  # 数据库路径，默认内存模式
    execution_mode: ExecutionMode = ExecutionMode.BATCH
    enable_parallelism: bool = True
    threads: int = 4
    memory_limit: str = "8GB"
    temp_directory: Optional[str] = None
    extensions: List[str] = field(default_factory=lambda: ["httpfs", "parquet", "json"])


@dataclass
class QueryResult:
    """查询结果封装"""
    success: bool
    data: Optional[pd.DataFrame] = None
    arrow_table: Optional[pa.Table] = None
    execution_time_ms: float = 0.0
    row_count: int = 0
    error_message: Optional[str] = None


class DuckDBIbisEngine:
    """
    DuckDB + Ibis 流批一体执行引擎
    
    核心能力:
    1. 使用DuckDB作为嵌入式OLAP引擎
    2. Ibis提供统一DataFrame API
    3. 支持批处理和流处理切换
    """
    
    def __init__(self, config: EngineConfig = None):
        self.config = config or EngineConfig()
        self._con = None
        self._ibis_con = None
        self._initialized = False
        
    def initialize(self) -> None:
        """初始化引擎"""
        if self._initialized:
            return
            
        start_time = time.time()
        
        # 配置DuckDB连接参数
        db_config = {
            "threads": self.config.threads,
            "memory_limit": self.config.memory_limit,
        }
        
        if self.config.temp_directory:
            db_config["temp_directory"] = self.config.temp_directory
            
        # 创建DuckDB连接
        self._con = duckdb.connect(
            database=self.config.db_path,
            config=db_config
        )
        
        # 安装并加载扩展
        for ext in self.config.extensions:
            try:
                self._con.execute(f"INSTALL {ext}")
                self._con.execute(f"LOAD {ext}")
                logger.info(f"Successfully loaded extension: {ext}")
            except Exception as e:
                logger.warning(f"Could not load extension {ext}: {e}")
        
        # 创建Ibis连接
        self._ibis_con = ibis.duckdb.connect(connection=self._con)
        
        self._initialized = True
        logger.info(f"DuckDB + Ibis engine initialized in {time.time() - start_time:.2f}s")
        
    @property
    def connection(self):
        """获取原生DuckDB连接"""
        if not self._initialized:
            self.initialize()
        return self._con
    
    @property
    def ibis_connection(self):
        """获取Ibis连接"""
        if not self._initialized:
            self.initialize()
        return self._ibis_con
    
    def execute_sql(self, sql: str, params: Dict = None) -> QueryResult:
        """执行原生SQL查询"""
        start_time = time.time()
        
        try:
            result = self.connection.execute(sql, params or {})
            df = result.fetchdf()
            
            return QueryResult(
                success=True,
                data=df,
                execution_time_ms=(time.time() - start_time) * 1000,
                row_count=len(df)
            )
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            return QueryResult(
                success=False,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def table(self, name: str):
        """获取Ibis表表达式"""
        return self.ibis_connection.table(name)
    
    def create_table(self, name: str, data, **kwargs) -> None:
        """创建表"""
        self.ibis_connection.create_table(name, data, **kwargs)
    
    def drop_table(self, name: str, force: bool = True) -> None:
        """删除表"""
        try:
            self.ibis_connection.drop_table(name, force=force)
        except Exception as e:
            logger.warning(f"Drop table warning: {e}")
    
    def execute_ibis(self, expr) -> QueryResult:
        """执行Ibis表达式"""
        start_time = time.time()
        
        try:
            result = expr.to_pandas()
            
            return QueryResult(
                success=True,
                data=result,
                execution_time_ms=(time.time() - start_time) * 1000,
                row_count=len(result)
            )
        except Exception as e:
            logger.error(f"Ibis execution failed: {e}")
            return QueryResult(
                success=False,
                error_message=str(e),
                execution_time_ms=(time.time() - start_time) * 1000
            )
    
    def compile_sql(self, expr) -> str:
        """将Ibis表达式编译为SQL"""
        return self.ibis_connection.compile(expr)
    
    def configure_s3(self, access_key: str, secret_key: str, region: str = "us-east-1", endpoint: str = None) -> None:
        """配置S3连接"""
        secret_sql = f"""
        CREATE OR REPLACE SECRET s3_secret (
            TYPE S3,
            PROVIDER CONFIG,
            KEY_ID '{access_key}',
            SECRET '{secret_key}',
            REGION '{region}'
        )
        """
        
        if endpoint:
            secret_sql = f"""
            CREATE OR REPLACE SECRET s3_secret (
                TYPE S3,
                PROVIDER CONFIG,
                KEY_ID '{access_key}',
                SECRET '{secret_key}',
                REGION '{region}',
                ENDPOINT '{endpoint}'
            )
            """
            
        self.connection.execute(secret_sql)
        logger.info("S3 secret configured")
    
    def read_parquet(self, path: str, table_name: str = None) -> QueryResult:
        """读取Parquet文件"""
        dest_table = table_name or f"parquet_temp_{int(time.time())}"
        
        sql = f"SELECT * FROM read_parquet('{path}')"
        result = self.execute_sql(sql)
        
        if result.success and table_name:
            self.create_table(table_name, result.data)
            
        return result
    
    def read_csv(self, path: str, table_name: str = None, **kwargs) -> QueryResult:
        """读取CSV文件"""
        options = ", ".join([f"{k}={v}" for k, v in kwargs.items()])
        sql = f"SELECT * FROM read_csv('{path}')"
        if options:
            sql = f"SELECT * FROM read_csv('{path}', {options})"
        
        result = self.execute_sql(sql)
        
        if result.success and table_name:
            self.create_table(table_name, result.data)
            
        return result
    
    def read_json(self, path: str, table_name: str = None) -> QueryResult:
        """读取JSON文件"""
        sql = f"SELECT * FROM read_json('{path}')"
        result = self.execute_sql(sql)
        
        if result.success and table_name:
            self.create_table(table_name, result.data)
            
        return result
    
    def write_parquet(self, table_name: str, output_path: str, **kwargs) -> bool:
        """将表写入Parquet文件"""
        try:
            options = ", ".join([f"{k.upper()} {v}" for k, v in kwargs.items()])
            sql = f"COPY {table_name} TO '{output_path}' (FORMAT PARQUET"
            if options:
                sql += f", {options}"
            sql += ")"
            
            self.connection.execute(sql)
            logger.info(f"Successfully wrote {table_name} to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Write parquet failed: {e}")
            return False
    
    def list_tables(self) -> List[str]:
        """列出所有表"""
        return self.ibis_connection.list_tables()
    
    def get_table_schema(self, table_name: str) -> Dict[str, str]:
        """获取表结构"""
        table = self.table(table_name)
        return {col.name: str(col.type) for col in table.columns}
    
    def close(self) -> None:
        """关闭连接"""
        if self._con:
            self._con.close()
            self._con = None
            self._ibis_con = None
            self._initialized = False
            logger.info("DuckDB engine closed")


class StreamingProcessor:
    """
    流处理器
    支持微批处理模式处理流式数据
    """
    
    def __init__(self, engine: DuckDBIbisEngine):
        self.engine = engine
        self.running = False
        self.checkpoint_interval = 1000  # 毫秒
    
    def process_stream(
        self,
        source_table: str,
        target_table: str,
        transform_sql: str,
        batch_size: int = 1000,
        max_duration_ms: int = 60000,
        checkpoint_callback=None
    ) -> Dict[str, Any]:
        """
        处理流式数据（微批模式）
        
        Args:
            source_table: 源表名（包含流式数据）
            target_table: 目标表名
            transform_sql: 转换SQL
            batch_size: 每批处理大小
            max_duration_ms: 最大处理时长
            checkpoint_callback: 检查点回调函数
        """
        stats = {
            "total_processed": 0,
            "batches": 0,
            "errors": 0,
            "start_time": time.time()
        }
        
        self.running = True
        start_time = time.time()
        
        try:
            # 创建目标表（如果不存在）
            self.engine.execute_sql(f"""
                CREATE TABLE IF NOT EXISTS {target_table} AS 
                {transform_sql} LIMIT 0
            """)
            
            while self.running:
                # 检查超时
                if time.time() - start_time > max_duration_ms / 1000:
                    logger.info("Max duration reached, stopping stream processor")
                    break
                
                # 微批处理
                batch_result = self._process_batch(
                    source_table,
                    target_table,
                    transform_sql,
                    batch_size
                )
                
                if batch_result["processed"] > 0:
                    stats["total_processed"] += batch_result["processed"]
                    stats["batches"] += 1
                    
                    if checkpoint_callback:
                        checkpoint_callback(stats)
                        
                elif batch_result.get("empty", False):
                    # 没有新数据，短暂等待
                    time.sleep(0.1)
                    
                if batch_result.get("error"):
                    stats["errors"] += 1
                    logger.error(f"Batch error: {batch_result['error']}")
                    
        finally:
            self.running = False
            stats["end_time"] = time.time()
            stats["duration_ms"] = (stats["end_time"] - stats["start_time"]) * 1000
            
        return stats
    
    def _process_batch(
        self,
        source_table: str,
        target_table: str,
        transform_sql: str,
        batch_size: int
    ) -> Dict[str, Any]:
        """处理单个批次"""
        try:
            # 检查是否有新数据
            check_result = self.engine.execute_sql(
                f"SELECT COUNT(*) as cnt FROM {source_table}"
            )
            
            if not check_result.success or check_result.data.iloc[0]['cnt'] == 0:
                return {"processed": 0, "empty": True}
            
            # 执行转换并写入目标表
            insert_sql = f"""
            INSERT INTO {target_table}
            {transform_sql}
            LIMIT {batch_size}
            """
            
            result = self.engine.execute_sql(insert_sql)
            
            if result.success:
                return {"processed": result.row_count}
            else:
                return {"processed": 0, "error": result.error_message}
                
        except Exception as e:
            return {"processed": 0, "error": str(e)}
    
    def stop(self):
        """停止流处理"""
        self.running = False


def create_engine(**kwargs) -> DuckDBIbisEngine:
    """
    创建DuckDB + Ibis引擎的便捷函数
    
    示例:
        engine = create_engine(
            db_path="data.duckdb",
            threads=8,
            memory_limit="16GB"
        )
    """
    config = EngineConfig(**kwargs)
    engine = DuckDBIbisEngine(config)
    engine.initialize()
    return engine
