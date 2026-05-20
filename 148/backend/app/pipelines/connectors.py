"""
DuckDB + Ibis 流批一体连接器
支持: Kafka流式读取, S3批量读取
"""

import json
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
import threading
import queue

from .duckdb_ibis_engine import DuckDBIbisEngine

logger = logging.getLogger(__name__)


class ConnectorType(Enum):
    KAFKA = "kafka"
    S3 = "s3"
    JDBC = "jdbc"
    FILE = "file"


class DataFormat(Enum):
    JSON = "json"
    CSV = "csv"
    PARQUET = "parquet"
    AVRO = "avro"
    RAW = "raw"


@dataclass
class KafkaConfig:
    """Kafka连接器配置"""
    bootstrap_servers: str
    topics: List[str]
    group_id: str = "duckdb_group"
    auto_offset_reset: str = "earliest"
    data_format: DataFormat = DataFormat.JSON
    batch_size: int = 1000
    poll_timeout: float = 1.0
    consumer_config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class S3Config:
    """S3连接器配置"""
    bucket: str
    prefix: str = ""
    access_key: Optional[str] = None
    secret_key: Optional[str] = None
    region: str = "us-east-1"
    endpoint: Optional[str] = None
    data_format: DataFormat = DataFormat.PARQUET
    use_globbing: bool = True


class KafkaConnector:
    """
    Kafka流式数据连接器
    支持消费Kafka消息并写入DuckDB表
    """
    
    def __init__(self, engine: DuckDBIbisEngine, config: KafkaConfig):
        self.engine = engine
        self.config = config
        self._consumer = None
        self._running = False
        self._thread = None
        self._message_queue = queue.Queue(maxsize=10000)
        
    def initialize(self) -> None:
        """初始化Kafka消费者"""
        try:
            from kafka import KafkaConsumer
            
            consumer_config = {
                "bootstrap_servers": self.config.bootstrap_servers,
                "group_id": self.config.group_id,
                "auto_offset_reset": self.config.auto_offset_reset,
                "enable_auto_commit": True,
                **self.config.consumer_config
            }
            
            # 根据数据格式配置value_deserializer
            if self.config.data_format == DataFormat.JSON:
                consumer_config["value_deserializer"] = lambda m: json.loads(m.decode("utf-8"))
            elif self.config.data_format == DataFormat.RAW:
                consumer_config["value_deserializer"] = lambda m: m.decode("utf-8")
            
            self._consumer = KafkaConsumer(*self.config.topics, **consumer_config)
            logger.info(f"Kafka consumer initialized for topics: {self.config.topics}")
            
        except ImportError:
            logger.warning("kafka-python not installed, using mock mode for testing")
            self._consumer = MockKafkaConsumer(self.config)
            
    def start_streaming(
        self,
        target_table: str,
        max_messages: Optional[int] = None,
        max_duration_seconds: Optional[int] = 60,
        message_callback: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        开始流式消费Kafka数据
        
        Args:
            target_table: 写入的目标DuckDB表名
            max_messages: 最大消息数，None表示无限
            max_duration_seconds: 最大运行时长
            message_callback: 每条消息处理后的回调
        """
        if not self._consumer:
            self.initialize()
            
        self._running = True
        stats = {
            "total_messages": 0,
            "batches_processed": 0,
            "errors": 0,
            "start_time": time.time(),
            "target_table": target_table
        }
        
        # 创建目标表（如果不存在）
        self._create_target_table(target_table)
        
        try:
            batch_messages = []
            
            while self._running:
                # 检查是否达到最大消息数
                if max_messages and stats["total_messages"] >= max_messages:
                    logger.info(f"Reached max messages: {max_messages}")
                    break
                    
                # 检查是否达到最大运行时长
                if max_duration_seconds and (time.time() - stats["start_time"]) > max_duration_seconds:
                    logger.info(f"Reached max duration: {max_duration_seconds}s")
                    break
                
                # 拉取消息
                try:
                    records = self._consumer.poll(timeout_ms=int(self.config.poll_timeout * 1000))
                    
                    for _, messages in records.items():
                        for message in messages:
                            processed_message = self._process_message(message)
                            batch_messages.append(processed_message)
                            
                            stats["total_messages"] += 1
                            
                            if message_callback:
                                message_callback(message)
                                
                            # 达到批大小时写入
                            if len(batch_messages) >= self.config.batch_size:
                                self._write_batch(target_table, batch_messages)
                                stats["batches_processed"] += 1
                                batch_messages = []
                                
                except Exception as e:
                    logger.error(f"Error consuming Kafka messages: {e}")
                    stats["errors"] += 1
                    
                # 短暂休眠避免CPU过高
                time.sleep(0.01)
                
            # 处理剩余消息
            if batch_messages:
                self._write_batch(target_table, batch_messages)
                stats["batches_processed"] += 1
                
        finally:
            self._running = False
            if self._consumer:
                self._consumer.close()
                
        stats["end_time"] = time.time()
        stats["duration_seconds"] = stats["end_time"] - stats["start_time"]
        stats["messages_per_second"] = stats["total_messages"] / stats["duration_seconds"] if stats["duration_seconds"] > 0 else 0
        
        logger.info(f"Kafka streaming completed: {stats}")
        return stats
    
    def _process_message(self, message) -> Dict[str, Any]:
        """处理单条Kafka消息"""
        try:
            value = message.value
            
            if isinstance(value, dict):
                return {
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "timestamp": message.timestamp,
                    "key": message.key.decode() if message.key else None,
                    "value": json.dumps(value) if self.config.data_format == DataFormat.JSON else str(value),
                    "headers": dict(message.headers) if message.headers else {}
                }
            else:
                return {
                    "topic": message.topic,
                    "partition": message.partition,
                    "offset": message.offset,
                    "timestamp": message.timestamp,
                    "key": message.key.decode() if message.key else None,
                    "value": str(value),
                    "headers": dict(message.headers) if message.headers else {}
                }
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                "topic": getattr(message, "topic", "unknown"),
                "value": str(message),
                "error": str(e)
            }
    
    def _create_target_table(self, table_name: str) -> None:
        """创建目标表"""
        create_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            topic VARCHAR,
            partition INTEGER,
            offset BIGINT,
            timestamp BIGINT,
            key VARCHAR,
            value VARCHAR,
            headers JSON,
            received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        self.engine.execute_sql(create_sql)
    
    def _write_batch(self, table_name: str, messages: List[Dict[str, Any]]) -> None:
        """批量写入DuckDB"""
        import pandas as pd
        
        df = pd.DataFrame(messages)
        self.engine.create_table(table_name, df, append=True)
        logger.debug(f"Wrote {len(messages)} messages to {table_name}")
    
    def stop(self) -> None:
        """停止流式消费"""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)


class S3Connector:
    """
    S3批量数据连接器
    支持从S3读取Parquet/CSV/JSON文件到DuckDB
    """
    
    def __init__(self, engine: DuckDBIbisEngine, config: S3Config):
        self.engine = engine
        self.config = config
        
    def configure_credentials(self) -> None:
        """配置S3凭证"""
        if self.config.access_key and self.config.secret_key:
            self.engine.configure_s3(
                access_key=self.config.access_key,
                secret_key=self.config.secret_key,
                region=self.config.region,
                endpoint=self.config.endpoint
            )
    
    def list_files(self) -> List[str]:
        """列出S3路径下的所有文件"""
        self.configure_credentials()
        
        path = f"s3://{self.config.bucket}/{self.config.prefix}"
        if self.config.use_globbing and not path.endswith("*"):
            path = path.rstrip("/") + "/*"
            
        # 使用DuckDB列出文件
        sql = f"SELECT filename FROM glob('{path}')"
        result = self.engine.execute_sql(sql)
        
        if result.success:
            return result.data['filename'].tolist()
        return []
    
    def read_parquet(
        self,
        s3_path: Optional[str] = None,
        target_table: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        从S3读取Parquet文件
        
        Args:
            s3_path: S3路径，如 s3://bucket/path/file.parquet
            target_table: 写入的表名
        """
        self.configure_credentials()
        
        if not s3_path:
            s3_path = f"s3://{self.config.bucket}/{self.config.prefix}"
            
        # 构建读取选项
        options = []
        for key, value in kwargs.items():
            options.append(f"{key.upper()} {value}")
        options_str = ", ".join(options)
        
        if options_str:
            read_sql = f"SELECT * FROM read_parquet('{s3_path}', {options_str})"
        else:
            read_sql = f"SELECT * FROM read_parquet('{s3_path}')"
        
        result = self.engine.execute_sql(read_sql)
        
        stats = {
            "success": result.success,
            "row_count": result.row_count,
            "s3_path": s3_path,
            "execution_time_ms": result.execution_time_ms
        }
        
        if result.success and target_table:
            self.engine.create_table(target_table, result.data)
            stats["target_table"] = target_table
            logger.info(f"Read {result.row_count} rows from S3 to table {target_table}")
            
        if not result.success:
            stats["error"] = result.error_message
            
        return stats
    
    def read_csv(
        self,
        s3_path: Optional[str] = None,
        target_table: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """从S3读取CSV文件"""
        self.configure_credentials()
        
        if not s3_path:
            s3_path = f"s3://{self.config.bucket}/{self.config.prefix}"
            
        options = []
        for key, value in kwargs.items():
            options.append(f"{key.upper()} {value}")
        options_str = ", ".join(options)
        
        if options_str:
            read_sql = f"SELECT * FROM read_csv('{s3_path}', {options_str})"
        else:
            read_sql = f"SELECT * FROM read_csv('{s3_path}')"
        
        result = self.engine.execute_sql(read_sql)
        
        stats = {
            "success": result.success,
            "row_count": result.row_count,
            "s3_path": s3_path,
            "execution_time_ms": result.execution_time_ms
        }
        
        if result.success and target_table:
            self.engine.create_table(target_table, result.data)
            stats["target_table"] = target_table
            
        if not result.success:
            stats["error"] = result.error_message
            
        return stats
    
    def read_json(
        self,
        s3_path: Optional[str] = None,
        target_table: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """从S3读取JSON文件"""
        self.configure_credentials()
        
        if not s3_path:
            s3_path = f"s3://{self.config.bucket}/{self.config.prefix}"
            
        options = []
        for key, value in kwargs.items():
            options.append(f"{key.upper()} {value}")
        options_str = ", ".join(options)
        
        if options_str:
            read_sql = f"SELECT * FROM read_json('{s3_path}', {options_str})"
        else:
            read_sql = f"SELECT * FROM read_json('{s3_path}')"
        
        result = self.engine.execute_sql(read_sql)
        
        stats = {
            "success": result.success,
            "row_count": result.row_count,
            "s3_path": s3_path,
            "execution_time_ms": result.execution_time_ms
        }
        
        if result.success and target_table:
            self.engine.create_table(target_table, result.data)
            stats["target_table"] = target_table
            
        if not result.success:
            stats["error"] = result.error_message
            
        return stats
    
    def write_parquet(
        self,
        source_table: str,
        s3_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        将DuckDB表写入S3的Parquet文件
        
        Args:
            source_table: 源表名
            s3_path: 目标S3路径
            partition_by: 分区列列表
            compression: 压缩格式 (snappy, gzip, zstd)
        """
        self.configure_credentials()
        
        if not s3_path:
            s3_path = f"s3://{self.config.bucket}/{self.config.prefix}"
            
        start_time = time.time()
        
        try:
            # 构建COPY选项
            options = ["FORMAT PARQUET"]
            for key, value in kwargs.items():
                if key == "partition_by":
                    cols = ", ".join(value) if isinstance(value, list) else value
                    options.append(f"PARTITION_BY ({cols})")
                elif key == "compression":
                    options.append(f"COMPRESSION {value.upper()}")
                else:
                    options.append(f"{key.upper()} {value}")
                    
            options_str = ", ".join(options)
            sql = f"COPY {source_table} TO '{s3_path}' ({options_str})"
            
            self.engine.execute_sql(sql)
            
            return {
                "success": True,
                "source_table": source_table,
                "s3_path": s3_path,
                "execution_time_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            logger.error(f"Error writing to S3: {e}")
            return {
                "success": False,
                "source_table": source_table,
                "s3_path": s3_path,
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000
            }


class ParquetMaterializer:
    """
    Parquet自动物化器
    自动将DuckDB表物化为Parquet文件（本地或S3）
    """
    
    def __init__(self, engine: DuckDBIbisEngine):
        self.engine = engine
        
    def materialize_table(
        self,
        source_table: str,
        output_path: str,
        partition_by: Optional[List[str]] = None,
        compression: str = "snappy",
        row_group_size: int = 100000,
        overwrite: bool = True
    ) -> Dict[str, Any]:
        """
        将表物化为Parquet文件
        
        Args:
            source_table: 源表名
            output_path: 输出路径（本地路径或S3路径）
            partition_by: 分区列列表
            compression: 压缩格式 (snappy, gzip, zstd, uncompressed)
            row_group_size: 行组大小
            overwrite: 是否覆盖已有文件
        """
        start_time = time.time()
        
        try:
            # 构建选项
            options = [
                "FORMAT PARQUET",
                f"COMPRESSION {compression.upper()}",
                f"ROW_GROUP_SIZE {row_group_size}"
            ]
            
            if partition_by:
                cols = ", ".join(partition_by)
                options.append(f"PARTITION_BY ({cols})")
                
            if overwrite:
                options.append("OVERWRITE TRUE")
                
            options_str = ", ".join(options)
            
            sql = f"COPY {source_table} TO '{output_path}' ({options_str})"
            
            self.engine.execute_sql(sql)
            
            duration = (time.time() - start_time) * 1000
            
            logger.info(f"Successfully materialized {source_table} to {output_path} in {duration:.2f}ms")
            
            return {
                "success": True,
                "source_table": source_table,
                "output_path": output_path,
                "partition_by": partition_by,
                "compression": compression,
                "execution_time_ms": duration
            }
            
        except Exception as e:
            logger.error(f"Materialization failed: {e}")
            return {
                "success": False,
                "source_table": source_table,
                "output_path": output_path,
                "error": str(e),
                "execution_time_ms": (time.time() - start_time) * 1000
            }
    
    def materialize_query_result(
        self,
        query: str,
        output_path: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        将查询结果物化为Parquet文件
        
        Args:
            query: SQL查询语句
            output_path: 输出路径
        """
        # 先执行查询创建临时表
        temp_table = f"temp_materialize_{int(time.time() * 1000)}"
        
        try:
            self.engine.execute_sql(f"CREATE TEMP TABLE {temp_table} AS {query}")
            
            return self.materialize_table(temp_table, output_path, **kwargs)
        finally:
            try:
                self.engine.execute_sql(f"DROP TABLE IF EXISTS {temp_table}")
            except:
                pass
    
    def incremental_materialize(
        self,
        source_table: str,
        output_path: str,
        watermark_column: str,
        last_watermark_value,
        **kwargs
    ) -> Dict[str, Any]:
        """
        增量物化（基于水印列）
        
        Args:
            source_table: 源表名
            output_path: 输出路径
            watermark_column: 水印列名（通常是时间戳）
            last_watermark_value: 上次的水印值
        """
        # 构建增量查询
        query = f"""
        SELECT * FROM {source_table}
        WHERE {watermark_column} > '{last_watermark_value}'
        """
        
        # 获取新的水印值
        watermark_result = self.engine.execute_sql(
            f"SELECT MAX({watermark_column}) as max_watermark FROM {source_table}"
        )
        
        new_watermark = None
        if watermark_result.success and len(watermark_result.data) > 0:
            new_watermark = watermark_result.data.iloc[0]['max_watermark']
            
        # 执行物化
        result = self.materialize_query_result(query, output_path, **kwargs)
        result["new_watermark"] = new_watermark
        
        return result


class MockKafkaConsumer:
    """Mock Kafka消费者，用于测试"""
    
    def __init__(self, config: KafkaConfig):
        self.config = config
        self._message_count = 0
        
    def poll(self, timeout_ms: int = 1000):
        """模拟拉取消息"""
        import time
        time.sleep(timeout_ms / 1000)
        
        if self._message_count < 100:
            self._message_count += 1
            mock_message = type('MockMessage', (), {
                'topic': self.config.topics[0],
                'partition': 0,
                'offset': self._message_count,
                'timestamp': int(time.time() * 1000),
                'key': f'key_{self._message_count}'.encode(),
                'value': json.dumps({'id': self._message_count, 'data': f'test_{self._message_count}'}),
                'headers': []
            })
            return {('mock-topic', 0): [mock_message]}
        return {}
        
    def close(self):
        pass
