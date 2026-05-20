from prefect import flow, Flow, task as prefect_task
from prefect.runtime import flow_run
from prefect.client import get_client
from prefect.concurrency import task_concurrency_limit
from typing import Dict, Any, List, Optional, Set, Tuple
import logging
from datetime import datetime
from collections import deque
import json
import asyncio
from sqlalchemy.orm import Session

from .tasks import TASK_REGISTRY
from .data_quality import DATA_QUALITY_REGISTRY
from app.core.database import get_db
from app.models.pipeline import PipelineExecution, TaskExecution

logger = logging.getLogger(__name__)


class DAGValidator:
    """使用Kahn算法检测DAG循环依赖"""

    def __init__(self, nodes: List[str], edges: List[Tuple[str, str]]):
        self.nodes = nodes
        self.edges = edges
        self.in_degree = {node: 0 for node in nodes}
        self.adjacency = {node: [] for node in nodes}

    def build_graph(self):
        """构建邻接表和入度表"""
        for source, target in self.edges:
            if source in self.nodes and target in self.nodes:
                self.adjacency[source].append(target)
                self.in_degree[target] += 1

    def kahn_algorithm(self) -> Tuple[bool, List[str], List[str]]:
        """
        Kahn算法进行拓扑排序
        返回: (是否有环, 拓扑顺序, 环中节点)
        """
        self.build_graph()
        queue = deque()
        result = []
        in_degree_copy = self.in_degree.copy()

        # 初始化入度为0的节点
        for node in self.nodes:
            if in_degree_copy[node] == 0:
                queue.append(node)

        visited_count = 0
        while queue:
            current = queue.popleft()
            result.append(current)
            visited_count += 1

            for neighbor in self.adjacency[current]:
                in_degree_copy[neighbor] -= 1
                if in_degree_copy[neighbor] == 0:
                    queue.append(neighbor)

        # 检测环
        has_cycle = visited_count != len(self.nodes)
        cycle_nodes = []

        if has_cycle:
            # 找出环中的节点
            cycle_nodes = [node for node in self.nodes if in_degree_copy[node] > 0]

        return has_cycle, result, cycle_nodes

    def validate(self) -> Dict[str, Any]:
        """验证DAG有效性"""
        has_cycle, topological_order, cycle_nodes = self.kahn_algorithm()

        return {
            "valid": not has_cycle,
            "has_cycle": has_cycle,
            "topological_order": topological_order,
            "cycle_nodes": cycle_nodes,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges)
        }


class CheckpointManager:
    """Checkpoint管理，支持数据库和S3存储"""

    def __init__(self, storage_type: str = "database", s3_config: Dict = None):
        self.storage_type = storage_type
        self.s3_config = s3_config or {}

    def save_checkpoint(self, execution_id: int, task_id: str, result: Any, db: Session):
        """保存Checkpoint"""
        checkpoint_data = {
            "task_id": task_id,
            "result": result,
            "timestamp": datetime.utcnow().isoformat(),
            "status": "COMPLETED"
        }

        if self.storage_type == "database":
            # 数据库存储
            execution = db.query(PipelineExecution).filter(
                PipelineExecution.id == execution_id
            ).first()
            if execution:
                if execution.checkpoint_data is None:
                    execution.checkpoint_data = {}
                execution.checkpoint_data[task_id] = checkpoint_data
                db.commit()

        elif self.storage_type == "s3":
            # S3存储 (需要安装boto3)
            try:
                import boto3
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=self.s3_config.get('aws_access_key_id'),
                    aws_secret_access_key=self.s3_config.get('aws_secret_access_key'),
                    region_name=self.s3_config.get('region_name', 'us-east-1')
                )
                bucket = self.s3_config.get('bucket', 'etl-checkpoints')
                key = f"checkpoints/{execution_id}/{task_id}.json"
                s3.put_object(
                    Bucket=bucket,
                    Key=key,
                    Body=json.dumps(checkpoint_data, default=str)
                )
            except ImportError:
                logger.warning("boto3 not installed, falling back to database storage")
                self.save_checkpoint(execution_id, task_id, result, db)

        return checkpoint_data

    def load_checkpoint(self, execution_id: int, db: Session) -> Dict[str, Any]:
        """加载Checkpoint"""
        checkpoints = {}

        if self.storage_type == "database":
            execution = db.query(PipelineExecution).filter(
                PipelineExecution.id == execution_id
            ).first()
            if execution and execution.checkpoint_data:
                checkpoints = execution.checkpoint_data

        elif self.storage_type == "s3":
            try:
                import boto3
                s3 = boto3.client(
                    's3',
                    aws_access_key_id=self.s3_config.get('aws_access_key_id'),
                    aws_secret_access_key=self.s3_config.get('aws_secret_access_key'),
                    region_name=self.s3_config.get('region_name', 'us-east-1')
                )
                bucket = self.s3_config.get('bucket', 'etl-checkpoints')
                prefix = f"checkpoints/{execution_id}/"
                response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix)
                if 'Contents' in response:
                    for obj in response['Contents']:
                        file_obj = s3.get_object(Bucket=bucket, Key=obj['Key'])
                        task_checkpoint = json.loads(file_obj['Body'].read())
                        task_id = task_checkpoint.get('task_id')
                        if task_id:
                            checkpoints[task_id] = task_checkpoint
            except ImportError:
                logger.warning("boto3 not installed, falling back to database storage")
                execution = db.query(PipelineExecution).filter(
                    PipelineExecution.id == execution_id
                ).first()
                if execution and execution.checkpoint_data:
                    checkpoints = execution.checkpoint_data

        return checkpoints

    def get_completed_tasks(self, execution_id: int, db: Session) -> Set[str]:
        """获取已完成的任务集合"""
        checkpoints = self.load_checkpoint(execution_id, db)
        return {task_id for task_id, data in checkpoints.items()
                if data.get('status') == 'COMPLETED'}


class PipelineExecutor:
    def __init__(
        self,
        flow_config: Dict[str, Any],
        checkpoint_data: Dict[str, Any] = None,
        max_concurrent_tasks: int = 4,
        checkpoint_storage: str = "database",
        s3_config: Dict = None
    ):
        self.flow_config = flow_config
        self.checkpoint_data = checkpoint_data or {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.checkpoint_manager = CheckpointManager(checkpoint_storage, s3_config)
        self.task_results = {}
        self.db = None
        self.execution_id = None

    def set_db_session(self, db: Session, execution_id: int):
        """设置数据库会话"""
        self.db = db
        self.execution_id = execution_id

    def _get_task_by_id(self, task_id: str) -> Optional[Dict[str, Any]]:
        for task in self.flow_config.get("tasks", []):
            if task["id"] == task_id:
                return task
        return None

    def _get_dependent_tasks(self, task_id: str) -> List[str]:
        dependencies = []
        edges = self.flow_config.get("edges", [])
        for edge in edges:
            if edge["target"] == task_id:
                dependencies.append(edge["source"])
        return dependencies

    def _should_skip_task(self, task_id: str) -> bool:
        """检查任务是否应该跳过（已完成）"""
        if self.execution_id and self.db:
            completed_tasks = self.checkpoint_manager.get_completed_tasks(
                self.execution_id, self.db
            )
            return task_id in completed_tasks
        return task_id in self.checkpoint_data

    def validate_dag(self) -> Dict[str, Any]:
        """验证DAG有效性"""
        nodes = [task["id"] for task in self.flow_config.get("tasks", [])]
        edges = [(edge["source"], edge["target"])
                 for edge in self.flow_config.get("edges", [])]

        validator = DAGValidator(nodes, edges)
        result = validator.validate()

        if not result["valid"]:
            logger.error(f"DAG检测到循环依赖: {result['cycle_nodes']}")
        else:
            logger.info(f"DAG验证通过，拓扑顺序: {result['topological_order']}")

        return result

    async def execute_task(self, task_config: Dict[str, Any], input_data: Dict = None) -> Any:
        """执行单个任务，支持背压控制"""
        task_type = task_config.get("type")
        task_params = task_config.get("params", {})

        # 合并输入数据
        if input_data:
            task_params.update(input_data)

        task_func = None
        if task_type in TASK_REGISTRY:
            task_func = TASK_REGISTRY[task_type]
        elif task_type in DATA_QUALITY_REGISTRY:
            task_func = DATA_QUALITY_REGISTRY[task_type]

        if not task_func:
            raise ValueError(f"Unknown task type: {task_type}")

        # 使用Prefect并发限制实现背压
        async with task_concurrency_limit(
            task_group="etl_tasks",
            max_tasks=self.max_concurrent_tasks
        ):
            logger.info(f"执行任务: {task_type} ({task_config['id']})")
            # Prefect 2.x 使用 .with_options 配置任务
            result = await prefect_task(
                task_func,
                name=task_config.get("data", {}).get("label", task_type)
            ).with_options(max_retries=3)(**task_params)
            return result

    async def build_and_run_flow(self) -> Dict[str, Any]:
        """构建并执行流"""
        # 首先验证DAG
        validation_result = self.validate_dag()
        if not validation_result["valid"]:
            return {
                "status": "FAILED",
                "error": f"检测到循环依赖，涉及节点: {validation_result['cycle_nodes']}",
                "validation_result": validation_result
            }

        topological_order = validation_result["topological_order"]
        nodes_map = {task["id"]: task for task in self.flow_config.get("tasks", [])}

        @flow(name=self.flow_config.get("name", "ETL Pipeline"))
        async def dynamic_flow():
            flow_run_id = str(flow_run.id)
            logger.info(f"开始执行流: {flow_run_id}")

            results = {}
            semaphore = asyncio.Semaphore(self.max_concurrent_tasks)

            async def execute_with_backpressure(task_id):
                async with semaphore:
                    if self._should_skip_task(task_id):
                        logger.info(f"跳过已完成的任务: {task_id}")
                        # 从checkpoint恢复结果
                        if self.db and self.execution_id:
                            checkpoints = self.checkpoint_manager.load_checkpoint(
                                self.execution_id, self.db
                            )
                            if task_id in checkpoints:
                                results[task_id] = checkpoints[task_id].get("result")
                        return

                    task_config = nodes_map.get(task_id)
                    if not task_config:
                        return

                    # 收集依赖任务的输出
                    dependent_tasks = self._get_dependent_tasks(task_id)
                    input_data = {}
                    for dep_id in dependent_tasks:
                        if dep_id in results:
                            if "input_data" not in input_data:
                                input_data["input_data"] = results[dep_id]
                            elif "left_data" not in input_data:
                                input_data["left_data"] = results[dep_id]
                            else:
                                input_data["right_data"] = results[dep_id]

                    # 执行任务
                    try:
                        result = await self.execute_task(task_config, input_data)
                        results[task_id] = result

                        # 保存Checkpoint
                        if self.db and self.execution_id:
                            self.checkpoint_manager.save_checkpoint(
                                self.execution_id, task_id, result, self.db
                            )

                        # 保存任务执行记录
                        if self.db and self.execution_id:
                            task_execution = TaskExecution(
                                execution_id=self.execution_id,
                                task_name=task_id,
                                status="COMPLETED",
                                start_time=datetime.utcnow(),
                                end_time=datetime.utcnow(),
                                result_data=result
                            )
                            self.db.add(task_execution)
                            self.db.commit()

                    except Exception as e:
                        logger.error(f"任务执行失败 {task_id}: {str(e)}")
                        if self.db and self.execution_id:
                            task_execution = TaskExecution(
                                execution_id=self.execution_id,
                                task_name=task_id,
                                status="FAILED",
                                start_time=datetime.utcnow(),
                                error_message=str(e)
                            )
                            self.db.add(task_execution)
                            self.db.commit()
                        raise

            # 按拓扑顺序执行任务
            for task_id in topological_order:
                await execute_with_backpressure(task_id)

            return {
                "flow_run_id": flow_run_id,
                "task_results": results,
                "status": "COMPLETED",
                "topological_order": topological_order
            }

        try:
            return await dynamic_flow()
        except Exception as e:
            return {
                "status": "FAILED",
                "error": str(e)
            }


async def run_pipeline(
    flow_config: Dict[str, Any],
    checkpoint_data: Dict[str, Any] = None,
    max_concurrent_tasks: int = 4,
    checkpoint_storage: str = "database",
    s3_config: Dict = None,
    db: Session = None,
    execution_id: int = None
) -> Dict[str, Any]:
    executor = PipelineExecutor(
        flow_config,
        checkpoint_data,
        max_concurrent_tasks,
        checkpoint_storage,
        s3_config
    )

    if db and execution_id:
        executor.set_db_session(db, execution_id)

    result = await executor.build_and_run_flow()
    return result


def validate_pipeline_dag(flow_config: Dict[str, Any]) -> Dict[str, Any]:
    """验证管道DAG"""
    nodes = [task["id"] for task in flow_config.get("tasks", [])]
    edges = [(edge["source"], edge["target"])
             for edge in flow_config.get("edges", [])]

    validator = DAGValidator(nodes, edges)
    return validator.validate()


async def get_flow_run_status(flow_run_id: str) -> Dict[str, Any]:
    async with get_client() as client:
        flow_run = await client.read_flow_run(flow_run_id)
        return {
            "id": str(flow_run.id),
            "name": flow_run.name,
            "state": flow_run.state_name,
            "start_time": flow_run.start_time.isoformat() if flow_run.start_time else None,
            "end_time": flow_run.end_time.isoformat() if flow_run.end_time else None,
        }


async def cancel_flow_run(flow_run_id: str) -> bool:
    async with get_client() as client:
        await client.cancel_flow_run(flow_run_id)
        return True
