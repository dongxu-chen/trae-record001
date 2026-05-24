#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
APM集成模块
死锁发生时关联应用调用链，支持SkyWalking、Pinpoint、Jaeger等主流APM系统
"""

import re
import json
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from collections import defaultdict
import requests


@dataclass
class TraceSpan:
    span_id: str
    trace_id: str
    service_name: str
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: int
    status: str
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    parent_span_id: Optional[str] = None
    sql_statement: Optional[str] = None
    db_type: Optional[str] = None
    db_table: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "service_name": self.service_name,
            "operation_name": self.operation_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "tags": self.tags,
            "logs": self.logs,
            "parent_span_id": self.parent_span_id,
            "sql_statement": self.sql_statement,
            "db_type": self.db_type,
            "db_table": self.db_table
        }


@dataclass
class TraceInfo:
    trace_id: str
    service_name: str
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: int
    status: str
    spans: List[TraceSpan] = field(default_factory=list)
    user_id: Optional[str] = None
    http_url: Optional[str] = None
    http_method: Optional[str] = None
    error_msg: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "service_name": self.service_name,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "spans": [s.to_dict() for s in self.spans],
            "user_id": self.user_id,
            "http_url": self.http_url,
            "http_method": self.http_method,
            "error_msg": self.error_msg,
            "span_count": len(self.spans)
        }


@dataclass
class DeadlockTraceCorrelation:
    deadlock_timestamp: datetime
    transaction_id: str
    trace_id: str
    service_name: str
    related_spans: List[TraceSpan]
    correlation_confidence: float
    matched_sqls: List[str]
    matched_tables: List[str]
    trace_info: Optional[TraceInfo] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "deadlock_timestamp": self.deadlock_timestamp.isoformat(),
            "transaction_id": self.transaction_id,
            "trace_id": self.trace_id,
            "service_name": self.service_name,
            "correlation_confidence": self.correlation_confidence,
            "matched_sqls": self.matched_sqls,
            "matched_tables": self.matched_tables,
            "related_spans": [s.to_dict() for s in self.related_spans],
            "trace_info": self.trace_info.to_dict() if self.trace_info else None
        }


class APMIntegration:
    def __init__(self, apm_type: str = 'skywalking', **kwargs):
        self.apm_type = apm_type.lower()
        self.config = kwargs
        self.base_url = kwargs.get('base_url', '')
        self.api_key = kwargs.get('api_key', '')
        self.service_name = kwargs.get('service_name', '')

        self._apm_client = None

    def _get_client(self):
        if self._apm_client:
            return self._apm_client

        if self.apm_type == 'skywalking':
            self._apm_client = SkyWalkingClient(self.base_url, self.api_key)
        elif self.apm_type == 'pinpoint':
            self._apm_client = PinpointClient(self.base_url, self.api_key)
        elif self.apm_type == 'jaeger':
            self._apm_client = JaegerClient(self.base_url, self.api_key)
        elif self.apm_type == 'datadog':
            self._apm_client = DatadogClient(self.base_url, self.api_key)
        else:
            self._apm_client = MockAPMClient()

        return self._apm_client

    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        client = self._get_client()
        try:
            return client.query_traces(start_time, end_time, service_name, tags)
        except Exception as e:
            print(f"查询APM链路失败: {e}")
            return []

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        client = self._get_client()
        try:
            return client.query_trace_detail(trace_id)
        except Exception as e:
            print(f"查询链路详情失败: {e}")
            return None

    def correlate_deadlock_with_traces(self, deadlock,
                                       time_window_before: int = 60,
                                       time_window_after: int = 10) -> List[DeadlockTraceCorrelation]:
        correlations = []

        if not deadlock.timestamp:
            return correlations

        start_time = datetime.fromtimestamp(deadlock.timestamp.timestamp() - time_window_before)
        end_time = datetime.fromtimestamp(deadlock.timestamp.timestamp() + time_window_after)

        traces = self.query_traces(start_time, end_time)

        for txn in deadlock.transactions:
            best_correlation = self._find_best_correlation(txn, traces, deadlock.timestamp)
            if best_correlation:
                correlations.append(best_correlation)

        return correlations

    def _find_best_correlation(self, txn, traces: List[TraceInfo],
                               deadlock_time: datetime) -> Optional[DeadlockTraceCorrelation]:
        best_match = None
        best_confidence = 0.0

        txn_tables = self._get_txn_tables(txn)
        txn_sqls = [s.lower() for s in txn.sql_statements]

        for trace in traces:
            matched_sqls = []
            matched_tables = []
            db_spans = []

            for span in trace.spans:
                if span.db_type or span.sql_statement:
                    db_spans.append(span)

                    if span.sql_statement:
                        span_sql = span.sql_statement.lower()
                        for txn_sql in txn_sqls:
                            if txn_sql in span_sql or span_sql in txn_sql:
                                matched_sqls.append(span.sql_statement)
                                break

                    if span.db_table and span.db_table in txn_tables:
                        matched_tables.append(span.db_table)

            time_diff = abs((trace.start_time - deadlock_time).total_seconds())
            time_confidence = max(0, 1 - time_diff / 60.0)

            sql_confidence = len(matched_sqls) / max(len(txn_sqls), 1)
            table_confidence = len(matched_tables) / max(len(txn_tables), 1)
            span_confidence = min(1.0, len(db_spans) / 2.0)

            overall_confidence = (
                0.3 * time_confidence +
                0.4 * sql_confidence +
                0.2 * table_confidence +
                0.1 * span_confidence
            )

            if overall_confidence > best_confidence and overall_confidence > 0.3:
                best_confidence = overall_confidence
                best_match = DeadlockTraceCorrelation(
                    deadlock_timestamp=deadlock_time,
                    transaction_id=txn.txn_id,
                    trace_id=trace.trace_id,
                    service_name=trace.service_name,
                    related_spans=db_spans,
                    correlation_confidence=overall_confidence,
                    matched_sqls=matched_sqls,
                    matched_tables=matched_tables,
                    trace_info=trace
                )

        return best_match

    def _get_txn_tables(self, txn) -> List[str]:
        tables = []
        for lock in txn.holding_locks:
            if lock.table_name not in tables:
                tables.append(lock.table_name)
        if txn.waiting_lock and txn.waiting_lock.table_name not in tables:
            tables.append(txn.waiting_lock.table_name)
        return tables

    def generate_trace_links(self, correlations: List[DeadlockTraceCorrelation]) -> List[Dict[str, str]]:
        links = []
        client = self._get_client()

        for corr in correlations:
            trace_url = client.get_trace_url(corr.trace_id)
            service_url = client.get_service_url(corr.service_name)
            links.append({
                "transaction_id": corr.transaction_id,
                "trace_id": corr.trace_id,
                "service_name": corr.service_name,
                "trace_url": trace_url,
                "service_url": service_url,
                "confidence": corr.correlation_confidence
            })

        return links

    def send_deadlock_alert(self, deadlock, correlations: List[DeadlockTraceCorrelation]) -> bool:
        client = self._get_client()
        try:
            event_data = {
                "event_type": "DEADLOCK_DETECTED",
                "timestamp": deadlock.timestamp.isoformat() if deadlock.timestamp else None,
                "transaction_count": len(deadlock.transactions),
                "victim_txns": deadlock.victim_txns,
                "correlations": [c.to_dict() for c in correlations]
            }
            return client.send_event(event_data)
        except Exception as e:
            print(f"发送死锁告警到APM失败: {e}")
            return False


class BaseAPMClient:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.api_key = api_key

    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        raise NotImplementedError

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        raise NotImplementedError

    def get_trace_url(self, trace_id: str) -> str:
        return f"{self.base_url}/trace/{trace_id}"

    def get_service_url(self, service_name: str) -> str:
        return f"{self.base_url}/service/{service_name}"

    def send_event(self, event_data: Dict[str, Any]) -> bool:
        return True


class SkyWalkingClient(BaseAPMClient):
    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        if not self.base_url:
            return []

        try:
            url = f"{self.base_url}/graphql"
            query = """
            query queryTraces($condition: TraceQueryCondition) {
                queryBasicTraces(condition: $condition) {
                    traces {
                        key: segmentId
                        operationNames
                        duration
                        start
                        isError
                        serviceId
                        serviceName
                    }
                }
            }
            """

            variables = {
                "condition": {
                    "queryDuration": {
                        "start": start_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "end": end_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "step": "SECOND"
                    },
                    "traceState": "ALL",
                    "queryOrder": "BY_START_TIME",
                    "paging": {"pageNum": 1, "pageSize": 100}
                }
            }

            if service_name:
                variables["condition"]["serviceName"] = service_name

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.post(url, json={"query": query, "variables": variables},
                                     headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                traces_data = data.get("data", {}).get("queryBasicTraces", {}).get("traces", [])
                return [self._parse_trace_info(t) for t in traces_data]

        except Exception as e:
            print(f"SkyWalking查询失败: {e}")

        return []

    def _parse_trace_info(self, trace_data: Dict[str, Any]) -> TraceInfo:
        start_ts = trace_data.get("start", 0) / 1000.0
        duration = trace_data.get("duration", 0)

        return TraceInfo(
            trace_id=trace_data.get("key", ""),
            service_name=trace_data.get("serviceName", ""),
            start_time=datetime.fromtimestamp(start_ts),
            end_time=datetime.fromtimestamp(start_ts + duration / 1000.0) if duration else None,
            duration_ms=duration,
            status="ERROR" if trace_data.get("isError") else "SUCCESS",
            spans=[]
        )

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        if not self.base_url:
            return None

        try:
            url = f"{self.base_url}/graphql"
            query = """
            query queryTrace($traceId: ID!) {
                queryTrace(traceId: $traceId) {
                    spans {
                        spanId
                        traceId
                        serviceCode
                        operationName
                        startTime
                        endTime
                        isError
                        type
                        peer
                        component
                        tags {
                            key
                            value
                        }
                        logs {
                            time
                            data {
                                key
                                value
                            }
                        }
                    }
                }
            }
            """

            variables = {"traceId": trace_id}

            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            response = requests.post(url, json={"query": query, "variables": variables},
                                     headers=headers, timeout=10)

            if response.status_code == 200:
                data = response.json()
                spans_data = data.get("data", {}).get("queryTrace", {}).get("spans", [])
                if spans_data:
                    return self._parse_trace_detail(trace_id, spans_data)

        except Exception as e:
            print(f"SkyWalking查询详情失败: {e}")

        return None

    def _parse_trace_detail(self, trace_id: str, spans_data: List[Dict[str, Any]]) -> TraceInfo:
        spans = []
        min_time = float('inf')
        max_time = 0
        service_name = ""

        for span_data in spans_data:
            start_ts = span_data.get("startTime", 0) / 1000.0
            end_ts = span_data.get("endTime", 0) / 1000.0
            duration = int((end_ts - start_ts) * 1000)

            min_time = min(min_time, start_ts)
            max_time = max(max_time, end_ts)
            service_name = span_data.get("serviceCode", service_name)

            tags = {}
            sql_statement = None
            db_type = None
            db_table = None

            for tag in span_data.get("tags", []):
                key = tag.get("key", "")
                value = tag.get("value", "")
                tags[key] = value

                if key == "db.statement" or key == "sql":
                    sql_statement = value
                elif key == "db.type":
                    db_type = value
                elif key == "db.table":
                    db_table = value

            span = TraceSpan(
                span_id=str(span_data.get("spanId", "")),
                trace_id=trace_id,
                service_name=span_data.get("serviceCode", ""),
                operation_name=span_data.get("operationName", ""),
                start_time=datetime.fromtimestamp(start_ts),
                end_time=datetime.fromtimestamp(end_ts) if end_ts else None,
                duration_ms=duration,
                status="ERROR" if span_data.get("isError") else "SUCCESS",
                tags=tags,
                logs=span_data.get("logs", []),
                parent_span_id=str(span_data.get("parentSpanId", "")),
                sql_statement=sql_statement,
                db_type=db_type,
                db_table=db_table
            )
            spans.append(span)

        return TraceInfo(
            trace_id=trace_id,
            service_name=service_name,
            start_time=datetime.fromtimestamp(min_time) if min_time != float('inf') else datetime.now(),
            end_time=datetime.fromtimestamp(max_time) if max_time > 0 else None,
            duration_ms=int((max_time - min_time) * 1000) if max_time > 0 and min_time != float('inf') else 0,
            status="ERROR" if any(s.status == "ERROR" for s in spans) else "SUCCESS",
            spans=spans
        )

    def get_trace_url(self, trace_id: str) -> str:
        if self.base_url:
            return f"{self.base_url}/trace/{trace_id}"
        return f"#trace/{trace_id}"


class PinpointClient(BaseAPMClient):
    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        return []

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        return None


class JaegerClient(BaseAPMClient):
    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        return []

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        return None


class DatadogClient(BaseAPMClient):
    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        return []

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        return None


class MockAPMClient(BaseAPMClient):
    def __init__(self):
        super().__init__("", "")
        self._mock_traces = self._generate_mock_traces()

    def _generate_mock_traces(self) -> List[TraceInfo]:
        traces = []
        base_time = datetime.now().timestamp() - 3600

        for i in range(10):
            trace_id = f"mock-trace-{i:04d}"
            service_name = ["order-service", "payment-service", "user-service", "inventory-service"][i % 4]

            spans = []
            txn_tables = [["orders", "order_items"], ["payments"], ["users"], ["products", "inventory"]][i % 4]
            sql_templates = [
                ["SELECT * FROM orders WHERE id = ?", "UPDATE order_items SET status = ? WHERE order_id = ?"],
                ["INSERT INTO payments (order_id, amount) VALUES (?, ?)"],
                ["SELECT * FROM users WHERE id = ? FOR UPDATE"],
                ["UPDATE products SET stock = stock - 1 WHERE id = ?", "SELECT * FROM inventory WHERE product_id = ?"]
            ][i % 4]

            start_ts = base_time + i * 60
            for j, sql in enumerate(sql_templates):
                span_start = start_ts + j * 0.1
                span_end = span_start + 0.05

                span = TraceSpan(
                    span_id=f"span-{i}-{j}",
                    trace_id=trace_id,
                    service_name=service_name,
                    operation_name=f"db-{txn_tables[j % len(txn_tables)]}",
                    start_time=datetime.fromtimestamp(span_start),
                    end_time=datetime.fromtimestamp(span_end),
                    duration_ms=50,
                    status="SUCCESS",
                    sql_statement=sql,
                    db_type="mysql",
                    db_table=txn_tables[j % len(txn_tables)]
                )
                spans.append(span)

            trace = TraceInfo(
                trace_id=trace_id,
                service_name=service_name,
                start_time=datetime.fromtimestamp(start_ts),
                end_time=datetime.fromtimestamp(start_ts + 0.2),
                duration_ms=200,
                status="SUCCESS",
                spans=spans,
                user_id=f"user-{1000 + i}",
                http_url=f"/api/{service_name.split('-')[0]}/{100 + i}",
                http_method=["GET", "POST", "PUT", "DELETE"][i % 4]
            )
            traces.append(trace)

        return traces

    def query_traces(self, start_time: datetime, end_time: datetime,
                     service_name: Optional[str] = None,
                     tags: Optional[Dict[str, Any]] = None) -> List[TraceInfo]:
        result = self._mock_traces
        if service_name:
            result = [t for t in result if t.service_name == service_name]
        return result

    def query_trace_detail(self, trace_id: str) -> Optional[TraceInfo]:
        for trace in self._mock_traces:
            if trace.trace_id == trace_id:
                return trace
        return None

    def get_trace_url(self, trace_id: str) -> str:
        return f"#mock/trace/{trace_id}"

    def send_event(self, event_data: Dict[str, Any]) -> bool:
        print(f"[MockAPM] 发送事件: {json.dumps(event_data, ensure_ascii=False, indent=2)}")
        return True
