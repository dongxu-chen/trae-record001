import logging
import json
import sys
import yaml
from datetime import datetime, timedelta
from typing import List, Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box

from .prometheus_client import PrometheusClient
from .data_collector import DataCollector
from .statistics_analyzer import StatisticsAnalyzer
from .vpa_recommender import VPARecommender
from .hpa_recommender import HPARecommender
from .cost_estimator import CostEstimator, ResourceCost, ClusterManagementConfig
from .seasonality_detector import SeasonalityDetector
from .waste_analyzer import WasteAnalyzer, WasteCategory
from .recommendation_simulator import RecommendationSimulator, SimulationConfig, SimulationStatus
from . import __version__

console = Console()
logger = logging.getLogger(__name__)


def format_cpu(cores: float) -> str:
    if cores >= 1:
        return f"{cores:.3f} cores"
    else:
        return f"{cores * 1000:.1f}m"


def format_memory(bytes_val: float) -> str:
    if bytes_val >= 1024 ** 4:
        return f"{bytes_val / (1024 ** 4):.2f} Ti"
    elif bytes_val >= 1024 ** 3:
        return f"{bytes_val / (1024 ** 3):.2f} Gi"
    elif bytes_val >= 1024 ** 2:
        return f"{bytes_val / (1024 ** 2):.2f} Mi"
    elif bytes_val >= 1024:
        return f"{bytes_val / 1024:.2f} Ki"
    else:
        return f"{bytes_val:.0f} B"


def format_confidence(confidence: float) -> str:
    if confidence >= 0.9:
        return f"[green]{confidence * 100:.0f}%[/green]"
    elif confidence >= 0.7:
        return f"[yellow]{confidence * 100:.0f}%[/yellow]"
    else:
        return f"[red]{confidence * 100:.0f}%[/red]"


def load_config(config_path: Optional[str] = None) -> dict:
    import os
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"无法加载配置文件 {config_path}: {e}")
    default_path = os.path.join(os.getcwd(), 'config.yaml')
    if os.path.exists(default_path):
        try:
            with open(default_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception as e:
            logger.warning(f"无法加载默认配置文件: {e}")
    return {}


@click.group()
@click.version_option(__version__, "-V", "--version")
@click.option("--prometheus-url", envvar="PROMETHEUS_URL", help="Prometheus server URL")
@click.option("--prometheus-token", envvar="PROMETHEUS_TOKEN", help="Prometheus auth token")
@click.option("--prometheus-username", envvar="PROMETHEUS_USERNAME", help="Prometheus username")
@click.option("--prometheus-password", envvar="PROMETHEUS_PASSWORD", help="Prometheus password")
@click.option("--verify-ssl/--no-verify-ssl", default=True, help="Verify SSL certificate")
@click.option("--config", "config_path", help="配置文件路径")
@click.option("--cluster-total-cores", type=float, help="集群总CPU核数，用于集群管理费分摊")
@click.option("--no-cluster-mgmt-cost", is_flag=True, help="禁用集群管理费计算")
@click.option("--verbose", count=True, help="Increase output verbosity")
@click.pass_context
def cli(ctx, prometheus_url, prometheus_token, prometheus_username, prometheus_password, 
        verify_ssl, config_path, cluster_total_cores, no_cluster_mgmt_cost, verbose):
    """Kubernetes资源推荐工具 - 基于VPA算法和Prometheus数据的智能资源分析"""

    logging_level = logging.WARNING
    if verbose == 1:
        logging_level = logging.INFO
    elif verbose >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        level=logging_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    ctx.ensure_object(dict)

    output_format = "table"
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg in ["--output", "-o"] and i + 1 < len(argv):
            output_format = argv[i + 1]
            break

    quiet_mode = output_format != "table"

    config = load_config(config_path)
    vpa_config = config.get('vpa', {})
    cost_config = config.get('cost', {})
    cluster_mgmt_config = cost_config.get('cluster_management', {})

    percentile_config = vpa_config.get('percentile_config', None)
    memory_oom_buffer_percent = vpa_config.get('memory_oom_buffer_percent', 10.0)

    if not no_cluster_mgmt_cost and cluster_mgmt_config.get('enabled', False):
        cm_config = ClusterManagementConfig(
            enabled=True,
            monthly_fixed_cost=cluster_mgmt_config.get('monthly_fixed_cost', 100.0),
            allocation_method=cluster_mgmt_config.get('allocation_method', 'by_core_ratio'),
            min_allocation_per_pod=cluster_mgmt_config.get('min_allocation_per_pod', 5.0),
        )
    else:
        cm_config = ClusterManagementConfig(enabled=False)

    if prometheus_url:
        try:
            ctx.obj["prometheus"] = PrometheusClient(
                url=prometheus_url,
                token=prometheus_token,
                username=prometheus_username,
                password=prometheus_password,
                verify_ssl=verify_ssl,
            )
            if not ctx.obj["prometheus"].health_check():
                if not quiet_mode:
                    console.print("[yellow]警告: 无法连接到Prometheus服务器，将使用演示模式[/yellow]")
                ctx.obj["prometheus"] = None
        except Exception as e:
            if not quiet_mode:
                console.print(f"[yellow]警告: Prometheus连接失败 ({e})，将使用演示模式[/yellow]")
            ctx.obj["prometheus"] = None
    else:
        if not quiet_mode:
            console.print("[yellow]提示: 未指定Prometheus URL，将使用演示模式[/yellow]")
        ctx.obj["prometheus"] = None

    ctx.obj["analyzer"] = StatisticsAnalyzer()
    ctx.obj["vpa"] = VPARecommender(
        ctx.obj["analyzer"],
        percentile_config=percentile_config,
        memory_oom_buffer_percent=memory_oom_buffer_percent,
    )
    ctx.obj["hpa"] = HPARecommender(ctx.obj["analyzer"])
    ctx.obj["cost"] = CostEstimator(cluster_management_config=cm_config)
    ctx.obj["seasonality"] = SeasonalityDetector(ctx.obj["analyzer"])
    ctx.obj["waste"] = WasteAnalyzer(ctx.obj["analyzer"])
    ctx.obj["simulator"] = RecommendationSimulator(ctx.obj["analyzer"])
    
    if cluster_total_cores:
        ctx.obj["cost"].set_cluster_total_cpu_cores(cluster_total_cores)


@cli.command()
@click.option("-n", "--namespace", required=True, help="Kubernetes命名空间")
@click.option("-p", "--pod", required=True, help="Pod名称")
@click.option("-d", "--days", default=7, type=int, help="分析历史数据的天数")
@click.option("-s", "--step", default="1m", help="数据采样间隔")
@click.option("--workload-type", type=click.Choice(["stateless", "stateful", "critical"]),
              default="stateless", help="工作负载类型")
@click.option("--risk-tolerance", type=click.Choice(["low", "medium", "high"]),
              default="medium", help="风险容忍度")
@click.option("--output", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="输出格式")
@click.pass_context
def vpa(ctx, namespace, pod, days, step, workload_type, risk_tolerance, output):
    """垂直资源推荐 - 为单个Pod推荐CPU和内存资源请求/限制"""

    quiet_mode = output != "table"

    if not quiet_mode:
        console.print(Panel.fit(
            f"[bold cyan]垂直资源推荐 (VPA)[/bold cyan]\n"
            f"命名空间: [green]{namespace}[/green] | Pod: [green]{pod}[/green] | 分析周期: [green]{days}天[/green]",
            border_style="cyan",
        ))

    prometheus = ctx.obj["prometheus"]
    vpa_recommender = ctx.obj["vpa"]
    cost_estimator = ctx.obj["cost"]

    if prometheus:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        collector = DataCollector(prometheus)
        pod_data = collector.collect_pod_data(namespace, pod, start_time, end_time, step)

        if not pod_data:
            if not quiet_mode:
                console.print("[red]错误: 无法收集Pod数据[/red]")
            return

        recommendation = vpa_recommender.recommend_for_pod(pod_data, workload_type, risk_tolerance)
    else:
        from .demo_data_generator import generate_demo_pod_data
        pod_data = generate_demo_pod_data(namespace, pod)
        recommendation = vpa_recommender.recommend_for_pod(pod_data, workload_type, risk_tolerance)

    if not recommendation:
        if not quiet_mode:
            console.print("[red]错误: 无法生成资源推荐[/red]")
        return

    if output == "table":
        display_vpa_recommendation(recommendation, cost_estimator)
    elif output == "json":
        print(json.dumps(recommendation_to_dict(recommendation), indent=2, ensure_ascii=False))
    elif output == "yaml":
        print(yaml.dump(recommendation_to_dict(recommendation), allow_unicode=True, sort_keys=False))


@cli.command()
@click.option("-n", "--namespace", required=True, help="Kubernetes命名空间")
@click.option("-d", "--deployment", required=True, help="Deployment名称")
@click.option("-a", "--days", default=7, type=int, help="分析历史数据的天数")
@click.option("--cpu-target", default=70.0, type=float, help="CPU目标利用率百分比")
@click.option("--memory-target", default=75.0, type=float, help="内存目标利用率百分比")
@click.option("--min-replicas", default=1, type=int, help="最小副本数")
@click.option("--max-replicas", default=10, type=int, help="最大副本数")
@click.option("--workload-type", type=click.Choice(["stateless", "stateful", "critical"]),
              default="stateless", help="工作负载类型")
@click.option("--risk-tolerance", type=click.Choice(["low", "medium", "high"]),
              default="medium", help="风险容忍度")
@click.option("--output", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="输出格式")
@click.pass_context
def hpa(ctx, namespace, deployment, days, cpu_target, memory_target, min_replicas, max_replicas,
        workload_type, risk_tolerance, output):
    """水平资源推荐 - 为Deployment推荐副本数"""

    quiet_mode = output != "table"

    if not quiet_mode:
        console.print(Panel.fit(
            f"[bold cyan]水平资源推荐 (HPA)[/bold cyan]\n"
            f"命名空间: [green]{namespace}[/green] | Deployment: [green]{deployment}[/green] | 分析周期: [green]{days}天[/green]",
            border_style="cyan",
        ))

    prometheus = ctx.obj["prometheus"]
    hpa_recommender = ctx.obj["hpa"]
    cost_estimator = ctx.obj["cost"]

    hpa_recommender.cpu_target_utilization = cpu_target
    hpa_recommender.memory_target_utilization = memory_target
    hpa_recommender.min_replicas = min_replicas
    hpa_recommender.max_replicas = max_replicas

    if prometheus:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        collector = DataCollector(prometheus)
        deployment_data = collector.collect_deployment_data(namespace, deployment, start_time, end_time)

        if not deployment_data or not deployment_data.pods:
            if not quiet_mode:
                console.print("[red]错误: 无法收集Deployment数据[/red]")
            return

        sample_pod = deployment_data.pods[0]
        cpu_request = sample_pod.cpu_request or 0.5
        memory_request = sample_pod.memory_request or 512 * 1024 * 1024

        recommendation = hpa_recommender.recommend_for_deployment(
            deployment_data, cpu_request, memory_request,
            workload_type=workload_type, risk_tolerance=risk_tolerance
        )
    else:
        from .demo_data_generator import generate_demo_deployment_data
        deployment_data = generate_demo_deployment_data(namespace, deployment)
        cpu_request = deployment_data.pods[0].cpu_request if deployment_data.pods else 0.5
        memory_request = deployment_data.pods[0].memory_request if deployment_data.pods else 1 * 1024 * 1024 * 1024
        recommendation = hpa_recommender.recommend_for_deployment(
            deployment_data, cpu_request, memory_request,
            workload_type=workload_type, risk_tolerance=risk_tolerance
        )

    if not recommendation:
        if not quiet_mode:
            console.print("[red]错误: 无法生成副本数推荐[/red]")
        return

    if output == "table":
        display_hpa_recommendation(recommendation, cpu_request, memory_request, cost_estimator)
    elif output == "json":
        print(json.dumps(hpa_recommendation_to_dict(recommendation), indent=2, ensure_ascii=False))
    elif output == "yaml":
        print(yaml.dump(hpa_recommendation_to_dict(recommendation), allow_unicode=True, sort_keys=False))


@cli.command()
@click.option("-n", "--namespace", required=True, help="Kubernetes命名空间")
@click.option("-d", "--deployment", required=True, help="Deployment名称")
@click.option("-a", "--days", default=7, type=int, help="分析历史数据的天数")
@click.option("--cloud-provider", type=click.Choice(["aws", "gcp", "azure", "alibaba", "onprem"]),
              default="aws", help="云服务提供商 (用于成本计算)")
@click.option("--workload-type", type=click.Choice(["stateless", "stateful", "critical"]),
              default="stateless", help="工作负载类型")
@click.option("--risk-tolerance", type=click.Choice(["low", "medium", "high"]),
              default="medium", help="风险容忍度")
@click.option("--output", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="输出格式")
@click.pass_context
def analyze(ctx, namespace, deployment, days, cloud_provider, workload_type, risk_tolerance, output):
    """综合分析 - 同时提供垂直和水平资源推荐及成本预估"""

    quiet_mode = output != "table"

    if not quiet_mode:
        console.print(Panel.fit(
            f"[bold cyan]综合资源分析[/bold cyan]\n"
            f"命名空间: [green]{namespace}[/green] | Deployment: [green]{deployment}[/green]\n"
            f"分析周期: [green]{days}天[/green] | 云服务商: [green]{cloud_provider.upper()}[/green]",
            border_style="cyan",
        ))

    prometheus = ctx.obj["prometheus"]
    analyzer = ctx.obj["analyzer"]
    vpa_recommender = ctx.obj["vpa"]
    hpa_recommender = ctx.obj["hpa"]
    cost_estimator = ctx.obj["cost"]

    cost_config = CostEstimator.get_cloud_provider_pricing(cloud_provider)
    cost_estimator.cost_config = cost_config

    vertical_recommendations = []
    horizontal_recommendation = None

    if prometheus:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)

        collector = DataCollector(prometheus)
        deployment_data = collector.collect_deployment_data(namespace, deployment, start_time, end_time)

        if deployment_data and deployment_data.pods:
            for pod_data in deployment_data.pods:
                vpa_rec = vpa_recommender.recommend_for_pod(pod_data, workload_type, risk_tolerance)
                if vpa_rec:
                    vertical_recommendations.append(vpa_rec)

            if vertical_recommendations:
                cpu_request_per_pod = vertical_recommendations[0].cpu.target_request
                memory_request_per_pod = vertical_recommendations[0].memory.target_request

                horizontal_recommendation = hpa_recommender.recommend_for_deployment(
                    deployment_data, cpu_request_per_pod, memory_request_per_pod,
                    workload_type=workload_type, risk_tolerance=risk_tolerance
                )
    else:
        from .demo_data_generator import generate_demo_full_analysis
        vertical_recommendations, horizontal_recommendation, cpu_request, memory_request = (
            generate_demo_full_analysis(namespace, deployment)
        )

        for rec in vertical_recommendations:
            vpa_rec = vpa_recommender.recommend_for_pod(rec, workload_type, risk_tolerance)
            if vpa_rec:
                vertical_recommendations[vertical_recommendations.index(rec)] = vpa_rec

    if not vertical_recommendations:
        if not quiet_mode:
            console.print("[red]错误: 无法生成任何推荐[/red]")
        return

    if output == "table":
        display_full_analysis(vertical_recommendations, horizontal_recommendation, cost_estimator)
    else:
        result = {
            "vertical_recommendations": [
                recommendation_to_dict(r) for r in vertical_recommendations
            ],
        }
        if horizontal_recommendation:
            result["horizontal_recommendation"] = hpa_recommendation_to_dict(horizontal_recommendation)

        cost_analysis = cost_estimator.estimate_combined_cost(
            vertical_recommendations, horizontal_recommendation
        )
        result["cost_analysis"] = cost_estimator.generate_cost_summary(cost_analysis)

        if output == "json":
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif output == "yaml":
            print(yaml.dump(result, allow_unicode=True, sort_keys=False))


@cli.command(name="list")
@click.option("-n", "--namespace", help="Kubernetes命名空间 (可选)")
@click.option("--resource-type", type=click.Choice(["pods", "deployments", "all"]),
              default="all", help="资源类型")
@click.pass_context
def list_resources(ctx, namespace, resource_type):
    """列出Kubernetes中的Pods和Deployments"""

    prometheus = ctx.obj["prometheus"]

    if not prometheus:
        console.print("[yellow]演示模式 - 列出示例资源[/yellow]")
        display_demo_resources()
        return

    console.print(Panel.fit(
        f"[bold cyan]Kubernetes资源列表[/bold cyan]\n"
        f"命名空间: [green]{namespace or '全部'}[/green] | 资源类型: [green]{resource_type}[/green]",
        border_style="cyan",
    ))

    try:
        if resource_type in ["pods", "all"]:
            pods = prometheus.get_all_pods(namespace)
            if pods:
                table = Table(title="Pods", box=box.ROUNDED)
                table.add_column("命名空间", style="cyan")
                table.add_column("Pod名称", style="green")
                table.add_column("所属节点")
                table.add_column("控制器")

                for pod in pods:
                    table.add_row(
                        pod["namespace"], pod["pod"],
                        pod.get("node", "N/A"),
                        pod.get("created_by_name", "N/A")
                    )
                console.print(table)
            else:
                console.print("[yellow]未找到任何Pod[/yellow]")

        if resource_type in ["deployments", "all"]:
            deployments = prometheus.get_all_deployments(namespace)
            if deployments:
                table = Table(title="Deployments", box=box.ROUNDED)
                table.add_column("命名空间", style="cyan")
                table.add_column("Deployment名称", style="green")

                for dep in deployments:
                    table.add_row(dep["namespace"], dep["deployment"])
                console.print(table)
            else:
                console.print("[yellow]未找到任何Deployment[/yellow]")

    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")


def display_vpa_recommendation(recommendation, cost_estimator):
    """显示VPA推荐结果"""

    if recommendation.warnings:
        for warning in recommendation.warnings:
            console.print(f"[yellow]⚠️  {warning}[/yellow]")

    cost_analysis = cost_estimator.estimate_vertical_cost(recommendation)

    table = Table(title="资源推荐详情", box=box.ROUNDED, show_header=True)
    table.add_column("资源类型", style="bold cyan", width=12)
    table.add_column("当前请求", justify="right")
    table.add_column("推荐请求", justify="right", style="green")
    table.add_column("推荐限制", justify="right")
    table.add_column("置信区间", justify="center")
    table.add_column("置信度", justify="center")

    table.add_row(
        "CPU",
        format_cpu(recommendation.current_cpu_request or 0),
        format_cpu(recommendation.cpu.target_request),
        format_cpu(recommendation.cpu.target_limit),
        f"{format_cpu(recommendation.cpu.lower_bound)} ~ {format_cpu(recommendation.cpu.upper_bound)}",
        format_confidence(recommendation.cpu.confidence),
    )

    table.add_row(
        "内存",
        format_memory(recommendation.current_memory_request or 0),
        format_memory(recommendation.memory.target_request),
        format_memory(recommendation.memory.target_limit),
        f"{format_memory(recommendation.memory.lower_bound)} ~ {format_memory(recommendation.memory.upper_bound)}",
        format_confidence(recommendation.memory.confidence),
    )

    console.print(table)

    details_table = Table(title="推荐详情", box=box.ROUNDED)
    details_table.add_column("属性", style="bold")
    details_table.add_column("CPU", justify="right")
    details_table.add_column("内存", justify="right")

    details_table.add_row(
        "使用百分位数",
        f"{recommendation.cpu.percentile_used}%",
        f"{recommendation.memory.percentile_used}%",
    )
    details_table.add_row(
        "安全边际",
        f"{recommendation.cpu.safety_margin:.2f}x",
        f"{recommendation.memory.safety_margin:.2f}x",
    )
    details_table.add_row(
        "估算方法",
        recommendation.cpu.estimation_method,
        recommendation.memory.estimation_method,
    )
    if recommendation.memory.oom_buffer_percent > 0:
        details_table.add_row(
            "OOM缓冲",
            "-",
            f"+{recommendation.memory.oom_buffer_percent:.0f}% ({format_memory(recommendation.memory.oom_buffer_amount)})",
        )

    console.print(details_table)

    if cost_analysis:
        cost_table = Table(title="成本分析", box=box.ROUNDED)
        cost_table.add_column("项目", style="bold")
        cost_table.add_column("当前 (每月)", justify="right")
        cost_table.add_column("推荐 (每月)", justify="right")
        cost_table.add_column("节省 (每月)", justify="right", style="green")

        cost_table.add_row(
            "CPU成本",
            f"${cost_analysis.cpu_current_cost:.2f}",
            f"${cost_analysis.cpu_recommended_cost:.2f}",
            f"${cost_analysis.cpu_savings:+.2f}",
        )
        cost_table.add_row(
            "内存成本",
            f"${cost_analysis.memory_current_cost:.2f}",
            f"${cost_analysis.memory_recommended_cost:.2f}",
            f"${cost_analysis.memory_savings:+.2f}",
        )
        if cost_analysis.cluster_management:
            cm = cost_analysis.cluster_management
            cost_table.add_row(
                "集群管理费",
                f"${cm.current_monthly_cost:.2f}",
                f"${cm.recommended_monthly_cost:.2f}",
                f"${cm.monthly_savings:+.2f}",
            )
        cost_table.add_row(
            "总计",
            f"${cost_analysis.current_monthly_cost:.2f}",
            f"${cost_analysis.recommended_monthly_cost:.2f}",
            f"[bold green]${cost_analysis.monthly_savings:+.2f} ({cost_analysis.savings_percent:+.1f}%)[/bold green]",
        )

        console.print(cost_table)

        if cost_analysis.monthly_savings > 0:
            console.print(Panel.fit(
                f"[bold green]🎉 预计每月节省 ${cost_analysis.monthly_savings:.2f} "
                f"({cost_analysis.savings_percent:.1f}%)[/bold green]\n"
                f"[dim]年度预计节省: ${cost_analysis.monthly_savings * 12:.2f}[/dim]",
                border_style="green",
            ))
        elif cost_analysis.monthly_savings < 0:
            console.print(Panel.fit(
                f"[bold yellow]⚠️  需要增加资源投入: ${abs(cost_analysis.monthly_savings):.2f}/月[/bold yellow]\n"
                f"[dim]以提高稳定性和应对流量增长[/dim]",
                border_style="yellow",
            ))
        else:
            console.print(Panel.fit(
                "[bold green]✓ 当前资源配置已处于最优状态[/bold green]",
                border_style="green",
            ))


def display_hpa_recommendation(recommendation, cpu_request, memory_request, cost_estimator):
    """显示HPA推荐结果"""

    if recommendation.warnings:
        for warning in recommendation.warnings:
            console.print(f"[yellow]⚠️  {warning}[/yellow]")

    rec = recommendation.recommendation
    cost_analysis = cost_estimator.estimate_horizontal_cost(recommendation, cpu_request, memory_request)

    table = Table(title="副本数推荐", box=box.ROUNDED)
    table.add_column("项目", style="bold cyan")
    table.add_column("值", justify="right")

    table.add_row("当前副本数", str(rec.current_replicas))
    table.add_row("推荐副本数", f"[bold green]{rec.target_replicas}[/bold green]")
    table.add_row("建议范围", f"{rec.min_replicas} ~ {rec.max_replicas}")
    table.add_row("置信区间", f"{rec.lower_bound} ~ {rec.upper_bound}")
    table.add_row("主要驱动资源", rec.driving_resource.upper())
    table.add_row("置信度", format_confidence(rec.confidence))
    table.add_row("CPU目标利用率", f"{rec.cpu_utilization_target:.0f}%")
    table.add_row("内存目标利用率", f"{rec.memory_utilization_target:.0f}%")

    console.print(table)

    console.print(Panel.fit(
        "\n".join(f"• {r}" for r in rec.reasoning),
        title="推荐依据",
        border_style="blue",
    ))

    if cost_analysis:
        cost_table = Table(title="成本分析", box=box.ROUNDED)
        cost_table.add_column("项目", style="bold")
        cost_table.add_column("当前 (每月)", justify="right")
        cost_table.add_column("推荐 (每月)", justify="right")
        cost_table.add_column("变化", justify="right")

        change = rec.target_replicas - rec.current_replicas

        cost_table.add_row(
            "副本数",
            str(rec.current_replicas),
            f"[bold]{rec.target_replicas}[/bold]",
            f"{change:+.0f}",
        )
        cost_table.add_row(
            "CPU成本",
            f"${cost_analysis.cpu_current_cost:.2f}",
            f"${cost_analysis.cpu_recommended_cost:.2f}",
            f"${cost_analysis.cpu_savings:+.2f}",
        )
        cost_table.add_row(
            "内存成本",
            f"${cost_analysis.memory_current_cost:.2f}",
            f"${cost_analysis.memory_recommended_cost:.2f}",
            f"${cost_analysis.memory_savings:+.2f}",
        )
        if cost_analysis.cluster_management:
            cm = cost_analysis.cluster_management
            cost_table.add_row(
                "集群管理费",
                f"${cm.current_monthly_cost:.2f}",
                f"${cm.recommended_monthly_cost:.2f}",
                f"${cm.monthly_savings:+.2f}",
            )
        cost_table.add_row(
            "总成本",
            f"${cost_analysis.current_monthly_cost:.2f}",
            f"${cost_analysis.recommended_monthly_cost:.2f}",
            f"[bold]${cost_analysis.monthly_savings:+.2f} ({cost_analysis.savings_percent:+.1f}%)[/bold]",
        )

        console.print(cost_table)


def display_full_analysis(vertical_recommendations, horizontal_recommendation, cost_estimator):
    """显示综合分析结果"""

    console.print("\n[bold cyan]=== 1. 垂直资源推荐 (VPA) ===[/bold cyan]")

    if len(vertical_recommendations) == 1:
        display_vpa_recommendation(vertical_recommendations[0], cost_estimator)
    else:
        table = Table(title="各Pod资源推荐汇总", box=box.ROUNDED)
        table.add_column("Pod", style="cyan")
        table.add_column("CPU 当前", justify="right")
        table.add_column("CPU 推荐", justify="right", style="green")
        table.add_column("内存 当前", justify="right")
        table.add_column("内存 推荐", justify="right", style="green")

        for rec in vertical_recommendations:
            table.add_row(
                rec.pod,
                format_cpu(rec.current_cpu_request or 0),
                format_cpu(rec.cpu.target_request),
                format_memory(rec.current_memory_request or 0),
                format_memory(rec.memory.target_request),
            )
        console.print(table)

    if horizontal_recommendation:
        console.print("\n[bold cyan]=== 2. 水平资源推荐 (HPA) ===[/bold cyan]")
        sample_rec = vertical_recommendations[0]
        display_hpa_recommendation(
            horizontal_recommendation,
            sample_rec.cpu.target_request,
            sample_rec.memory.target_request,
            cost_estimator,
        )

    cost_analysis = cost_estimator.estimate_combined_cost(
        vertical_recommendations, horizontal_recommendation
    )

    console.print("\n[bold cyan]=== 3. 综合成本分析 ===[/bold cyan]")
    summary = cost_estimator.generate_cost_summary(cost_analysis)

    total_table = Table(title="总成本预估", box=box.ROUNDED)
    total_table.add_column("项目", style="bold")
    total_table.add_column("金额", justify="right")

    total_table.add_row(
        "当前月度成本",
        f"${summary['total_current_monthly_cost']:.2f}",
    )
    total_table.add_row(
        "推荐月度成本",
        f"${summary['total_recommended_monthly_cost']:.2f}",
    )
    total_table.add_row(
        "月度节省",
        f"[bold green]${summary['total_monthly_savings']:.2f} ({summary['total_savings_percent']:.1f}%)[/bold green]",
    )
    total_table.add_row(
        "年度预计节省",
        f"[bold green]${summary['annualized']['savings']:.2f}[/bold green]",
    )

    if summary.get('cluster_management'):
        cm = summary['cluster_management']
        total_table.add_row(
            "集群管理费分摊",
            f"${cm['current_monthly_cost']:.2f} → ${cm['recommended_monthly_cost']:.2f}",
        )

    console.print(total_table)

    if "breakdown" in summary and summary["breakdown"]:
        breakdown_table = Table(title="成本节省明细", box=box.ROUNDED)
        breakdown_table.add_column("优化类型", style="cyan")
        breakdown_table.add_column("月度节省", justify="right")
        breakdown_table.add_column("节省比例", justify="right")
        breakdown_table.add_column("置信度", justify="center")

        if "vertical" in summary["breakdown"]:
            v = summary["breakdown"]["vertical"]
            breakdown_table.add_row(
                "垂直优化 (资源)",
                f"${v['monthly_savings']:.2f}",
                f"{v['savings_percent']:+.1f}%",
                format_confidence(v["confidence"]),
            )

        if "horizontal" in summary["breakdown"]:
            h = summary["breakdown"]["horizontal"]
            breakdown_table.add_row(
                "水平优化 (副本)",
                f"${h['monthly_savings']:.2f}",
                f"{h['savings_percent']:+.1f}%",
                format_confidence(h["confidence"]),
            )

        console.print(breakdown_table)


def display_demo_resources():
    """显示演示资源"""
    table = Table(title="演示环境资源", box=box.ROUNDED)
    table.add_column("命名空间", style="cyan")
    table.add_column("资源类型", style="yellow")
    table.add_column("资源名称", style="green")

    demo_data = [
        ("default", "Deployment", "web-app"),
        ("default", "Deployment", "api-service"),
        ("default", "Deployment", "worker"),
        ("production", "Deployment", "payment-gateway"),
        ("production", "Deployment", "user-service"),
        ("monitoring", "Deployment", "prometheus"),
        ("monitoring", "Deployment", "grafana"),
    ]

    for ns, typ, name in demo_data:
        table.add_row(ns, typ, name)

    console.print(table)
    console.print("[dim]使用 --prometheus-url 连接到真实的Prometheus服务器[/dim]")


def format_category(category: WasteCategory) -> str:
    styles = {
        WasteCategory.IDLE: ("red", "❌"),
        WasteCategory.UNDERUTILIZED: ("yellow", "⚠️"),
        WasteCategory.OPTIMAL: ("green", "✅"),
        WasteCategory.OVERUTILIZED: ("orange", "⚠️"),
        WasteCategory.CRITICAL: ("red", "🚨"),
    }
    color, icon = styles.get(category, ("white", "?"))
    names = {
        WasteCategory.IDLE: "闲置",
        WasteCategory.UNDERUTILIZED: "低利用率",
        WasteCategory.OPTIMAL: "最优",
        WasteCategory.OVERUTILIZED: "过度利用",
        WasteCategory.CRITICAL: "严重不足",
    }
    return f"[{color}]{icon} {names.get(category, category.value)}[/{color}]"


def display_seasonality_analysis(cpu_analysis, memory_analysis, namespace, pod):
    console.print(Panel.fit(
        f"[bold cyan]📊 季节性分析 - {namespace}/{pod}[/bold cyan]",
        border_style="cyan",
    ))

    from .seasonality_detector import SeasonalPattern
    for resource, analysis in [("CPU", cpu_analysis), ("内存", memory_analysis)]:
        table = Table(title=f"{resource}季节性分析", box=box.ROUNDED)
        table.add_column("指标", style="bold")
        table.add_column("值")

        pattern_names = {
            SeasonalPattern.DAILY: "日度周期",
            SeasonalPattern.WEEKLY: "周度周期",
            SeasonalPattern.HOURLY: "小时级周期",
            SeasonalPattern.NONE: "无明显模式",
        }

        table.add_row(
            "检测到的模式",
            pattern_names.get(analysis.pattern, str(analysis.pattern)),
        )
        table.add_row("置信度", f"{analysis.confidence * 100:.0f}%")
        if analysis.dominant_period_hours:
            table.add_row("主周期时长", f"{analysis.dominant_period_hours:.1f} 小时")
        table.add_row("季节性强度", f"{analysis.seasonal_strength * 100:.0f}%")
        table.add_row("峰值资源倍数", f"{analysis.peak_resource_multiplier:.2f}x")
        table.add_row("谷值资源倍数", f"{analysis.trough_resource_multiplier:.2f}x")
        table.add_row(
            "强季节性",
            "[green]是[/green]" if analysis.has_strong_seasonality else "[yellow]否[/yellow]",
        )

        console.print(table)

        if analysis.recommendations:
            console.print(Panel(
                "\n".join(analysis.recommendations),
                title="💡 分析建议",
                border_style="cyan",
            ))


def display_waste_analysis(analysis, output_cost=True):
    console.print(Panel.fit(
        f"[bold magenta]💰 资源浪费分析 - {analysis.namespace}/{analysis.pod}[/bold magenta]",
        border_style="magenta",
    ))

    table = Table(title="资源利用率分析", box=box.ROUNDED)
    table.add_column("指标", style="bold")
    table.add_column("CPU")
    table.add_column("内存")

    table.add_row(
        "当前请求",
        format_cpu(analysis.cpu.request) if analysis.cpu.request > 0 else "未设置",
        format_memory(analysis.memory.request) if analysis.memory.request > 0 else "未设置",
    )
    table.add_row("平均使用", format_cpu(analysis.cpu.usage_mean), format_memory(analysis.memory.usage_mean))
    table.add_row("P95 使用", format_cpu(analysis.cpu.usage_percentile_95), format_memory(analysis.memory.usage_percentile_95))
    table.add_row(
        "利用率",
        f"{analysis.cpu.utilization * 100:.1f}%",
        f"{analysis.memory.utilization * 100:.1f}%",
    )
    table.add_row("分类", format_category(analysis.cpu.category), format_category(analysis.memory.category))
    table.add_row(
        "浪费量",
        format_cpu(analysis.cpu.waste_amount),
        format_memory(analysis.memory.waste_amount),
    )
    table.add_row(
        "浪费比例",
        f"{analysis.cpu.waste_percent:.1f}%",
        f"{analysis.memory.waste_percent:.1f}%",
    )
    if output_cost and analysis.total_monthly_waste_cost > 0:
        table.add_row(
            "月度浪费成本",
            f"${analysis.cpu.monthly_waste_cost:.2f}",
            f"${analysis.memory.monthly_waste_cost:.2f}",
        )

    console.print(table)

    severity_style = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
        "critical": "red",
    }.get(analysis.waste_severity, "white")

    console.print(Panel(
        f"浪费严重程度: [{severity_style}]{analysis.waste_severity.upper()}[/{severity_style}]\n"
        f"总月度浪费成本: [bold]${analysis.total_monthly_waste_cost:.2f}[/bold] (年度: ${analysis.total_monthly_waste_cost * 12:.2f})",
        border_style=severity_style,
    ))

    if analysis.recommendations:
        console.print(Panel(
            "\n".join(analysis.recommendations),
            title="💡 优化建议",
            border_style="magenta",
        ))


def display_deployment_waste_analysis(analysis):
    console.print(Panel.fit(
        f"[bold magenta]💰 Deployment资源浪费分析 - {analysis.namespace}/{analysis.deployment}[/bold magenta]",
        border_style="magenta",
    ))

    table = Table(title="总体情况", box=box.ROUNDED)
    table.add_column("指标", style="bold")
    table.add_column("值", justify="right")

    table.add_row("Pod总数", str(analysis.total_pods))
    table.add_row("闲置Pod", f"[red]{analysis.idle_pods}[/red]")
    table.add_row("低利用率Pod", f"[yellow]{analysis.underutilized_pods}[/yellow]")
    table.add_row("最优配置Pod", f"[green]{analysis.optimal_pods}[/green]")
    table.add_row("过度利用Pod", f"[orange]{analysis.overutilized_pods}[/orange]")
    table.add_row("严重不足Pod", f"[red]{analysis.critical_pods}[/red]")
    table.add_row("月度浪费成本", f"[bold red]${analysis.total_monthly_waste_cost:.2f}[/bold red]")
    table.add_row("年度浪费成本", f"[bold red]${analysis.total_monthly_waste_cost * 12:.2f}[/bold red]")

    console.print(table)

    if analysis.recommendations:
        console.print(Panel(
            "\n".join(analysis.recommendations),
            title="💡 优化建议",
            border_style="magenta",
        ))

    if analysis.pods:
        console.print("\n[bold]Pod详情:[/bold]")
        detail_table = Table(box=box.ROUNDED)
        detail_table.add_column("Pod", style="bold")
        detail_table.add_column("CPU分类")
        detail_table.add_column("内存分类")
        detail_table.add_column("严重程度")
        detail_table.add_column("月度浪费", justify="right")

        for pod in analysis.pods:
            severity_style = {
                "low": "green",
                "medium": "yellow",
                "high": "red",
                "critical": "red",
            }.get(pod.waste_severity, "white")
            detail_table.add_row(
                pod.pod,
                format_category(pod.cpu.category),
                format_category(pod.memory.category),
                f"[{severity_style}]{pod.waste_severity.upper()}[/{severity_style}]",
                f"${pod.total_monthly_waste_cost:.2f}",
            )

        console.print(detail_table)


def display_simulation_result(result):
    status_styles = {
        SimulationStatus.SUCCESS: ("green", "✅"),
        SimulationStatus.WARNING: ("yellow", "⚠️"),
        SimulationStatus.FAILURE: ("red", "❌"),
    }
    color, icon = status_styles.get(result.status, ("white", "?"))

    console.print(Panel.fit(
        f"[{color}]{icon} 推荐演练结果 - {result.namespace}/{result.pod}[/{color}]",
        border_style=color,
    ))

    console.print(f"\n[bold]{result.summary}[/bold]\n")

    if result.metrics:
        metrics_table = Table(title="模拟指标对比", box=box.ROUNDED)
        metrics_table.add_column("指标", style="bold")
        metrics_table.add_column("当前值", justify="right")
        metrics_table.add_column("模拟值", justify="right")
        metrics_table.add_column("变化", justify="right")

        for metric in result.metrics:
            current_str = f"{metric.current_value:.2f} {metric.unit}" if metric.unit else f"{metric.current_value:.2f}"
            simulated_str = f"{metric.simulated_value:.2f} {metric.unit}" if metric.unit else f"{metric.simulated_value:.2f}"
            change_color = "green" if metric.improvement > 0 else "red" if metric.improvement < 0 else "white"
            change_str = f"[{change_color}]{metric.improvement:+.1f}%[/{change_color}]"
            metrics_table.add_row(metric.name, current_str, simulated_str, change_str)

        console.print(metrics_table)

    if result.events:
        console.print("\n[bold]⚠️  检测到的事件:[/bold]")
        events_table = Table(box=box.ROUNDED, show_lines=True)
        events_table.add_column("时间", style="bold")
        events_table.add_column("类型")
        events_table.add_column("描述")

        from datetime import datetime
        for event in result.events[:10]:
            event_type_style = {
                "throttling": "yellow",
                "oom": "red",
                "eviction": "red",
            }.get(event.event_type, "white")
            dt = datetime.fromtimestamp(event.timestamp)
            events_table.add_row(
                dt.strftime("%Y-%m-%d %H:%M:%S"),
                f"[{event_type_style}]{event.event_type.upper()}[/{event_type_style}]",
                event.description,
            )
        if len(result.events) > 10:
            events_table.add_row("...", "...", f"还有 {len(result.events) - 10} 个事件未显示")

        console.print(events_table)

    if result.cost_analysis:
        cost_table = Table(title="成本分析", box=box.ROUNDED)
        cost_table.add_column("项目", style="bold")
        cost_table.add_column("当前", justify="right")
        cost_table.add_column("推荐", justify="right")
        cost_table.add_column("节省", justify="right")

        cost_table.add_row(
            "月度成本",
            f"${result.cost_analysis.current_monthly_cost:.2f}",
            f"${result.cost_analysis.recommended_monthly_cost:.2f}",
            f"[green]${result.cost_analysis.monthly_savings:+.2f} ({result.cost_analysis.savings_percent:+.1f}%)[/green]",
        )

        console.print(cost_table)

    risk_style = {
        "low": "green",
        "medium": "yellow",
        "high": "red",
    }.get(result.risk_level, "white")
    console.print(f"\n风险等级: [{risk_style}]{result.risk_level.upper()}[/{risk_style}]")


def display_deployment_simulation_result(result):
    status_styles = {
        SimulationStatus.SUCCESS: ("green", "✅"),
        SimulationStatus.WARNING: ("yellow", "⚠️"),
        SimulationStatus.FAILURE: ("red", "❌"),
    }
    color, icon = status_styles.get(result.status, ("white", "?"))

    console.print(Panel.fit(
        f"[{color}]{icon} Deployment推荐演练结果 - {result.namespace}/{result.deployment}[/{color}]",
        border_style=color,
    ))

    console.print(f"\n[bold]{result.summary}[/bold]\n")

    summary_table = Table(title="总体情况", box=box.ROUNDED)
    summary_table.add_column("指标", style="bold")
    summary_table.add_column("值", justify="right")

    summary_table.add_row("Pod总数", str(len(result.pods)))
    summary_table.add_row("CPU节流事件", f"[yellow]{result.total_throttling_events}[/yellow]")
    summary_table.add_row("OOM风险事件", f"[red]{result.total_oom_events}[/red]")
    summary_table.add_row("Pod驱逐风险", f"[red]{result.total_evictions}[/red]")
    summary_table.add_row(
        "月度成本节省",
        f"[green]${result.cost_savings_monthly:+.2f}[/green]" if result.cost_savings_monthly >= 0
        else f"[red]${result.cost_savings_monthly:.2f}[/red]",
    )
    summary_table.add_row(
        "可用性影响",
        f"[green]+{result.availability_impact:.1f}%[/green]" if result.availability_impact >= 0
        else f"[red]{result.availability_impact:.1f}%[/red]",
    )
    perf_style = {"positive": "green", "neutral": "yellow", "caution": "orange"}
    summary_table.add_row(
        "性能影响",
        f"[{perf_style.get(result.performance_impact, 'white')}]{result.performance_impact.upper()}[/{perf_style.get(result.performance_impact, 'white')}]",
    )

    console.print(summary_table)

    if result.recommendations:
        console.print(Panel(
            "\n".join(result.recommendations),
            title="💡 演练建议",
            border_style=color,
        ))

    if result.pods:
        console.print("\n[bold]Pod演练详情:[/bold]")
        detail_table = Table(box=box.ROUNDED)
        detail_table.add_column("Pod", style="bold")
        detail_table.add_column("状态")
        detail_table.add_column("风险等级")
        detail_table.add_column("节流", justify="right")
        detail_table.add_column("OOM", justify="right")
        detail_table.add_column("月度节省", justify="right")

        for pod in result.pods:
            pod_status_style = {
                SimulationStatus.SUCCESS: "green",
                SimulationStatus.WARNING: "yellow",
                SimulationStatus.FAILURE: "red",
            }.get(pod.status, "white")
            pod_risk_style = {
                "low": "green",
                "medium": "yellow",
                "high": "red",
            }.get(pod.risk_level, "white")
            savings = pod.cost_analysis.monthly_savings if pod.cost_analysis else 0
            detail_table.add_row(
                pod.pod,
                f"[{pod_status_style}]{pod.status.upper()}[/{pod_status_style}]",
                f"[{pod_risk_style}]{pod.risk_level.upper()}[/{pod_risk_style}]",
                str(pod.cpu_throttling_events),
                str(pod.oom_events),
                f"${savings:+.2f}",
            )

        console.print(detail_table)


def seasonality_to_dict(cpu_analysis, memory_analysis, namespace, pod):
    return {
        "namespace": namespace,
        "pod": pod,
        "cpu": {
            "pattern": cpu_analysis.pattern.value,
            "confidence": float(cpu_analysis.confidence),
            "dominant_period_hours": float(cpu_analysis.dominant_period_hours) if cpu_analysis.dominant_period_hours else None,
            "seasonal_strength": float(cpu_analysis.seasonal_strength),
            "peak_resource_multiplier": float(cpu_analysis.peak_resource_multiplier),
            "trough_resource_multiplier": float(cpu_analysis.trough_resource_multiplier),
            "has_strong_seasonality": bool(cpu_analysis.has_strong_seasonality),
            "recommendations": list(cpu_analysis.recommendations),
        },
        "memory": {
            "pattern": memory_analysis.pattern.value,
            "confidence": float(memory_analysis.confidence),
            "dominant_period_hours": float(memory_analysis.dominant_period_hours) if memory_analysis.dominant_period_hours else None,
            "seasonal_strength": float(memory_analysis.seasonal_strength),
            "peak_resource_multiplier": float(memory_analysis.peak_resource_multiplier),
            "trough_resource_multiplier": float(memory_analysis.trough_resource_multiplier),
            "has_strong_seasonality": bool(memory_analysis.has_strong_seasonality),
            "recommendations": list(memory_analysis.recommendations),
        },
    }


def waste_analysis_to_dict(analysis):
    return {
        "namespace": analysis.namespace,
        "pod": analysis.pod,
        "cpu": {
            "request": analysis.cpu.request,
            "usage_mean": analysis.cpu.usage_mean,
            "usage_median": analysis.cpu.usage_median,
            "usage_percentile_95": analysis.cpu.usage_percentile_95,
            "utilization": analysis.cpu.utilization,
            "waste_amount": analysis.cpu.waste_amount,
            "waste_percent": analysis.cpu.waste_percent,
            "category": analysis.cpu.category.value,
            "monthly_waste_cost": analysis.cpu.monthly_waste_cost,
        },
        "memory": {
            "request": analysis.memory.request,
            "usage_mean": analysis.memory.usage_mean,
            "usage_median": analysis.memory.usage_median,
            "usage_percentile_95": analysis.memory.usage_percentile_95,
            "utilization": analysis.memory.utilization,
            "waste_amount": analysis.memory.waste_amount,
            "waste_percent": analysis.memory.waste_percent,
            "category": analysis.memory.category.value,
            "monthly_waste_cost": analysis.memory.monthly_waste_cost,
        },
        "total_monthly_waste_cost": analysis.total_monthly_waste_cost,
        "waste_severity": analysis.waste_severity,
        "is_idle": analysis.is_idle,
        "recommendations": analysis.recommendations,
    }


def simulation_result_to_dict(result):
    def event_to_dict(e):
        return {
            "timestamp": e.timestamp,
            "resource_type": e.resource_type,
            "event_type": e.event_type,
            "value": e.value,
            "threshold": e.threshold,
            "description": e.description,
        }

    def metric_to_dict(m):
        return {
            "name": m.name,
            "current_value": m.current_value,
            "simulated_value": m.simulated_value,
            "improvement": m.improvement,
            "unit": m.unit,
        }

    return {
        "pod": result.pod,
        "namespace": result.namespace,
        "status": result.status.value,
        "cpu_evictions": result.cpu_evictions,
        "memory_evictions": result.memory_evictions,
        "cpu_throttling_events": result.cpu_throttling_events,
        "oom_events": result.oom_events,
        "p95_cpu_latency_impact": result.p95_cpu_latency_impact,
        "max_cpu_usage": result.max_cpu_usage,
        "max_memory_usage": result.max_memory_usage,
        "risk_level": result.risk_level,
        "summary": result.summary,
        "events": [event_to_dict(e) for e in result.events],
        "metrics": [metric_to_dict(m) for m in result.metrics],
        "cost_analysis": {
            "current_monthly_cost": result.cost_analysis.current_monthly_cost,
            "recommended_monthly_cost": result.cost_analysis.recommended_monthly_cost,
            "monthly_savings": result.cost_analysis.monthly_savings,
            "savings_percent": result.cost_analysis.savings_percent,
        } if result.cost_analysis else None,
    }


@cli.command()
@click.option("-n", "--namespace", required=True, help="Kubernetes命名空间")
@click.option("-p", "--pod", required=True, help="Pod名称")
@click.option("-d", "--days", default=14, type=int, help="分析历史数据的天数（至少需要24小时）")
@click.option("-s", "--step", default="5m", help="数据采样间隔")
@click.option("--output", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="输出格式")
@click.pass_context
def seasonality(ctx, namespace, pod, days, step, output):
    """季节性检测 - 分析资源使用的周期性模式"""

    quiet_mode = output != "table"

    if not quiet_mode:
        console.print(Panel.fit(
            "[bold cyan]📊 Kubernetes 季节性检测[/bold cyan]",
            border_style="cyan",
        ))

    prometheus = ctx.obj.get("prometheus")
    seasonality_detector = ctx.obj["seasonality"]

    if not quiet_mode and days < 1:
        console.print("[yellow]警告: 少于1天的数据可能无法有效检测季节性[/yellow]")

    from datetime import datetime, timedelta
    if prometheus:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        collector = DataCollector(prometheus)
        pod_data = collector.collect_pod_data(namespace, pod, start_time, end_time, step)
    else:
        from .demo_data_generator import generate_demo_pod_data
        pod_data = generate_demo_pod_data(namespace, pod, days=days)
        if not quiet_mode:
            console.print("[yellow]使用演示模式 - 生成包含季节性模式的测试数据[/yellow]")

    if not pod_data:
        if not quiet_mode:
            console.print("[red]错误: 无法收集Pod数据[/red]")
        return

    cpu_analysis = seasonality_detector.detect_seasonality(pod_data.cpu_usage, "cpu")
    memory_analysis = seasonality_detector.detect_seasonality(pod_data.memory_usage, "memory")

    if output == "table":
        display_seasonality_analysis(cpu_analysis, memory_analysis, namespace, pod)
    elif output == "json":
        print(json.dumps(seasonality_to_dict(cpu_analysis, memory_analysis, namespace, pod),
                         indent=2, ensure_ascii=False))
    elif output == "yaml":
        print(yaml.dump(seasonality_to_dict(cpu_analysis, memory_analysis, namespace, pod),
                       allow_unicode=True, sort_keys=False))


@cli.command()
@click.option("-n", "--namespace", required=True, help="Kubernetes命名空间")
@click.option("-p", "--pod", "pod_name", help="Pod名称（与-d二选一）")
@click.option("-d", "--deployment", help="Deployment名称（与-p二选一）")
@click.option("--days", default=7, type=int, help="分析历史数据的天数")
@click.option("--step", default="1m", help="数据采样间隔")
@click.option("--min-waste", type=float, default=1.0, help="只显示月度浪费超过此金额的资源")
@click.option("--output", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="输出格式")
@click.pass_context
def waste(ctx, namespace, pod_name, deployment, days, step, min_waste, output):
    """资源浪费分析 - 识别闲置资源和浪费成本"""

    quiet_mode = output != "table"

    if not quiet_mode:
        console.print(Panel.fit(
            "[bold magenta]💰 Kubernetes 资源浪费分析[/bold magenta]",
            border_style="magenta",
        ))

    prometheus = ctx.obj.get("prometheus")
    waste_analyzer = ctx.obj["waste"]
    cost_estimator = ctx.obj.get("cost")

    if not pod_name and not deployment:
        if not quiet_mode:
            console.print("[red]错误: 必须指定Pod名称(-p)或Deployment名称(-d)[/red]")
        return

    from datetime import datetime, timedelta
    if prometheus:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        collector = DataCollector(prometheus)

        if pod_name:
            pod_data = collector.collect_pod_data(namespace, pod_name, start_time, end_time, step)
            if pod_data:
                analysis = waste_analyzer.analyze_pod_waste(pod_data, cost_estimator)
            else:
                if not quiet_mode:
                    console.print("[red]错误: 无法收集Pod数据[/red]")
                return
        else:
            dep_data = collector.collect_deployment_data(namespace, deployment, start_time, end_time, step)
            if dep_data:
                analysis = waste_analyzer.analyze_deployment_waste(dep_data, cost_estimator)
            else:
                if not quiet_mode:
                    console.print("[red]错误: 无法收集Deployment数据[/red]")
                return
    else:
        from .demo_data_generator import generate_demo_pod_data, generate_demo_deployment_data
        if pod_name:
            pod_data = generate_demo_pod_data(namespace, pod_name, high_waste=True)
            analysis = waste_analyzer.analyze_pod_waste(pod_data, cost_estimator)
            if not quiet_mode:
                console.print("[yellow]使用演示模式 - 生成包含资源浪费的测试数据[/yellow]")
        else:
            dep_data = generate_demo_deployment_data(namespace, deployment, replicas=3, high_waste=True)
            analysis = waste_analyzer.analyze_deployment_waste(dep_data, cost_estimator)
            if not quiet_mode:
                console.print("[yellow]使用演示模式 - 生成包含资源浪费的Deployment测试数据[/yellow]")

    if min_waste > 0 and hasattr(analysis, 'total_monthly_waste_cost'):
        if analysis.total_monthly_waste_cost < min_waste:
            if not quiet_mode:
                console.print(f"[green]未发现超过 ${min_waste:.2f}/月 的资源浪费[/green]")
            return

    if output == "table":
        if hasattr(analysis, 'pods'):
            display_deployment_waste_analysis(analysis)
        else:
            display_waste_analysis(analysis)
    elif output == "json":
        if hasattr(analysis, 'pods'):
            pod_analyses = [waste_analysis_to_dict(p) for p in analysis.pods]
            result = {
                "namespace": analysis.namespace,
                "deployment": analysis.deployment,
                "total_pods": analysis.total_pods,
                "idle_pods": analysis.idle_pods,
                "underutilized_pods": analysis.underutilized_pods,
                "optimal_pods": analysis.optimal_pods,
                "overutilized_pods": analysis.overutilized_pods,
                "critical_pods": analysis.critical_pods,
                "total_monthly_waste_cost": analysis.total_monthly_waste_cost,
                "recommendations": analysis.recommendations,
                "pods": pod_analyses,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(json.dumps(waste_analysis_to_dict(analysis), indent=2, ensure_ascii=False))
    elif output == "yaml":
        if hasattr(analysis, 'pods'):
            pod_analyses = [waste_analysis_to_dict(p) for p in analysis.pods]
            result = {
                "namespace": analysis.namespace,
                "deployment": analysis.deployment,
                "total_pods": analysis.total_pods,
                "total_monthly_waste_cost": analysis.total_monthly_waste_cost,
                "pods": pod_analyses,
            }
            print(yaml.dump(result, allow_unicode=True, sort_keys=False))
        else:
            print(yaml.dump(waste_analysis_to_dict(analysis), allow_unicode=True, sort_keys=False))


@cli.command()
@click.option("-n", "--namespace", required=True, help="Kubernetes命名空间")
@click.option("-p", "--pod", "pod_name", help="Pod名称（与-d二选一）")
@click.option("-d", "--deployment", help="Deployment名称（与-p二选一）")
@click.option("--days", default=7, type=int, help="模拟使用历史数据的天数")
@click.option("--step", default="1m", help="数据采样间隔")
@click.option("--workload-type", type=click.Choice(["stateless", "stateful", "critical"]),
              default="stateless", help="工作负载类型")
@click.option("--risk-tolerance", type=click.Choice(["low", "medium", "high"]),
              default="medium", help="风险容忍度")
@click.option("--stress-scenario", type=click.Choice(["normal", "moderate", "high", "extreme"]),
              default="normal", help="压力场景模拟")
@click.option("--output", type=click.Choice(["table", "json", "yaml"]),
              default="table", help="输出格式")
@click.pass_context
def simulate(ctx, namespace, pod_name, deployment, days, step, workload_type, risk_tolerance, stress_scenario, output):
    """推荐演练 - 模拟应用推荐配置运行观察效果"""

    quiet_mode = output != "table"

    if not quiet_mode:
        console.print(Panel.fit(
            "[bold blue]🔬 Kubernetes 推荐演练[/bold blue]",
            border_style="blue",
        ))

    prometheus = ctx.obj.get("prometheus")
    vpa_recommender = ctx.obj["vpa"]
    simulator = ctx.obj["simulator"]
    cost_estimator = ctx.obj.get("cost")

    if not pod_name and not deployment:
        if not quiet_mode:
            console.print("[red]错误: 必须指定Pod名称(-p)或Deployment名称(-d)[/red]")
        return

    simulator.config.stress_scenario = stress_scenario

    from datetime import datetime, timedelta
    if prometheus:
        end_time = datetime.now()
        start_time = end_time - timedelta(days=days)
        collector = DataCollector(prometheus)

        if pod_name:
            pod_data = collector.collect_pod_data(namespace, pod_name, start_time, end_time, step)
        else:
            dep_data = collector.collect_deployment_data(namespace, deployment, start_time, end_time, step)
    else:
        from .demo_data_generator import generate_demo_pod_data, generate_demo_deployment_data
        if pod_name:
            pod_data = generate_demo_pod_data(namespace, pod_name, high_variance=True)
            if not quiet_mode:
                console.print(f"[yellow]使用演示模式 - 压力场景: {stress_scenario}[/yellow]")
        else:
            dep_data = generate_demo_deployment_data(namespace, deployment, replicas=3, high_variance=True)
            if not quiet_mode:
                console.print(f"[yellow]使用演示模式 - 压力场景: {stress_scenario}[/yellow]")

    if pod_name:
        if not pod_data:
            if not quiet_mode:
                console.print("[red]错误: 无法收集Pod数据[/red]")
            return

        vpa_recommendation = vpa_recommender.recommend_for_pod(pod_data, workload_type, risk_tolerance)
        if not vpa_recommendation:
            if not quiet_mode:
                console.print("[red]错误: 无法生成VPA推荐[/red]")
            return

        sim_result = simulator.simulate_pod_recommendation(pod_data, vpa_recommendation, cost_estimator)

        if output == "table":
            display_simulation_result(sim_result)
        elif output == "json":
            print(json.dumps(simulation_result_to_dict(sim_result), indent=2, ensure_ascii=False))
        elif output == "yaml":
            print(yaml.dump(simulation_result_to_dict(sim_result), allow_unicode=True, sort_keys=False))
    else:
        if not dep_data:
            if not quiet_mode:
                console.print("[red]错误: 无法收集Deployment数据[/red]")
            return

        vpa_recommendations = []
        for pod_data in dep_data.pods:
            vpa_rec = vpa_recommender.recommend_for_pod(pod_data, workload_type, risk_tolerance)
            if vpa_rec:
                vpa_recommendations.append(vpa_rec)

        if not vpa_recommendations:
            if not quiet_mode:
                console.print("[red]错误: 无法生成VPA推荐[/red]")
            return

        from .hpa_recommender import DeploymentHorizontalRecommendation
        hpa_recommendation = None
        if hasattr(ctx.obj, 'get'):
            hpa_recommender = ctx.obj.get("hpa")
            if hpa_recommender:
                hpa_recommendation = hpa_recommender.recommend_for_deployment(dep_data)

        sim_result = simulator.simulate_deployment_recommendation(
            dep_data, vpa_recommendations, hpa_recommendation, cost_estimator
        )

        if output == "table":
            display_deployment_simulation_result(sim_result)
        elif output == "json":
            pod_results = [simulation_result_to_dict(p) for p in sim_result.pods]
            result = {
                "namespace": sim_result.namespace,
                "deployment": sim_result.deployment,
                "status": sim_result.status.value,
                "total_throttling_events": sim_result.total_throttling_events,
                "total_oom_events": sim_result.total_oom_events,
                "total_evictions": sim_result.total_evictions,
                "cost_savings_monthly": sim_result.cost_savings_monthly,
                "availability_impact": sim_result.availability_impact,
                "performance_impact": sim_result.performance_impact,
                "summary": sim_result.summary,
                "recommendations": sim_result.recommendations,
                "pods": pod_results,
            }
            print(json.dumps(result, indent=2, ensure_ascii=False))
        elif output == "yaml":
            pod_results = [simulation_result_to_dict(p) for p in sim_result.pods]
            result = {
                "namespace": sim_result.namespace,
                "deployment": sim_result.deployment,
                "status": sim_result.status.value,
                "cost_savings_monthly": sim_result.cost_savings_monthly,
                "pods": pod_results,
            }
            print(yaml.dump(result, allow_unicode=True, sort_keys=False))


def recommendation_to_dict(rec):
    """将推荐对象转换为字典"""
    return {
        "namespace": rec.namespace,
        "pod": rec.pod,
        "data_quality": rec.data_quality,
        "warnings": rec.warnings,
        "cpu": {
            "current_request": rec.current_cpu_request,
            "current_limit": rec.current_cpu_limit,
            "target_request": rec.cpu.target_request,
            "target_limit": rec.cpu.target_limit,
            "lower_bound": rec.cpu.lower_bound,
            "upper_bound": rec.cpu.upper_bound,
            "confidence": rec.cpu.confidence,
            "percentile_used": rec.cpu.percentile_used,
            "safety_margin": rec.cpu.safety_margin,
            "estimation_method": rec.cpu.estimation_method,
            "base_percentile_value": rec.cpu.base_percentile_value,
        },
        "memory": {
            "current_request": rec.current_memory_request,
            "current_limit": rec.current_memory_limit,
            "target_request": rec.memory.target_request,
            "target_limit": rec.memory.target_limit,
            "lower_bound": rec.memory.lower_bound,
            "upper_bound": rec.memory.upper_bound,
            "confidence": rec.memory.confidence,
            "percentile_used": rec.memory.percentile_used,
            "safety_margin": rec.memory.safety_margin,
            "estimation_method": rec.memory.estimation_method,
            "base_percentile_value": rec.memory.base_percentile_value,
            "oom_buffer_percent": rec.memory.oom_buffer_percent,
            "oom_buffer_amount": rec.memory.oom_buffer_amount,
        },
    }


def hpa_recommendation_to_dict(rec):
    """将HPA推荐对象转换为字典"""
    return {
        "namespace": rec.namespace,
        "deployment": rec.deployment,
        "warnings": rec.warnings,
        "recommendation": {
            "current_replicas": rec.recommendation.current_replicas,
            "target_replicas": rec.recommendation.target_replicas,
            "min_replicas": rec.recommendation.min_replicas,
            "max_replicas": rec.recommendation.max_replicas,
            "lower_bound": rec.recommendation.lower_bound,
            "upper_bound": rec.recommendation.upper_bound,
            "confidence": rec.recommendation.confidence,
            "driving_resource": rec.recommendation.driving_resource,
            "cpu_utilization_target": rec.recommendation.cpu_utilization_target,
            "memory_utilization_target": rec.recommendation.memory_utilization_target,
            "reasoning": rec.recommendation.reasoning,
        },
    }


def main():
    try:
        cli(obj={})
    except Exception as e:
        console.print(f"[red]错误: {e}[/red]")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
