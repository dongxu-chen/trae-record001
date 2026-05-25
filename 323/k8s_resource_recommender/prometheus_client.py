import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urljoin

import requests

logger = logging.getLogger(__name__)


class PrometheusClient:
    def __init__(
        self,
        url: str,
        token: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_ssl: bool = True,
        timeout: int = 30,
    ):
        self.url = url.rstrip("/")
        self.token = token
        self.username = username
        self.password = password
        self.verify_ssl = verify_ssl
        self.timeout = timeout
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        if self.token:
            session.headers["Authorization"] = f"Bearer {self.token}"
        elif self.username and self.password:
            session.auth = (self.username, self.password)
        session.verify = self.verify_ssl
        return session

    def _query(self, query: str, time: Optional[datetime] = None) -> Dict:
        params = {"query": query}
        if time:
            params["time"] = time.timestamp()

        url = urljoin(self.url, "/api/v1/query")
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "success":
            raise ValueError(f"Prometheus query failed: {result.get('error')}")

        return result.get("data", {})

    def _query_range(
        self,
        query: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> Dict:
        params = {
            "query": query,
            "start": start.timestamp(),
            "end": end.timestamp(),
            "step": step,
        }

        url = urljoin(self.url, "/api/v1/query_range")
        response = self.session.get(url, params=params, timeout=self.timeout)
        response.raise_for_status()
        result = response.json()

        if result.get("status") != "success":
            raise ValueError(f"Prometheus query_range failed: {result.get('error')}")

        return result.get("data", {})

    def get_pod_cpu_usage(
        self,
        namespace: str,
        pod: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> List[Tuple[float, float]]:
        query = (
            f'sum(rate(container_cpu_usage_seconds_total{{namespace="{namespace}", '
            f'pod="{pod}", container!="POD", container!=""}}[5m]))'
        )
        data = self._query_range(query, start, end, step)
        return self._extract_values(data)

    def get_pod_memory_usage(
        self,
        namespace: str,
        pod: str,
        start: datetime,
        end: datetime,
        step: str = "1m",
    ) -> List[Tuple[float, float]]:
        query = (
            f'sum(container_memory_working_set_bytes{{namespace="{namespace}", '
            f'pod="{pod}", container!="POD", container!=""}})'
        )
        data = self._query_range(query, start, end, step)
        return self._extract_values(data)

    def get_pod_cpu_request(
        self, namespace: str, pod: str, time: Optional[datetime] = None
    ) -> Optional[float]:
        query = (
            f'sum(kube_pod_container_resource_requests{{namespace="{namespace}", '
            f'pod="{pod}", resource="cpu", container!="POD", container!=""}})'
        )
        data = self._query(query, time)
        values = self._extract_scalar(data)
        return values[0][1] if values else None

    def get_pod_cpu_limit(
        self, namespace: str, pod: str, time: Optional[datetime] = None
    ) -> Optional[float]:
        query = (
            f'sum(kube_pod_container_resource_limits{{namespace="{namespace}", '
            f'pod="{pod}", resource="cpu", container!="POD", container!=""}})'
        )
        data = self._query(query, time)
        values = self._extract_scalar(data)
        return values[0][1] if values else None

    def get_pod_memory_request(
        self, namespace: str, pod: str, time: Optional[datetime] = None
    ) -> Optional[float]:
        query = (
            f'sum(kube_pod_container_resource_requests{{namespace="{namespace}", '
            f'pod="{pod}", resource="memory", container!="POD", container!=""}})'
        )
        data = self._query(query, time)
        values = self._extract_scalar(data)
        return values[0][1] if values else None

    def get_pod_memory_limit(
        self, namespace: str, pod: str, time: Optional[datetime] = None
    ) -> Optional[float]:
        query = (
            f'sum(kube_pod_container_resource_limits{{namespace="{namespace}", '
            f'pod="{pod}", resource="memory", container!="POD", container!=""}})'
        )
        data = self._query(query, time)
        values = self._extract_scalar(data)
        return values[0][1] if values else None

    def get_pod_replicas(
        self,
        namespace: str,
        deployment: str,
        start: datetime,
        end: datetime,
        step: str = "5m",
    ) -> List[Tuple[float, float]]:
        query = (
            f'kube_deployment_spec_replicas{{namespace="{namespace}", '
            f'deployment="{deployment}"}}'
        )
        data = self._query_range(query, start, end, step)
        return self._extract_values(data)

    def get_all_pods(self, namespace: Optional[str] = None) -> List[Dict[str, str]]:
        if namespace:
            query = f'kube_pod_info{{namespace="{namespace}"}}'
        else:
            query = "kube_pod_info"

        data = self._query(query)
        pods = []
        for result in data.get("result", []):
            metric = result.get("metric", {})
            pods.append(
                {
                    "namespace": metric.get("namespace", ""),
                    "pod": metric.get("pod", ""),
                    "node": metric.get("node", ""),
                    "created_by_name": metric.get("created_by_name", ""),
                }
            )
        return pods

    def get_all_deployments(
        self, namespace: Optional[str] = None
    ) -> List[Dict[str, str]]:
        if namespace:
            query = f'kube_deployment_created{{namespace="{namespace}"}}'
        else:
            query = "kube_deployment_created"

        data = self._query(query)
        deployments = []
        for result in data.get("result", []):
            metric = result.get("metric", {})
            deployments.append(
                {
                    "namespace": metric.get("namespace", ""),
                    "deployment": metric.get("deployment", ""),
                }
            )
        return deployments

    def get_pods_for_deployment(
        self, namespace: str, deployment: str
    ) -> List[Dict[str, str]]:
        query = (
            f'kube_pod_info{{namespace="{namespace}", '
            f'created_by_name=~"{deployment}.*"}}'
        )
        data = self._query(query)
        pods = []
        for result in data.get("result", []):
            metric = result.get("metric", {})
            pods.append(
                {
                    "namespace": metric.get("namespace", ""),
                    "pod": metric.get("pod", ""),
                    "node": metric.get("node", ""),
                }
            )
        return pods

    @staticmethod
    def _extract_values(data: Dict) -> List[Tuple[float, float]]:
        results = []
        for result in data.get("result", []):
            for ts, value in result.get("values", []):
                try:
                    results.append((float(ts), float(value)))
                except (ValueError, TypeError):
                    continue
        return sorted(results, key=lambda x: x[0])

    @staticmethod
    def _extract_scalar(data: Dict) -> List[Tuple[float, float]]:
        results = []
        for result in data.get("result", []):
            value = result.get("value", [])
            if len(value) == 2:
                try:
                    results.append((float(value[0]), float(value[1])))
                except (ValueError, TypeError):
                    continue
        return results

    def health_check(self) -> bool:
        try:
            url = urljoin(self.url, "/api/v1/status/config")
            response = self.session.get(url, timeout=self.timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Prometheus health check failed: {e}")
            return False
