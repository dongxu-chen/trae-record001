from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import statistics
import logging
from collections import defaultdict
from enum import Enum

logger = logging.getLogger(__name__)


class PerformanceLevel(Enum):
    EXCELLENT = "excellent"
    GOOD = "good"
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class TaskMetrics:
    """任务执行指标"""
    task_id: str
    task_name: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: float = 0.0
    status: str = "PENDING"
    input_rows: int = 0
    output_rows: int = 0
    input_size_bytes: int = 0
    output_size_bytes: int = 0
    error_count: int = 0
    retry_count: int = 0
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    peak_memory_mb: float = 0.0


@dataclass
class PipelineMetrics:
    """管道执行指标"""
    pipeline_id: str
    execution_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: float = 0.0
    status: str = "PENDING"
    tasks: List[TaskMetrics] = field(default_factory=list)
    total_input_rows: int = 0
    total_output_rows: int = 0
    total_data_processed_mb: float = 0.0
    peak_memory_mb: float = 0.0
    avg_cpu_usage_percent: float = 0.0


@dataclass
class PerformanceRecommendation:
    """性能优化建议"""
    level: PerformanceLevel
    category: str
    message: str
    suggestion: str
    priority: int


class PerformanceAnalyzer:
    """性能分析器"""

    def __init__(self):
        # 性能阈值配置
        self.thresholds = {
            'task_duration_warning': 300000,    # 5分钟
            'task_duration_critical': 600000,   # 10分钟
            'throughput_warning': 100,          # 100 rows/sec
            'throughput_critical': 10,          # 10 rows/sec
            'memory_usage_warning': 512,        # 512 MB
            'memory_usage_critical': 1024,      # 1 GB
            'cpu_usage_warning': 70,            # 70%
            'cpu_usage_critical': 90,           # 90%
            'error_rate_warning': 0.01,         # 1%
            'error_rate_critical': 0.05,        # 5%
            'skew_warning': 2.0,                # 2倍差异
        }

    def calculate_throughput(self, metrics: TaskMetrics) -> float:
        """计算吞吐量 (rows/sec)"""
        if metrics.duration_ms <= 0:
            return 0.0
        return (metrics.output_rows / metrics.duration_ms) * 1000

    def calculate_data_rate(self, metrics: TaskMetrics) -> float:
        """计算数据处理速率 (MB/sec)"""
        if metrics.duration_ms <= 0:
            return 0.0
        mb_processed = metrics.output_size_bytes / (1024 * 1024)
        return (mb_processed / metrics.duration_ms) * 1000

    def calculate_error_rate(self, metrics: TaskMetrics) -> float:
        """计算错误率"""
        if metrics.input_rows <= 0:
            return 0.0
        return metrics.error_count / metrics.input_rows

    def analyze_task_performance(self, task_metrics: TaskMetrics) -> Dict[str, Any]:
        """分析单个任务的性能"""
        throughput = self.calculate_throughput(task_metrics)
        data_rate = self.calculate_data_rate(task_metrics)
        error_rate = self.calculate_error_rate(task_metrics)

        analysis = {
            'task_id': task_metrics.task_id,
            'task_name': task_metrics.task_name,
            'duration_ms': task_metrics.duration_ms,
            'throughput_rows_per_sec': round(throughput, 2),
            'data_rate_mb_per_sec': round(data_rate, 4),
            'error_rate': round(error_rate, 4),
            'input_rows': task_metrics.input_rows,
            'output_rows': task_metrics.output_rows,
            'memory_usage_mb': task_metrics.memory_usage_mb,
            'peak_memory_mb': task_metrics.peak_memory_mb,
            'cpu_usage_percent': task_metrics.cpu_usage_percent,
            'bottlenecks': [],
            'recommendations': [],
        }

        # 检查执行时间
        if task_metrics.duration_ms > self.thresholds['task_duration_critical']:
            analysis['bottlenecks'].append('execution_time')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.CRITICAL,
                    category='execution_time',
                    message=f"任务执行时间过长: {task_metrics.duration_ms/1000/60:.1f}分钟",
                    suggestion="考虑增加并行度、优化查询、拆分任务",
                    priority=1
                )
            )
        elif task_metrics.duration_ms > self.thresholds['task_duration_warning']:
            analysis['bottlenecks'].append('execution_time')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.WARNING,
                    category='execution_time',
                    message=f"任务执行时间较长: {task_metrics.duration_ms/1000/60:.1f}分钟",
                    suggestion="检查数据源性能、考虑索引优化",
                    priority=2
                )
            )

        # 检查吞吐量
        if throughput < self.thresholds['throughput_critical'] and task_metrics.input_rows > 0:
            analysis['bottlenecks'].append('throughput')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.CRITICAL,
                    category='throughput',
                    message=f"数据吞吐量过低: {throughput:.2f} rows/sec",
                    suggestion="检查数据源连接、增加批量大小、优化数据格式",
                    priority=1
                )
            )
        elif throughput < self.thresholds['throughput_warning'] and task_metrics.input_rows > 0:
            analysis['bottlenecks'].append('throughput')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.WARNING,
                    category='throughput',
                    message=f"数据吞吐量较低: {throughput:.2f} rows/sec",
                    suggestion="考虑增加资源分配、调整并行度",
                    priority=3
                )
            )

        # 检查内存使用
        if task_metrics.peak_memory_mb > self.thresholds['memory_usage_critical']:
            analysis['bottlenecks'].append('memory')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.CRITICAL,
                    category='memory',
                    message=f"内存使用过高: 峰值 {task_metrics.peak_memory_mb:.1f} MB",
                    suggestion="减小批量大小、增加内存配额、优化数据结构",
                    priority=1
                )
            )
        elif task_metrics.peak_memory_mb > self.thresholds['memory_usage_warning']:
            analysis['bottlenecks'].append('memory')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.WARNING,
                    category='memory',
                    message=f"内存使用较高: 峰值 {task_metrics.peak_memory_mb:.1f} MB",
                    suggestion="监控内存趋势、必要时增加资源",
                    priority=3
                )
            )

        # 检查CPU使用
        if task_metrics.cpu_usage_percent > self.thresholds['cpu_usage_critical']:
            analysis['bottlenecks'].append('cpu')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.CRITICAL,
                    category='cpu',
                    message=f"CPU使用率过高: {task_metrics.cpu_usage_percent:.1f}%",
                    suggestion="优化算法、增加CPU资源、考虑分布式处理",
                    priority=1
                )
            )

        # 检查错误率
        if error_rate > self.thresholds['error_rate_critical']:
            analysis['bottlenecks'].append('errors')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.CRITICAL,
                    category='errors',
                    message=f"错误率过高: {error_rate*100:.2f}%",
                    suggestion="检查数据质量、优化错误处理逻辑",
                    priority=1
                )
            )
        elif error_rate > self.thresholds['error_rate_warning']:
            analysis['bottlenecks'].append('errors')
            analysis['recommendations'].append(
                PerformanceRecommendation(
                    level=PerformanceLevel.WARNING,
                    category='errors',
                    message=f"存在错误: {error_rate*100:.2f}%",
                    suggestion="查看错误日志、加强数据验证",
                    priority=2
                )
            )

        return analysis

    def analyze_pipeline_performance(self, pipeline_metrics: PipelineMetrics) -> Dict[str, Any]:
        """分析整个管道的性能"""
        task_analyses = [self.analyze_task_performance(task) for task in pipeline_metrics.tasks]

        # 统计汇总
        durations = [t.duration_ms for t in pipeline_metrics.tasks]
        throughputs = [self.calculate_throughput(t) for t in pipeline_metrics.tasks]
        memory_usages = [t.peak_memory_mb for t in pipeline_metrics.tasks]

        # 检查数据倾斜
        max_duration = max(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        avg_duration = statistics.mean(durations) if durations else 0
        skew_ratio = max_duration / min_duration if min_duration > 0 else 0

        all_bottlenecks = []
        all_recommendations = []
        for analysis in task_analyses:
            all_bottlenecks.extend(analysis['bottlenecks'])
            all_recommendations.extend(analysis['recommendations'])

        # 管道级别的分析
        if skew_ratio > self.thresholds['skew_warning'] and len(durations) > 1:
            all_recommendations.append(
                PerformanceRecommendation(
                    level=PerformanceLevel.WARNING,
                    category='skew',
                    message=f"检测到数据倾斜: 最快/最慢任务比率 {skew_ratio:.1f}x",
                    suggestion="重新分区数据、调整并行度、考虑加盐处理",
                    priority=2
                )
            )

        # 总体性能评级
        critical_count = sum(1 for r in all_recommendations if r.level == PerformanceLevel.CRITICAL)
        warning_count = sum(1 for r in all_recommendations if r.level == PerformanceLevel.WARNING)

        if critical_count > 0:
            overall_level = PerformanceLevel.CRITICAL
        elif warning_count > 2:
            overall_level = PerformanceLevel.WARNING
        elif warning_count > 0:
            overall_level = PerformanceLevel.NORMAL
        else:
            overall_level = PerformanceLevel.GOOD

        # 按优先级排序建议
        all_recommendations.sort(key=lambda x: x.priority)

        return {
            'pipeline_id': pipeline_metrics.pipeline_id,
            'execution_id': pipeline_metrics.execution_id,
            'total_duration_ms': pipeline_metrics.total_duration_ms,
            'total_duration_formatted': str(timedelta(milliseconds=pipeline_metrics.total_duration_ms)),
            'overall_performance_level': overall_level.value,
            'summary': {
                'total_tasks': len(pipeline_metrics.tasks),
                'total_input_rows': pipeline_metrics.total_input_rows,
                'total_output_rows': pipeline_metrics.total_output_rows,
                'total_data_processed_mb': round(pipeline_metrics.total_data_processed_mb, 2),
                'avg_throughput_rows_per_sec': round(statistics.mean(throughputs) if throughputs else 0, 2),
                'avg_task_duration_ms': round(avg_duration, 2),
                'max_task_duration_ms': round(max_duration, 2),
                'min_task_duration_ms': round(min_duration, 2),
                'peak_memory_mb': round(pipeline_metrics.peak_memory_mb, 2),
                'avg_cpu_usage_percent': round(pipeline_metrics.avg_cpu_usage_percent, 2),
            },
            'bottlenecks': list(set(all_bottlenecks)),
            'task_performances': task_analyses,
            'recommendations': [
                {
                    'level': r.level.value,
                    'category': r.category,
                    'message': r.message,
                    'suggestion': r.suggestion,
                    'priority': r.priority
                }
                for r in all_recommendations
            ],
            'critical_issues_count': critical_count,
            'warning_issues_count': warning_count,
        }

    def generate_comparison_report(self, executions: List[PipelineMetrics]) -> Dict[str, Any]:
        """生成多次执行的对比报告"""
        if len(executions) < 2:
            return {"error": "至少需要2次执行数据进行对比"}

        durations = [e.total_duration_ms for e in executions]
        throughputs = []
        for e in executions:
            task_throughputs = [self.calculate_throughput(t) for t in e.tasks]
            throughputs.append(statistics.mean(task_throughputs) if task_throughputs else 0)

        # 趋势分析
        duration_trend = "improving" if durations[-1] < durations[0] else "degrading" if durations[-1] > durations[0] else "stable"
        throughput_trend = "improving" if throughputs[-1] > throughputs[0] else "degrading" if throughputs[-1] < throughputs[0] else "stable"

        return {
            "total_executions_compared": len(executions),
            "comparison_period": {
                "first_execution": executions[0].start_time.isoformat(),
                "last_execution": executions[-1].start_time.isoformat(),
            },
            "duration_analysis": {
                "min_ms": min(durations),
                "max_ms": max(durations),
                "avg_ms": statistics.mean(durations),
                "trend": duration_trend,
                "change_percent": round(((durations[-1] - durations[0]) / durations[0]) * 100, 2) if durations[0] > 0 else 0,
            },
            "throughput_analysis": {
                "min_rows_per_sec": min(throughputs),
                "max_rows_per_sec": max(throughputs),
                "avg_rows_per_sec": statistics.mean(throughputs),
                "trend": throughput_trend,
                "change_percent": round(((throughputs[-1] - throughputs[0]) / throughputs[0]) * 100, 2) if throughputs[0] > 0 else 0,
            },
            "recommendations": self._generate_comparison_recommendations(durations, throughputs)
        }

    def _generate_comparison_recommendations(self, durations, throughputs):
        """生成对比建议"""
        recommendations = []

        # 执行时间趋势
        if len(durations) >= 3:
            recent_avg = statistics.mean(durations[-2:])
            older_avg = statistics.mean(durations[:-2])
            if recent_avg > older_avg * 1.2:
                recommendations.append({
                    "level": "warning",
                    "type": "performance_degradation",
                    "message": "检测到性能下降趋势",
                    "suggestion": "检查系统资源、数据量增长、依赖服务状态"
                })

        return recommendations


def create_task_metrics_from_execution(execution_data: Dict[str, Any]) -> TaskMetrics:
    """从执行数据创建任务指标"""
    return TaskMetrics(
        task_id=execution_data.get('task_id', ''),
        task_name=execution_data.get('task_name', ''),
        execution_id=execution_data.get('execution_id', ''),
        start_time=datetime.fromisoformat(execution_data.get('start_time')) if execution_data.get('start_time') else datetime.now(),
        end_time=datetime.fromisoformat(execution_data.get('end_time')) if execution_data.get('end_time') else None,
        duration_ms=execution_data.get('duration_ms', 0),
        status=execution_data.get('status', 'PENDING'),
        input_rows=execution_data.get('input_rows', 0),
        output_rows=execution_data.get('output_rows', 0),
        error_count=execution_data.get('error_count', 0),
        retry_count=execution_data.get('retry_count', 0),
        memory_usage_mb=execution_data.get('memory_usage_mb', 0),
        peak_memory_mb=execution_data.get('peak_memory_mb', 0),
        cpu_usage_percent=execution_data.get('cpu_usage_percent', 0),
    )


def generate_performance_report(execution_data: List[Dict[str, Any]], pipeline_id: str = None) -> Dict[str, Any]:
    """生成性能报告的便捷函数"""
    analyzer = PerformanceAnalyzer()

    # 转换数据
    task_metrics_list = [create_task_metrics_from_execution(td) for td in execution_data]

    # 计算汇总指标
    total_duration = sum(t.duration_ms for t in task_metrics_list)
    total_input = sum(t.input_rows for t in task_metrics_list)
    total_output = sum(t.output_rows for t in task_metrics_list)

    pipeline_metrics = PipelineMetrics(
        pipeline_id=pipeline_id or "unknown",
        execution_id=task_metrics_list[0].execution_id if task_metrics_list else "unknown",
        start_time=min(t.start_time for t in task_metrics_list) if task_metrics_list else datetime.now(),
        total_duration_ms=total_duration,
        tasks=task_metrics_list,
        total_input_rows=total_input,
        total_output_rows=total_output,
        peak_memory_mb=max(t.peak_memory_mb for t in task_metrics_list) if task_metrics_list else 0,
        avg_cpu_usage_percent=statistics.mean(t.cpu_usage_percent for t in task_metrics_list) if task_metrics_list else 0,
    )

    return analyzer.analyze_pipeline_performance(pipeline_metrics)
