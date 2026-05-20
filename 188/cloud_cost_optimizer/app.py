import logging
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from .cloud_providers import AWSProvider, AliyunProvider, TencentProvider, BillingRecord
from .database import ClickHouseStore, CostAllocator, ProductMapper
from .analysis import TrendAnalyzer, AnomalyDetector, BudgetManager, CostForecaster
from .optimization import ResourceOptimizer, RIPlanner
from .config import Settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class CloudCostOptimizer:
    """多云费用分析优化工具主类"""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or Settings.from_env()
        self.store = ClickHouseStore(self.settings.clickhouse)
        self.allocator = CostAllocator(self.settings)
        self.product_mapper = ProductMapper()
        self.trend_analyzer = TrendAnalyzer(self.settings)
        self.anomaly_detector = AnomalyDetector(self.settings)
        self.budget_manager = BudgetManager(self.settings)
        self.cost_forecaster = CostForecaster(self.settings)
        self.optimizer = ResourceOptimizer(self.settings)
        self.ri_planner = RIPlanner(self.settings)

        self.providers = self._init_providers()

    def _init_providers(self) -> Dict[str, Any]:
        """初始化云厂商客户端"""
        providers = {}

        if self.settings.aws.enabled:
            providers["AWS"] = AWSProvider(
                access_key=self.settings.aws.access_key,
                secret_key=self.settings.aws.secret_key,
                region=self.settings.aws.region,
            )

        if self.settings.aliyun.enabled:
            providers["阿里云"] = AliyunProvider(
                access_key=self.settings.aliyun.access_key,
                secret_key=self.settings.aliyun.secret_key,
                region=self.settings.aliyun.region,
            )

        if self.settings.tencent.enabled:
            providers["腾讯云"] = TencentProvider(
                access_key=self.settings.tencent.access_key,
                secret_key=self.settings.tencent.secret_key,
                region=self.settings.tencent.region,
            )

        logger.info(f"Initialized {len(providers)} cloud providers: {list(providers.keys())}")
        return providers

    def fetch_and_store_billing_data(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """获取并存储账单数据"""
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today() + timedelta(days=1)

        logger.info(f"Fetching billing data from {start_date} to {end_date}")

        all_records: List[BillingRecord] = []
        results = {}

        for provider_name, provider in self.providers.items():
            try:
                records = provider.fetch_billing_records(start_date, end_date)
                inserted = self.store.insert_billing_records(records)
                all_records.extend(records)
                results[provider_name] = {
                    "records_count": len(records),
                    "inserted_count": inserted,
                    "total_cost": sum(r.pretax_amount for r in records),
                }
                logger.info(f"Fetched {len(records)} records from {provider_name}")
            except Exception as e:
                logger.error(f"Failed to fetch data from {provider_name}: {e}")
                results[provider_name] = {"error": str(e)}

        results["total"] = {
            "providers": len(self.providers),
            "total_records": len(all_records),
            "total_cost": sum(r.pretax_amount for r in all_records),
        }

        return results

    def run_cost_allocation(self, label_keys: Optional[List[str]] = None) -> Dict[str, Any]:
        """执行费用分摊"""
        label_keys = label_keys or self.settings.label_keys
        logger.info(f"Running cost allocation for labels: {label_keys}")

        start_date = date.today() - timedelta(days=30)
        end_date = date.today() + timedelta(days=1)

        all_records = self._get_all_records(start_date, end_date)
        if not all_records:
            return {"error": "No records available for allocation"}

        results = {}
        for label_key in label_keys:
            allocations = self.allocator.allocate_by_label(all_records, label_key)
            allocation_records = self.allocator.generate_allocation_records(
                all_records, label_key
            )
            self.store.insert_cost_allocation(allocation_records)
            results[label_key] = {
                "allocations": allocations,
                "record_count": len(allocation_records),
            }

        unallocated = self.allocator.get_unallocated_summary(all_records)
        results["unallocated"] = unallocated

        return results

    def run_trend_analysis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """执行趋势分析"""
        if start_date is None:
            start_date = date.today() - timedelta(days=90)
        if end_date is None:
            end_date = date.today() + timedelta(days=1)

        logger.info(f"Running trend analysis from {start_date} to {end_date}")

        all_records = self._get_all_records(start_date, end_date)
        if not all_records:
            return {"error": "No records available for trend analysis"}

        results = {
            "daily_trend": self.trend_analyzer.calculate_daily_trend(all_records),
            "service_trend": self.trend_analyzer.calculate_service_trend(all_records),
            "monthly_summary": self.trend_analyzer.calculate_monthly_summary(all_records),
            "growth_rate": self.trend_analyzer.calculate_growth_rate(all_records),
            "forecast": self.trend_analyzer.forecast_next_month(all_records),
        }

        return results

    def run_anomaly_detection(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """执行异常检测"""
        if start_date is None:
            start_date = date.today() - timedelta(days=60)
        if end_date is None:
            end_date = date.today() + timedelta(days=1)

        logger.info(f"Running anomaly detection from {start_date} to {end_date}")

        all_records = self._get_all_records(start_date, end_date)
        if not all_records:
            return {"error": "No records available for anomaly detection"}

        anomalies = self.anomaly_detector.detect_anomalies(all_records)
        new_resources = self.anomaly_detector.detect_new_resources(all_records)
        weekend_anomalies = self.anomaly_detector.detect_weekday_weekend_anomalies(all_records)

        all_anomalies = anomalies + new_resources + weekend_anomalies

        anomaly_dicts = [
            self.anomaly_detector.anomaly_to_dict(a) for a in all_anomalies
        ]
        self.store.insert_anomalies(anomaly_dicts)

        summary = self.anomaly_detector.generate_alert_summary(all_anomalies)
        summary["anomalies"] = anomaly_dicts

        return summary

    def run_optimization_analysis(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """执行优化分析"""
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today() + timedelta(days=1)

        logger.info(f"Running optimization analysis from {start_date} to {end_date}")

        all_records = self._get_all_records(start_date, end_date)
        if not all_records:
            return {"error": "No records available for optimization analysis"}

        resource_metrics = self._collect_resource_metrics(all_records, start_date, end_date)
        suggestions = self.optimizer.generate_all_suggestions(all_records, resource_metrics)

        suggestion_dicts = [
            self.optimizer.suggestion_to_dict(s) for s in suggestions
        ]
        self.store.insert_optimization_suggestions(suggestion_dicts)

        summary = self.optimizer.calculate_total_savings(suggestions)
        summary["suggestions"] = suggestion_dicts

        risky_count = sum(1 for s in suggestion_dicts if not s.get("can_release", True))
        summary["risky_suggestions_count"] = risky_count
        summary["safe_suggestions_count"] = len(suggestion_dicts) - risky_count

        return summary

    def run_product_mapping(
        self,
        records: Optional[List[BillingRecord]] = None,
    ) -> Dict[str, Any]:
        """执行产品名称统一映射"""
        if records is None:
            end_date = date.today() + timedelta(days=1)
            start_date = end_date - timedelta(days=30)
            records = self._get_all_records(start_date, end_date)

        if not records:
            return {"error": "No records available for product mapping"}

        mapped_records = []
        mapping_stats = {
            "total_records": len(records),
            "mapped_count": 0,
            "unmapped_count": 0,
            "by_provider": {},
            "by_category": defaultdict(int),
            "unmapped_services": defaultdict(set),
        }

        for record in records:
            mapping = self.product_mapper.map_product(
                record.provider, record.service_name, record.product_code
            )

            mapped_record = {
                **record.to_dict(),
                **mapping,
            }
            mapped_records.append(mapped_record)

            if mapping["mapping_found"]:
                mapping_stats["mapped_count"] += 1
                mapping_stats["by_category"][mapping["category"]] += 1
            else:
                mapping_stats["unmapped_count"] += 1
                mapping_stats["unmapped_services"][record.provider].add(record.service_name)

            provider_key = record.provider
            if provider_key not in mapping_stats["by_provider"]:
                mapping_stats["by_provider"][provider_key] = {
                    "total": 0,
                    "mapped": 0,
                    "unmapped": 0,
                }
            mapping_stats["by_provider"][provider_key]["total"] += 1
            if mapping["mapping_found"]:
                mapping_stats["by_provider"][provider_key]["mapped"] += 1
            else:
                mapping_stats["by_provider"][provider_key]["unmapped"] += 1

        for provider in mapping_stats["unmapped_services"]:
            mapping_stats["unmapped_services"][provider] = list(
                mapping_stats["unmapped_services"][provider]
            )

        mapping_stats["by_category"] = dict(mapping_stats["by_category"])

        return {
            "mapped_records": mapped_records,
            "mapping_stats": mapping_stats,
            "mapping_info": self.product_mapper.get_statistics(),
        }

    def generate_release_plan(
        self,
        resource_ids: List[str],
        all_records: Optional[List[BillingRecord]] = None,
    ) -> Dict[str, Any]:
        """生成资源释放计划"""
        if all_records is None:
            end_date = date.today() + timedelta(days=1)
            start_date = end_date - timedelta(days=30)
            all_records = self._get_all_records(start_date, end_date)

        plan = self.optimizer.dependency_checker.generate_release_plan(
            resource_ids, [], all_records
        )

        release_order = self.optimizer.dependency_checker.get_release_order(
            resource_ids, [], all_records
        )

        return {
            "release_plan": plan,
            "release_order": release_order,
            "can_release_count": sum(1 for p in plan if p["can_release"]),
            "risky_count": sum(1 for p in plan if not p["can_release"]),
        }

    def run_full_analysis(
        self,
        start_days: int = 90,
    ) -> Dict[str, Any]:
        """执行完整分析流程"""
        end_date = date.today() + timedelta(days=1)
        start_date = end_date - timedelta(days=start_days)

        logger.info(f"Running full analysis for last {start_days} days")

        results = {
            "billing_fetch": self.fetch_and_store_billing_data(
                start_date - timedelta(days=30), end_date
            ),
            "cost_allocation": self.run_cost_allocation(),
            "trend_analysis": self.run_trend_analysis(start_date, end_date),
            "anomaly_detection": self.run_anomaly_detection(start_date, end_date),
            "optimization": self.run_optimization_analysis(
                start_date - timedelta(days=30), end_date
            ),
        }

        return results

    def get_dashboard_data(
        self,
        days: int = 30,
    ) -> Dict[str, Any]:
        """获取仪表板数据"""
        end_date = date.today() + timedelta(days=1)
        start_date = end_date - timedelta(days=days)

        all_records = self._get_all_records(start_date, end_date)
        if not all_records:
            return {"error": "No data available"}

        total_cost = sum(r.pretax_amount for r in all_records)
        providers = set(r.provider for r in all_records)
        services = set(r.service_name for r in all_records)
        resources = set(r.resource_id for r in all_records if r.resource_id)

        cost_by_provider = {}
        for r in all_records:
            cost_by_provider[r.provider] = cost_by_provider.get(r.provider, 0) + r.pretax_amount

        cost_by_service = {}
        for r in all_records:
            cost_by_service[r.service_name] = cost_by_service.get(r.service_name, 0) + r.pretax_amount

        top_services = sorted(
            cost_by_service.items(), key=lambda x: x[1], reverse=True
        )[:10]

        daily_cost = {}
        for r in all_records:
            day = r.usage_start_date.isoformat()
            daily_cost[day] = daily_cost.get(day, 0) + r.pretax_amount

        return {
            "period_days": days,
            "total_cost": total_cost,
            "provider_count": len(providers),
            "service_count": len(services),
            "resource_count": len(resources),
            "cost_by_provider": cost_by_provider,
            "top_services": top_services,
            "daily_cost": daily_cost,
            "providers": list(providers),
        }

    def _get_all_records(
        self,
        start_date: date,
        end_date: date,
    ) -> List[BillingRecord]:
        """从数据库获取所有记录（如果数据库不可用则从API获取）"""
        records = []

        for provider_name, provider in self.providers.items():
            try:
                provider_records = provider.fetch_billing_records(start_date, end_date)
                records.extend(provider_records)
            except Exception as e:
                logger.error(f"Failed to get records from {provider_name}: {e}")

        return records

    def _collect_resource_metrics(
        self,
        records: List[BillingRecord],
        start_date: date,
        end_date: date,
    ) -> Dict[str, Dict[str, Any]]:
        """收集资源监控指标"""
        metrics = {}
        resource_info = {}

        for record in records:
            if record.resource_id:
                resource_info[record.resource_id] = {
                    "provider": record.provider,
                    "service_name": record.service_name,
                }

        for resource_id, info in resource_info.items():
            provider = self.providers.get(info["provider"])
            if provider:
                try:
                    metric = provider.get_resource_metrics(
                        resource_id,
                        info["service_name"],
                        start_date,
                        end_date,
                    )
                    if metric:
                        metrics[resource_id] = metric
                except Exception as e:
                    logger.debug(f"Failed to get metrics for {resource_id}: {e}")

        return metrics

    def get_provider_status(self) -> Dict[str, Any]:
        """获取各云厂商连接状态"""
        status = {}
        for name, provider in self.providers.items():
            try:
                status[name] = {
                    "enabled": True,
                    "region": provider.region if hasattr(provider, "region") else "unknown",
                }
            except Exception as e:
                status[name] = {"enabled": False, "error": str(e)}

        return status

    def run_budget_analysis(
        self,
        records: Optional[List[BillingRecord]] = None,
    ) -> Dict[str, Any]:
        """执行预算分析"""
        if records is None:
            end_date = date.today() + timedelta(days=1)
            start_date = end_date - timedelta(days=60)
            records = self._get_all_records(start_date, end_date)

        if not records:
            return {"error": "No records available for budget analysis"}

        dashboard = self.budget_manager.get_budget_dashboard(records)
        return dashboard

    def create_budget(
        self,
        name: str,
        amount: float,
        period: str = "monthly",
        scope: Optional[Dict[str, Any]] = None,
        alert_thresholds: Optional[List[float]] = None,
    ) -> Dict[str, Any]:
        """创建预算"""
        budget = self.budget_manager.create_budget(
            name=name,
            amount=amount,
            period=period,
            scope=scope,
            alert_thresholds=alert_thresholds,
        )
        return {
            "budget_id": budget.budget_id,
            "name": budget.name,
            "amount": budget.amount,
            "period": budget.period,
            "alert_thresholds": budget.alert_thresholds,
        }

    def list_budgets(self) -> List[Dict[str, Any]]:
        """列出所有预算"""
        budgets = self.budget_manager.list_budgets()
        return [
            {
                "budget_id": b.budget_id,
                "name": b.name,
                "amount": b.amount,
                "period": b.period,
                "is_active": b.is_active,
                "alert_thresholds": b.alert_thresholds,
                "scope": b.scope,
            }
            for b in budgets
        ]

    def update_budget(
        self,
        budget_id: str,
        amount: Optional[float] = None,
        name: Optional[str] = None,
        alert_thresholds: Optional[List[float]] = None,
        is_active: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """更新预算"""
        budget = self.budget_manager.update_budget(
            budget_id=budget_id,
            amount=amount,
            name=name,
            alert_thresholds=alert_thresholds,
            is_active=is_active,
        )
        if budget:
            return {
                "budget_id": budget.budget_id,
                "name": budget.name,
                "amount": budget.amount,
                "period": budget.period,
                "is_active": budget.is_active,
            }
        return None

    def delete_budget(self, budget_id: str) -> bool:
        """删除预算"""
        return self.budget_manager.delete_budget(budget_id)

    def run_ri_analysis(
        self,
        records: Optional[List[BillingRecord]] = None,
        analysis_days: int = 60,
    ) -> Dict[str, Any]:
        """执行RI购买分析"""
        if records is None:
            end_date = date.today() + timedelta(days=1)
            start_date = end_date - timedelta(days=analysis_days)
            records = self._get_all_records(start_date, end_date)

        if not records:
            return {"error": "No records available for RI analysis"}

        plan = self.ri_planner.generate_recommendations(records, analysis_days)
        return self.ri_planner.plan_to_dict(plan)

    def run_cost_forecast(
        self,
        records: Optional[List[BillingRecord]] = None,
    ) -> Dict[str, Any]:
        """执行费用预测"""
        if records is None:
            end_date = date.today() + timedelta(days=1)
            start_date = end_date - timedelta(days=90)
            records = self._get_all_records(start_date, end_date)

        if not records:
            return {"error": "No records available for cost forecast"}

        forecast = self.cost_forecaster.forecast_next_month(records)
        result = self.cost_forecaster.ensemble_to_dict(forecast)

        service_forecasts = self.cost_forecaster.forecast_by_service(records)
        result["service_forecasts"] = {
            service: self.cost_forecaster.ensemble_to_dict(fc)
            for service, fc in service_forecasts.items()
        }

        provider_forecasts = self.cost_forecaster.forecast_by_provider(records)
        result["provider_forecasts"] = {
            provider: self.cost_forecaster.ensemble_to_dict(fc)
            for provider, fc in provider_forecasts.items()
        }

        return result
