import logging
from datetime import datetime, timedelta
from typing import List, Tuple

import numpy as np

from .data_collector import MetricsData, PodResourceData, DeploymentResourceData

logger = logging.getLogger(__name__)


def generate_demo_metrics(
    start_time: datetime,
    end_time: datetime,
    step_minutes: int = 1,
    base_value: float = 1.0,
    volatility: float = 0.3,
    trend: float = 0.0,
    has_spikes: bool = True,
    has_daily_pattern: bool = True,
) -> MetricsData:
    """生成演示用的指标数据"""

    metrics = MetricsData()

    total_minutes = int((end_time - start_time).total_seconds() / 60)
    num_points = total_minutes // step_minutes

    if num_points < 10:
        num_points = 100

    timestamps = []
    current_time = start_time
    for i in range(num_points):
        timestamps.append(current_time)
        current_time += timedelta(minutes=step_minutes)

    time_array = np.arange(num_points)

    values = base_value * np.ones(num_points)

    if has_daily_pattern:
        daily_cycle = 24 * 60 // step_minutes
        hour_of_day = (time_array % daily_cycle) / (daily_cycle / (2 * np.pi))
        daily_pattern = 0.3 * np.sin(hour_of_day - np.pi / 2) + 0.7
        values *= daily_pattern

    noise = np.random.normal(0, volatility, num_points)
    values *= (1 + noise)

    if trend != 0:
        trend_values = np.linspace(0, trend * num_points, num_points)
        values += trend_values

    if has_spikes:
        num_spikes = max(1, num_points // 200)
        spike_indices = np.random.choice(num_points, num_spikes, replace=False)
        for idx in spike_indices:
            spike_magnitude = base_value * (2 + np.random.random() * 3)
            values[idx] = spike_magnitude
            if idx > 0:
                values[idx - 1] = spike_magnitude * 0.5
            if idx < num_points - 1:
                values[idx + 1] = spike_magnitude * 0.5

    values = np.maximum(values, base_value * 0.1)

    metrics.timestamps = timestamps
    metrics.values = values

    return metrics


def generate_demo_pod_data(
    namespace: str = "default",
    pod_name: str = "demo-pod",
    days: int = 7,
    high_waste: bool = False,
    high_variance: bool = False,
) -> PodResourceData:
    """生成演示用的Pod数据"""

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    pod_data = PodResourceData(namespace, pod_name)

    if high_waste:
        pod_data.cpu_request = 2.0
        pod_data.cpu_limit = 4.0
        pod_data.memory_request = 4 * 1024 * 1024 * 1024
        pod_data.memory_limit = 8 * 1024 * 1024 * 1024
        cpu_base = 0.2
        memory_base = 0.6 * 1024 * 1024 * 1024
        cpu_volatility = 0.2
        memory_volatility = 0.1
    elif high_variance:
        pod_data.cpu_request = 1.0
        pod_data.cpu_limit = 2.0
        pod_data.memory_request = 2 * 1024 * 1024 * 1024
        pod_data.memory_limit = 4 * 1024 * 1024 * 1024
        cpu_base = 0.6
        memory_base = 1.2 * 1024 * 1024 * 1024
        cpu_volatility = 0.8
        memory_volatility = 0.4
    else:
        pod_data.cpu_request = 1.0
        pod_data.cpu_limit = 2.0
        pod_data.memory_request = 2 * 1024 * 1024 * 1024
        pod_data.memory_limit = 4 * 1024 * 1024 * 1024
        cpu_base = 0.3
        memory_base = 1.2 * 1024 * 1024 * 1024
        cpu_volatility = 0.4
        memory_volatility = 0.15

    pod_data.cpu_usage = generate_demo_metrics(
        start_time, end_time,
        step_minutes=1,
        base_value=cpu_base,
        volatility=cpu_volatility,
        trend=0.0001,
        has_spikes=True,
        has_daily_pattern=True,
    )

    pod_data.memory_usage = generate_demo_metrics(
        start_time, end_time,
        step_minutes=1,
        base_value=memory_base,
        volatility=memory_volatility,
        trend=0.00001,
        has_spikes=False,
        has_daily_pattern=False,
    )

    pod_data.collected_at = datetime.now()

    return pod_data


def generate_demo_deployment_data(
    namespace: str = "default",
    deployment_name: str = "demo-deployment",
    days: int = 7,
    num_replicas: int = 3,
    replicas: Optional[int] = None,
    high_waste: bool = False,
    high_variance: bool = False,
) -> DeploymentResourceData:
    """生成演示用的Deployment数据"""

    end_time = datetime.now()
    start_time = end_time - timedelta(days=days)

    deployment_data = DeploymentResourceData(namespace, deployment_name)

    if replicas is not None:
        num_replicas = replicas

    if high_waste:
        cpu_request_per_pod = 2.0
        memory_request_per_pod = 4 * 1024 * 1024 * 1024
        cpu_base_per_pod = 0.15 + np.random.random() * 0.1
        memory_base_per_pod = 0.4 * 1024 * 1024 * 1024 + np.random.random() * 100 * 1024 * 1024
        cpu_volatility = 0.2
        memory_volatility = 0.1
    elif high_variance:
        cpu_request_per_pod = 1.0
        memory_request_per_pod = 2 * 1024 * 1024 * 1024
        cpu_base_per_pod = 0.4 + np.random.random() * 0.3
        memory_base_per_pod = 0.8 * 1024 * 1024 * 1024 + np.random.random() * 300 * 1024 * 1024
        cpu_volatility = 0.6
        memory_volatility = 0.3
    else:
        cpu_request_per_pod = 0.5
        memory_request_per_pod = 1 * 1024 * 1024 * 1024
        cpu_base_per_pod = 0.15 + np.random.random() * 0.2
        memory_base_per_pod = 0.5 * 1024 * 1024 * 1024 + np.random.random() * 200 * 1024 * 1024
        cpu_volatility = 0.35
        memory_volatility = 0.1

    for i in range(num_replicas):
        pod = PodResourceData(namespace, f"{deployment_name}-{i}-abcde")
        pod.cpu_request = cpu_request_per_pod
        pod.cpu_limit = cpu_request_per_pod * 2
        pod.memory_request = memory_request_per_pod
        pod.memory_limit = memory_request_per_pod * 2

        pod.cpu_usage = generate_demo_metrics(
            start_time, end_time,
            step_minutes=1,
            base_value=cpu_base_per_pod,
            volatility=cpu_volatility + np.random.random() * 0.2,
            trend=0.00005 + np.random.random() * 0.0001,
            has_spikes=True,
            has_daily_pattern=True,
        )

        pod.memory_usage = generate_demo_metrics(
            start_time, end_time,
            step_minutes=1,
            base_value=memory_base_per_pod,
            volatility=memory_volatility + np.random.random() * 0.1,
            trend=0.000005,
            has_spikes=False,
            has_daily_pattern=False,
        )

        pod.collected_at = datetime.now()
        deployment_data.pods.append(pod)

    deployment_data.replicas_history = MetricsData()
    replica_timestamps = []
    replica_values = []
    current = start_time
    while current <= end_time:
        replica_timestamps.append(current)
        variation = np.random.randint(-1, 2)
        replica_values.append(float(max(1, num_replicas + variation)))
        current += timedelta(minutes=5)

    deployment_data.replicas_history.timestamps = replica_timestamps
    deployment_data.replicas_history.values = np.array(replica_values)

    total_cpu = np.zeros_like(deployment_data.pods[0].cpu_usage.values)
    total_memory = np.zeros_like(deployment_data.pods[0].memory_usage.values)

    for pod in deployment_data.pods:
        total_cpu += pod.cpu_usage.values
        total_memory += pod.memory_usage.values

    deployment_data.aggregated_cpu.timestamps = deployment_data.pods[0].cpu_usage.timestamps
    deployment_data.aggregated_cpu.values = total_cpu
    deployment_data.aggregated_memory.timestamps = deployment_data.pods[0].memory_usage.timestamps
    deployment_data.aggregated_memory.values = total_memory

    return deployment_data


def generate_demo_full_analysis(
    namespace: str = "default",
    deployment_name: str = "demo-app",
    days: int = 7,
):
    """生成演示用的完整分析数据"""

    num_replicas = np.random.randint(2, 5)

    deployment_data = generate_demo_deployment_data(
        namespace, deployment_name, days, num_replicas
    )

    cpu_request = deployment_data.pods[0].cpu_request if deployment_data.pods else 0.5
    memory_request = deployment_data.pods[0].memory_request if deployment_data.pods else 1 * 1024 * 1024 * 1024

    return deployment_data.pods, None, cpu_request, memory_request


def generate_demo_resources() -> List[dict]:
    """生成演示用的资源列表"""

    return [
        {
            "namespace": "default",
            "pod": "web-app-7c98f7d6b-abcde",
            "deployment": "web-app",
            "cpu_request": 0.5,
            "cpu_limit": 1.0,
            "memory_request": 512 * 1024 * 1024,
            "memory_limit": 1024 * 1024 * 1024,
        },
        {
            "namespace": "default",
            "pod": "api-service-6d8f7c9e0-fghij",
            "deployment": "api-service",
            "cpu_request": 1.0,
            "cpu_limit": 2.0,
            "memory_request": 1024 * 1024 * 1024,
            "memory_limit": 2048 * 1024 * 1024,
        },
        {
            "namespace": "production",
            "pod": "payment-gateway-5b7c8d9e0-klmno",
            "deployment": "payment-gateway",
            "cpu_request": 2.0,
            "cpu_limit": 4.0,
            "memory_request": 4096 * 1024 * 1024,
            "memory_limit": 8192 * 1024 * 1024,
        },
    ]
