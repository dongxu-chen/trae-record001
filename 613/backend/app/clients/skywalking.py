import httpx
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import json
import random

from app.config import settings


class SkyWalkingClient:
    def __init__(self, base_url: str = None, timeout: int = None):
        self.base_url = base_url or settings.skywalking_base_url
        self.timeout = timeout or settings.skywalking_timeout
        self.use_mock = True

    async def _request(self, endpoint: str, method: str = "GET", params: Dict = None) -> Dict:
        if self.use_mock:
            return self._mock_response(endpoint, params)

        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.request(method, url, params=params)
            response.raise_for_status()
            return response.json()

    def _mock_response(self, endpoint: str, params: Dict = None) -> Dict:
        if "alarm" in endpoint.lower():
            return self._mock_alerts(params)
        elif "rule" in endpoint.lower():
            return self._mock_rules()
        elif "metrics" in endpoint.lower():
            return self._mock_metrics(params)
        return {}

    def _mock_alerts(self, params: Dict = None) -> Dict:
        lookback_hours = params.get("lookback", settings.default_lookback_hours) if params else settings.default_lookback_hours
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=lookback_hours)

        services = ["order-service", "user-service", "payment-service", "inventory-service", "gateway-service"]
        rules = [
            "resp_time_percentile_rule",
            "service_resp_time_rule",
            "service_sla_rule",
            "service_instance_resp_time_rule",
            "endpoint_resp_time_rule",
            "service_relation_client_resp_time_rule",
            "db_access_resp_time_rule",
            "cache_access_resp_time_rule",
        ]

        alerts = []
        for i in range(random.randint(500, 1000)):
            alert_time = start_time + timedelta(seconds=random.randint(0, int(lookback_hours * 3600)))
            service = random.choice(services)
            rule_name = random.choice(rules)

            critical_rules = ["service_sla_rule", "service_resp_time_rule"]
            scope = random.choice(["SERVICE", "SERVICE_INSTANCE", "ENDPOINT"])
            priority = "CRITICAL" if rule_name in critical_rules else random.choice(["WARNING", "CRITICAL", "INFO"])

            if priority == "INFO":
                frequency = random.randint(5, 50)
            elif priority == "WARNING":
                frequency = random.randint(3, 30)
            else:
                frequency = random.randint(1, 10)

            for _ in range(random.randint(1, frequency)):
                inner_time = alert_time + timedelta(seconds=random.randint(0, 300))
                alerts.append({
                    "id": f"alert_{i}_{_}",
                    "ruleName": rule_name,
                    "alarmMessage": f"{rule_name} threshold exceeded in {service}",
                    "scope": scope,
                    "service": service,
                    "serviceInstance": f"{service}-instance-{random.randint(1, 5)}" if scope == "SERVICE_INSTANCE" else None,
                    "endpointName": f"/api/{service}/resource/{random.randint(1, 100)}" if scope == "ENDPOINT" else None,
                    "startTime": int(inner_time.timestamp() * 1000),
                    "priority": priority,
                    "tags": [{"key": "env", "value": "prod"}, {"key": "version", "value": "v1.0"}],
                })

        return {"data": {"total": len(alerts), "items": alerts}}

    def _mock_rules(self) -> Dict:
        rules = [
            {
                "id": 1,
                "name": "resp_time_percentile_rule",
                "metricsName": "percentile",
                "threshold": [800, 1000, 1200, 1500, 2000],
                "op": ">",
                "period": 10,
                "count": 3,
                "silencePeriod": 10,
                "message": "Percentile response time is over threshold",
                "enabled": True,
                "priority": "WARNING",
            },
            {
                "id": 2,
                "name": "service_resp_time_rule",
                "metricsName": "service_resp_time",
                "threshold": 1000,
                "op": ">",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Service average response time over 1s",
                "enabled": True,
                "priority": "CRITICAL",
            },
            {
                "id": 3,
                "name": "service_sla_rule",
                "metricsName": "service_sla",
                "threshold": 99,
                "op": "<",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Service SLA below 99%",
                "enabled": True,
                "priority": "CRITICAL",
            },
            {
                "id": 4,
                "name": "service_instance_resp_time_rule",
                "metricsName": "service_instance_resp_time",
                "threshold": 2000,
                "op": ">",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Service instance response time over 2s",
                "enabled": True,
                "priority": "WARNING",
            },
            {
                "id": 5,
                "name": "endpoint_resp_time_rule",
                "metricsName": "endpoint_resp_time",
                "threshold": 1000,
                "op": ">",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Endpoint response time over 1s",
                "enabled": True,
                "priority": "WARNING",
            },
            {
                "id": 6,
                "name": "service_relation_client_resp_time_rule",
                "metricsName": "service_relation_client_resp_time",
                "threshold": 1000,
                "op": ">",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Service relation client response time over 1s",
                "enabled": True,
                "priority": "INFO",
            },
            {
                "id": 7,
                "name": "db_access_resp_time_rule",
                "metricsName": "database_access_resp_time",
                "threshold": 1000,
                "op": ">",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Database access response time over 1s",
                "enabled": True,
                "priority": "WARNING",
            },
            {
                "id": 8,
                "name": "cache_access_resp_time_rule",
                "metricsName": "cache_access_resp_time",
                "threshold": 300,
                "op": ">",
                "period": 2,
                "count": 2,
                "silencePeriod": 10,
                "message": "Cache access response time over 300ms",
                "enabled": True,
                "priority": "INFO",
            },
        ]
        return {"data": rules}

    def _mock_metrics(self, params: Dict = None) -> Dict:
        metric_name = params.get("name", "service_resp_time") if params else "service_resp_time"
        now = datetime.now()
        values = []

        for i in range(24):
            time_point = now - timedelta(hours=24 - i)
            base_value = {
                "service_resp_time": 500,
                "service_sla": 99.5,
                "percentile": 600,
            }.get(metric_name, 100)

            value = base_value + random.gauss(0, base_value * 0.1)
            if random.random() < 0.1:
                value *= random.uniform(2, 5)

            values.append({
                "time": int(time_point.timestamp() * 1000),
                "value": round(value, 2),
            })

        return {"data": {"values": values}}

    async def get_alerts(
        self,
        lookback_hours: int = None,
        rule_name: str = None,
        service: str = None,
        priority: str = None,
    ) -> List[Dict[str, Any]]:
        params = {
            "lookback": lookback_hours or settings.default_lookback_hours,
            "pageSize": 10000,
        }
        if rule_name:
            params["ruleName"] = rule_name
        if service:
            params["service"] = service
        if priority:
            params["priority"] = priority

        response = await self._request("/api/v3/alarm", params=params)
        data = response.get("data", {})
        if isinstance(data, dict):
            return data.get("items", [])
        return data if isinstance(data, list) else []

    async def get_rules(self) -> List[Dict[str, Any]]:
        response = await self._request("/api/v3/alerting/rules")
        data = response.get("data", [])
        return data if isinstance(data, list) else []

    async def get_metrics(
        self,
        metric_name: str,
        service: str = None,
        duration_hours: int = 24,
    ) -> List[Dict[str, Any]]:
        params = {
            "name": metric_name,
            "duration": duration_hours,
        }
        if service:
            params["service"] = service

        response = await self._request("/api/v3/metrics", params=params)
        data = response.get("data", {})
        return data.get("values", []) if isinstance(data, dict) else []

    async def update_rule(self, rule_id: int, rule_config: Dict[str, Any]) -> Dict[str, Any]:
        endpoint = f"/api/v3/alerting/rules/{rule_id}"
        response = await self._request(endpoint, method="PUT", params=rule_config)
        return response.get("data", {})

    async def test_connection(self) -> bool:
        try:
            await self._request("/api/v3/health")
            return True
        except Exception:
            return self.use_mock


skywalking_client = SkyWalkingClient()
