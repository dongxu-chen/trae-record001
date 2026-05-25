import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from .prometheus_client import PrometheusClient

logger = logging.getLogger(__name__)


class MetricsData:
    def __init__(self):
        self.timestamps: List[datetime] = []
        self.values: np.ndarray = np.array([])

    @property
    def is_empty(self) -> bool:
        return len(self.values) == 0

    @property
    def duration_hours(self) -> float:
        if len(self.timestamps) < 2:
            return 0.0
        return (self.timestamps[-1] - self.timestamps[0]).total_seconds() / 3600

    def to_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame({"timestamp": self.timestamps, "value": self.values})


class PodResourceData:
    def __init__(self, namespace: str, pod: str):
        self.namespace = namespace
        self.pod = pod
        self.cpu_usage = MetricsData()
        self.memory_usage = MetricsData()
        self.cpu_request: Optional[float] = None
        self.cpu_limit: Optional[float] = None
        self.memory_request: Optional[float] = None
        self.memory_limit: Optional[float] = None
        self.collected_at: Optional[datetime] = None


class DeploymentResourceData:
    def __init__(self, namespace: str, deployment: str):
        self.namespace = namespace
        self.deployment = deployment
        self.pods: List[PodResourceData] = []
        self.replicas_history: MetricsData = MetricsData()
        self.aggregated_cpu = MetricsData()
        self.aggregated_memory = MetricsData()


class DataCollector:
    def __init__(
        self,
        prometheus_client: PrometheusClient,
        min_data_points: int = 10,
        fill_method: str = "linear",
    ):
        self.prometheus_client = prometheus_client
        self.min_data_points = min_data_points
        self.fill_method = fill_method

    def collect_pod_data(
        self,
        namespace: str,
        pod: str,
        start_time: datetime,
        end_time: datetime,
        step: str = "1m",
    ) -> PodResourceData:
        logger.info(f"Collecting data for pod {namespace}/{pod}")
        pod_data = PodResourceData(namespace, pod)

        cpu_raw = self.prometheus_client.get_pod_cpu_usage(
            namespace, pod, start_time, end_time, step
        )
        memory_raw = self.prometheus_client.get_pod_memory_usage(
            namespace, pod, start_time, end_time, step
        )

        pod_data.cpu_usage = self._process_metrics(cpu_raw, start_time, end_time, step)
        pod_data.memory_usage = self._process_metrics(
            memory_raw, start_time, end_time, step
        )

        pod_data.cpu_request = self.prometheus_client.get_pod_cpu_request(namespace, pod)
        pod_data.cpu_limit = self.prometheus_client.get_pod_cpu_limit(namespace, pod)
        pod_data.memory_request = self.prometheus_client.get_pod_memory_request(
            namespace, pod
        )
        pod_data.memory_limit = self.prometheus_client.get_pod_memory_limit(
            namespace, pod
        )

        pod_data.collected_at = datetime.now()

        self._validate_pod_data(pod_data)
        return pod_data

    def collect_deployment_data(
        self,
        namespace: str,
        deployment: str,
        start_time: datetime,
        end_time: datetime,
        step: str = "1m",
    ) -> DeploymentResourceData:
        logger.info(f"Collecting data for deployment {namespace}/{deployment}")
        deployment_data = DeploymentResourceData(namespace, deployment)

        pods = self.prometheus_client.get_pods_for_deployment(namespace, deployment)
        logger.info(f"Found {len(pods)} pods for deployment")

        for pod_info in pods:
            try:
                pod_data = self.collect_pod_data(
                    pod_info["namespace"],
                    pod_info["pod"],
                    start_time,
                    end_time,
                    step,
                )
                deployment_data.pods.append(pod_data)
            except Exception as e:
                logger.warning(
                    f"Failed to collect data for pod {pod_info['pod']}: {e}"
                )

        replicas_raw = self.prometheus_client.get_pod_replicas(
            namespace, deployment, start_time, end_time, "5m"
        )
        deployment_data.replicas_history = self._process_metrics(
            replicas_raw, start_time, end_time, "5m"
        )

        self._aggregate_deployment_metrics(deployment_data)
        return deployment_data

    def _process_metrics(
        self,
        raw_data: List[Tuple[float, float]],
        start_time: datetime,
        end_time: datetime,
        step: str,
    ) -> MetricsData:
        metrics = MetricsData()

        if not raw_data:
            return metrics

        timestamps = []
        values = []
        for ts, val in raw_data:
            dt = datetime.fromtimestamp(ts)
            if start_time <= dt <= end_time:
                timestamps.append(dt)
                values.append(val)

        if not timestamps:
            return metrics

        metrics.timestamps = timestamps
        metrics.values = np.array(values, dtype=np.float64)

        metrics = self._clean_metrics(metrics)
        metrics = self._fill_missing_data(metrics, start_time, end_time, step)

        return metrics

    def _clean_metrics(self, metrics: MetricsData) -> MetricsData:
        if metrics.is_empty:
            return metrics

        values = metrics.values.copy()

        valid_mask = np.isfinite(values)
        values = values[valid_mask]
        timestamps = [t for t, v in zip(metrics.timestamps, valid_mask) if v]

        if len(values) == 0:
            return MetricsData()

        q1 = np.percentile(values, 1)
        q99 = np.percentile(values, 99)
        iqr = q99 - q1
        lower_bound = q1 - 3 * iqr
        upper_bound = q99 + 3 * iqr

        outlier_mask = (values >= lower_bound) & (values <= upper_bound)
        values = values[outlier_mask]
        timestamps = [t for t, v in zip(timestamps, outlier_mask) if v]

        non_zero_mask = values > 0
        if np.sum(non_zero_mask) >= self.min_data_points:
            values = values[non_zero_mask]
            timestamps = [t for t, v in zip(timestamps, non_zero_mask) if v]

        cleaned = MetricsData()
        cleaned.timestamps = timestamps
        cleaned.values = values
        return cleaned

    def _fill_missing_data(
        self,
        metrics: MetricsData,
        start_time: datetime,
        end_time: datetime,
        step: str,
    ) -> MetricsData:
        if metrics.is_empty:
            return metrics

        df = metrics.to_dataframe()
        df = df.set_index("timestamp")

        step_seconds = self._parse_step(step)
        full_index = pd.date_range(
            start=start_time, end=end_time, freq=f"{step_seconds}S"
        )
        df = df.reindex(full_index)

        if self.fill_method == "linear":
            df["value"] = df["value"].interpolate(method="linear")
        elif self.fill_method == "time":
            df["value"] = df["value"].interpolate(method="time")
        elif self.fill_method == "ffill":
            df["value"] = df["value"].ffill().bfill()

        df["value"] = df["value"].fillna(df["value"].median())

        filled = MetricsData()
        filled.timestamps = df.index.tolist()
        filled.values = df["value"].values
        return filled

    def _aggregate_deployment_metrics(self, deployment_data: DeploymentResourceData):
        if not deployment_data.pods:
            return

        all_cpu_timestamps = []
        all_cpu_values = []
        all_memory_timestamps = []
        all_memory_values = []

        for pod in deployment_data.pods:
            if not pod.cpu_usage.is_empty:
                all_cpu_timestamps.extend(pod.cpu_usage.timestamps)
                all_cpu_values.extend(pod.cpu_usage.values)
            if not pod.memory_usage.is_empty:
                all_memory_timestamps.extend(pod.memory_usage.timestamps)
                all_memory_values.extend(pod.memory_usage.values)

        if all_cpu_timestamps:
            cpu_df = pd.DataFrame(
                {"timestamp": all_cpu_timestamps, "value": all_cpu_values}
            )
            cpu_df = cpu_df.set_index("timestamp")
            cpu_df = cpu_df.resample("1min").sum()

            deployment_data.aggregated_cpu.timestamps = cpu_df.index.tolist()
            deployment_data.aggregated_cpu.values = cpu_df["value"].values

        if all_memory_timestamps:
            memory_df = pd.DataFrame(
                {"timestamp": all_memory_timestamps, "value": all_memory_values}
            )
            memory_df = memory_df.set_index("timestamp")
            memory_df = memory_df.resample("1min").sum()

            deployment_data.aggregated_memory.timestamps = memory_df.index.tolist()
            deployment_data.aggregated_memory.values = memory_df["value"].values

    def _validate_pod_data(self, pod_data: PodResourceData):
        issues = []

        if pod_data.cpu_usage.is_empty:
            issues.append("No CPU usage data collected")
        elif len(pod_data.cpu_usage.values) < self.min_data_points:
            issues.append(
                f"Insufficient CPU data points: {len(pod_data.cpu_usage.values)} < {self.min_data_points}"
            )

        if pod_data.memory_usage.is_empty:
            issues.append("No memory usage data collected")
        elif len(pod_data.memory_usage.values) < self.min_data_points:
            issues.append(
                f"Insufficient memory data points: {len(pod_data.memory_usage.values)} < {self.min_data_points}"
            )

        if pod_data.cpu_request is None:
            logger.warning(f"Could not retrieve CPU request for {pod_data.pod}")
        if pod_data.cpu_limit is None:
            logger.warning(f"Could not retrieve CPU limit for {pod_data.pod}")
        if pod_data.memory_request is None:
            logger.warning(f"Could not retrieve memory request for {pod_data.pod}")
        if pod_data.memory_limit is None:
            logger.warning(f"Could not retrieve memory limit for {pod_data.pod}")

        if issues:
            logger.warning(
                f"Data quality issues for pod {pod_data.pod}:\n"
                + "\n".join(f"  - {issue}" for issue in issues)
            )

    @staticmethod
    def _parse_step(step: str) -> int:
        if step.endswith("s"):
            return int(step[:-1])
        elif step.endswith("m"):
            return int(step[:-1]) * 60
        elif step.endswith("h"):
            return int(step[:-1]) * 3600
        elif step.endswith("d"):
            return int(step[:-1]) * 86400
        else:
            raise ValueError(f"Invalid step format: {step}")
