import json
import logging
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from ..cloud_providers import BillingRecord
from ..config import ClickHouseConfig

logger = logging.getLogger(__name__)

try:
    import clickhouse_driver
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False


class ClickHouseStore:
    def __init__(self, config: ClickHouseConfig):
        self.config = config
        self._client = None

    def _get_client(self):
        if self._client is None and CLICKHOUSE_AVAILABLE:
            try:
                self._client = clickhouse_driver.Client(
                    host=self.config.host,
                    port=self.config.port,
                    user=self.config.user,
                    password=self.config.password,
                    database=self.config.database,
                )
                self._init_database()
            except Exception as e:
                logger.error(f"Failed to connect to ClickHouse: {e}")
                self._client = None
        return self._client

    def _init_database(self):
        client = self._get_client()
        if client is None:
            return

        try:
            client.execute(f"CREATE DATABASE IF NOT EXISTS {self.config.database}")
            client.execute(f"USE {self.config.database}")
            self._create_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")

    def _create_tables(self):
        client = self._get_client()
        if client is None:
            return

        create_billing_table = """
        CREATE TABLE IF NOT EXISTS billing_records (
            provider String,
            account_id String,
            region String,
            service_name String,
            product_code String,
            resource_id String,
            usage_start_date Date,
            usage_end_date Date,
            usage_amount Float64,
            usage_unit String,
            pretax_amount Float64,
            currency String,
            instance_type String,
            operating_system String,
            tags Map(String, String),
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(usage_start_date)
        ORDER BY (provider, usage_start_date, service_name, resource_id)
        SETTINGS index_granularity = 8192
        """

        create_resource_metrics_table = """
        CREATE TABLE IF NOT EXISTS resource_metrics (
            provider String,
            resource_id String,
            service_name String,
            metric_date Date,
            avg_cpu_utilization Float64,
            max_cpu_utilization Float64,
            avg_network_in Float64,
            avg_network_out Float64,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(metric_date)
        ORDER BY (provider, metric_date, resource_id)
        SETTINGS index_granularity = 8192
        """

        create_cost_allocation_table = """
        CREATE TABLE IF NOT EXISTS cost_allocation (
            allocation_date Date,
            provider String,
            label_key String,
            label_value String,
            service_name String,
            total_cost Float64,
            resource_count UInt32,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(allocation_date)
        ORDER BY (allocation_date, provider, label_key, label_value)
        SETTINGS index_granularity = 8192
        """

        create_anomalies_table = """
        CREATE TABLE IF NOT EXISTS cost_anomalies (
            provider String,
            service_name String,
            resource_id String,
            anomaly_date Date,
            expected_cost Float64,
            actual_cost Float64,
            percentage_change Float64,
            severity String,
            anomaly_type String,
            description String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(anomaly_date)
        ORDER BY (anomaly_date, provider, severity)
        SETTINGS index_granularity = 8192
        """

        create_optimization_suggestions_table = """
        CREATE TABLE IF NOT EXISTS optimization_suggestions (
            provider String,
            resource_id String,
            service_name String,
            suggestion_type String,
            current_cost Float64,
            estimated_savings Float64,
            savings_percentage Float64,
            description String,
            details String,
            priority String,
            created_at DateTime DEFAULT now()
        ) ENGINE = MergeTree()
        PARTITION BY toYYYYMM(created_at)
        ORDER BY (created_at, provider, priority)
        SETTINGS index_granularity = 8192
        """

        try:
            client.execute(create_billing_table)
            client.execute(create_resource_metrics_table)
            client.execute(create_cost_allocation_table)
            client.execute(create_anomalies_table)
            client.execute(create_optimization_suggestions_table)
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")

    def insert_billing_records(self, records: List[BillingRecord]) -> int:
        client = self._get_client()
        if client is None:
            logger.warning("ClickHouse not available, skipping insert")
            return len(records)

        rows = []
        for record in records:
            rows.append((
                record.provider,
                record.account_id,
                record.region,
                record.service_name,
                record.product_code,
                record.resource_id,
                record.usage_start_date,
                record.usage_end_date,
                record.usage_amount,
                record.usage_unit,
                record.pretax_amount,
                record.currency,
                record.instance_type,
                record.operating_system,
                record.tags or {},
            ))

        try:
            client.execute(
                """
                INSERT INTO billing_records (
                    provider, account_id, region, service_name, product_code,
                    resource_id, usage_start_date, usage_end_date, usage_amount,
                    usage_unit, pretax_amount, currency, instance_type,
                    operating_system, tags
                ) VALUES
                """,
                rows,
            )
            logger.info(f"Inserted {len(rows)} billing records")
            return len(rows)
        except Exception as e:
            logger.error(f"Failed to insert billing records: {e}")
            return 0

    def insert_resource_metrics(self, metrics: List[Dict[str, Any]]) -> int:
        client = self._get_client()
        if client is None:
            logger.warning("ClickHouse not available, skipping insert")
            return len(metrics)

        rows = []
        for m in metrics:
            rows.append((
                m.get("provider", ""),
                m.get("resource_id", ""),
                m.get("service_name", ""),
                m.get("metric_date", date.today()),
                m.get("avg_cpu_utilization", 0.0),
                m.get("max_cpu_utilization", 0.0),
                m.get("avg_network_in", 0.0),
                m.get("avg_network_out", 0.0),
            ))

        try:
            client.execute(
                """
                INSERT INTO resource_metrics (
                    provider, resource_id, service_name, metric_date,
                    avg_cpu_utilization, max_cpu_utilization,
                    avg_network_in, avg_network_out
                ) VALUES
                """,
                rows,
            )
            logger.info(f"Inserted {len(rows)} resource metrics")
            return len(rows)
        except Exception as e:
            logger.error(f"Failed to insert resource metrics: {e}")
            return 0

    def insert_cost_allocation(self, allocations: List[Dict[str, Any]]) -> int:
        client = self._get_client()
        if client is None:
            logger.warning("ClickHouse not available, skipping insert")
            return len(allocations)

        rows = []
        for alloc in allocations:
            rows.append((
                alloc.get("allocation_date", date.today()),
                alloc.get("provider", ""),
                alloc.get("label_key", ""),
                alloc.get("label_value", ""),
                alloc.get("service_name", ""),
                alloc.get("total_cost", 0.0),
                alloc.get("resource_count", 0),
            ))

        try:
            client.execute(
                """
                INSERT INTO cost_allocation (
                    allocation_date, provider, label_key, label_value,
                    service_name, total_cost, resource_count
                ) VALUES
                """,
                rows,
            )
            logger.info(f"Inserted {len(rows)} cost allocations")
            return len(rows)
        except Exception as e:
            logger.error(f"Failed to insert cost allocations: {e}")
            return 0

    def insert_anomalies(self, anomalies: List[Dict[str, Any]]) -> int:
        client = self._get_client()
        if client is None:
            logger.warning("ClickHouse not available, skipping insert")
            return len(anomalies)

        rows = []
        for anomaly in anomalies:
            rows.append((
                anomaly.get("provider", ""),
                anomaly.get("service_name", ""),
                anomaly.get("resource_id", ""),
                anomaly.get("anomaly_date", date.today()),
                anomaly.get("expected_cost", 0.0),
                anomaly.get("actual_cost", 0.0),
                anomaly.get("percentage_change", 0.0),
                anomaly.get("severity", ""),
                anomaly.get("anomaly_type", ""),
                anomaly.get("description", ""),
            ))

        try:
            client.execute(
                """
                INSERT INTO cost_anomalies (
                    provider, service_name, resource_id, anomaly_date,
                    expected_cost, actual_cost, percentage_change,
                    severity, anomaly_type, description
                ) VALUES
                """,
                rows,
            )
            logger.info(f"Inserted {len(rows)} anomalies")
            return len(rows)
        except Exception as e:
            logger.error(f"Failed to insert anomalies: {e}")
            return 0

    def insert_optimization_suggestions(self, suggestions: List[Dict[str, Any]]) -> int:
        client = self._get_client()
        if client is None:
            logger.warning("ClickHouse not available, skipping insert")
            return len(suggestions)

        rows = []
        for suggestion in suggestions:
            rows.append((
                suggestion.get("provider", ""),
                suggestion.get("resource_id", ""),
                suggestion.get("service_name", ""),
                suggestion.get("suggestion_type", ""),
                suggestion.get("current_cost", 0.0),
                suggestion.get("estimated_savings", 0.0),
                suggestion.get("savings_percentage", 0.0),
                suggestion.get("description", ""),
                suggestion.get("details", ""),
                suggestion.get("priority", ""),
            ))

        try:
            client.execute(
                """
                INSERT INTO optimization_suggestions (
                    provider, resource_id, service_name, suggestion_type,
                    current_cost, estimated_savings, savings_percentage,
                    description, details, priority
                ) VALUES
                """,
                rows,
            )
            logger.info(f"Inserted {len(rows)} optimization suggestions")
            return len(rows)
        except Exception as e:
            logger.error(f"Failed to insert optimization suggestions: {e}")
            return 0

    def query(self, sql: str, params: Optional[Dict] = None) -> List[Dict[str, Any]]:
        client = self._get_client()
        if client is None:
            logger.warning("ClickHouse not available, returning empty result")
            return []

        try:
            result = client.execute(sql, params or {})
            columns = [desc[0] for desc in client.execute(sql + " LIMIT 1", with_column_types=True)]
            return [dict(zip(columns, row)) for row in result]
        except Exception as e:
            logger.error(f"Failed to execute query: {e}")
            return []

    def get_cost_trend(
        self,
        start_date: date,
        end_date: date,
        providers: Optional[List[str]] = None,
        group_by: str = "day",
    ) -> List[Dict[str, Any]]:
        group_expr = {
            "day": "toDate(usage_start_date)",
            "week": "toStartOfWeek(usage_start_date)",
            "month": "toStartOfMonth(usage_start_date)",
            "provider": "provider",
            "service": "service_name",
        }.get(group_by, "toDate(usage_start_date)")

        where_clause = "WHERE usage_start_date >= %(start_date)s AND usage_start_date < %(end_date)s"
        params = {"start_date": start_date, "end_date": end_date}

        if providers:
            placeholders = ", ".join(f"%(provider_{i})s" for i in range(len(providers)))
            where_clause += f" AND provider IN ({placeholders})"
            for i, p in enumerate(providers):
                params[f"provider_{i}"] = p

        sql = f"""
        SELECT
            {group_expr} AS period,
            provider,
            SUM(pretax_amount) AS total_cost,
            COUNT(DISTINCT resource_id) AS resource_count
        FROM billing_records
        {where_clause}
        GROUP BY period, provider
        ORDER BY period, provider
        """

        return self.query(sql, params)

    def get_cost_by_service(
        self,
        start_date: date,
        end_date: date,
        providers: Optional[List[str]] = None,
        top_n: int = 10,
    ) -> List[Dict[str, Any]]:
        where_clause = "WHERE usage_start_date >= %(start_date)s AND usage_start_date < %(end_date)s"
        params = {"start_date": start_date, "end_date": end_date}

        if providers:
            placeholders = ", ".join(f"%(provider_{i})s" for i in range(len(providers)))
            where_clause += f" AND provider IN ({placeholders})"
            for i, p in enumerate(providers):
                params[f"provider_{i}"] = p

        sql = f"""
        SELECT
            service_name,
            provider,
            SUM(pretax_amount) AS total_cost,
            COUNT(DISTINCT resource_id) AS resource_count
        FROM billing_records
        {where_clause}
        GROUP BY service_name, provider
        ORDER BY total_cost DESC
        LIMIT {top_n}
        """

        return self.query(sql, params)

    def get_cost_by_label(
        self,
        start_date: date,
        end_date: date,
        label_key: str,
        providers: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        where_clause = "WHERE usage_start_date >= %(start_date)s AND usage_start_date < %(end_date)s"
        params = {"start_date": start_date, "end_date": end_date, "label_key": label_key}

        if providers:
            placeholders = ", ".join(f"%(provider_{i})s" for i in range(len(providers)))
            where_clause += f" AND provider IN ({placeholders})"
            for i, p in enumerate(providers):
                params[f"provider_{i}"] = p

        sql = f"""
        SELECT
            if(mapContains(tags, %(label_key)s), tags[% (label_key) s], 'unknown') AS label_value,
            provider,
            SUM(pretax_amount) AS total_cost,
            COUNT(DISTINCT resource_id) AS resource_count
        FROM billing_records
        {where_clause}
        GROUP BY label_value, provider
        ORDER BY total_cost DESC
        """

        return self.query(sql, params)

    def get_daily_cost_by_resource(
        self,
        start_date: date,
        end_date: date,
        resource_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        where_clause = "WHERE usage_start_date >= %(start_date)s AND usage_start_date < %(end_date)s"
        params = {"start_date": start_date, "end_date": end_date}

        if resource_id:
            where_clause += " AND resource_id = %(resource_id)s"
            params["resource_id"] = resource_id

        sql = f"""
        SELECT
            usage_start_date AS date,
            resource_id,
            service_name,
            provider,
            SUM(pretax_amount) AS total_cost
        FROM billing_records
        {where_clause}
        GROUP BY date, resource_id, service_name, provider
        ORDER BY date, total_cost DESC
        """

        return self.query(sql, params)

    def get_resource_ids(
        self,
        start_date: date,
        end_date: date,
        providers: Optional[List[str]] = None,
    ) -> List[str]:
        where_clause = "WHERE usage_start_date >= %(start_date)s AND usage_start_date < %(end_date)s"
        params = {"start_date": start_date, "end_date": end_date}

        if providers:
            placeholders = ", ".join(f"%(provider_{i})s" for i in range(len(providers)))
            where_clause += f" AND provider IN ({placeholders})"
            for i, p in enumerate(providers):
                params[f"provider_{i}"] = p

        sql = f"""
        SELECT DISTINCT resource_id
        FROM billing_records
        {where_clause}
        AND resource_id != ''
        """

        results = self.query(sql, params)
        return [r["resource_id"] for r in results]

    def get_recent_anomalies(self, days: int = 7, limit: int = 100) -> List[Dict[str, Any]]:
        sql = """
        SELECT *
        FROM cost_anomalies
        WHERE anomaly_date >= today() - INTERVAL %(days)s DAY
        ORDER BY anomaly_date DESC, severity, percentage_change DESC
        LIMIT %(limit)s
        """
        return self.query(sql, {"days": days, "limit": limit})

    def get_optimization_suggestions(self, limit: int = 100) -> List[Dict[str, Any]]:
        sql = """
        SELECT *
        FROM optimization_suggestions
        ORDER BY created_at DESC, estimated_savings DESC
        LIMIT %(limit)s
        """
        return self.query(sql, {"limit": limit})

    def clear_old_data(self, days: int = 365) -> int:
        client = self._get_client()
        if client is None:
            return 0

        try:
            result = client.execute(
                "SELECT COUNT(*) FROM billing_records WHERE usage_start_date < today() - INTERVAL %(days)s DAY",
                {"days": days},
            )
            count = result[0][0] if result else 0

            client.execute(
                "DELETE FROM billing_records WHERE usage_start_date < today() - INTERVAL %(days)s DAY",
                {"days": days},
            )
            return count
        except Exception as e:
            logger.error(f"Failed to clear old data: {e}")
            return 0
