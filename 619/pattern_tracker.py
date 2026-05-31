import pandas as pd
import numpy as np
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import json


class PatternEvolutionTracker:
    def __init__(self, orders_df, users_df, rule_results, gang_analysis=None):
        self.orders_df = orders_df
        self.users_df = users_df
        self.rule_results = rule_results
        self.gang_analysis = gang_analysis or {}
        self.time_periods = []
        self.pattern_history = []
        self.alerts = []

    def analyze_time_periods(self, period_days=15):
        orders = self.orders_df.copy()
        orders["order_time"] = pd.to_datetime(orders["order_time"])
        min_date = orders["order_time"].min()
        max_date = orders["order_time"].max()

        periods = []
        current = min_date
        period_id = 1
        while current <= max_date:
            period_end = current + timedelta(days=period_days)
            period_orders = orders[
                (orders["order_time"] >= current) &
                (orders["order_time"] < period_end)
            ]
            if len(period_orders) > 0:
                periods.append({
                    "period_id": period_id,
                    "start_date": current.strftime("%Y-%m-%d"),
                    "end_date": period_end.strftime("%Y-%m-%d"),
                    "orders": period_orders,
                    "user_ids": set(period_orders["user_id"].unique())
                })
                period_id += 1
            current = period_end

        self.time_periods = periods
        return periods

    def extract_period_patterns(self):
        if not self.time_periods:
            self.analyze_time_periods()

        pattern_history = []
        for period in self.time_periods:
            pattern = self._extract_single_period_pattern(period)
            pattern_history.append(pattern)

        self.pattern_history = pattern_history
        return pattern_history

    def _extract_single_period_pattern(self, period):
        orders = period["orders"]
        user_ids = period["user_ids"]

        pattern = {
            "period_id": period["period_id"],
            "start_date": period["start_date"],
            "end_date": period["end_date"],
            "total_orders": len(orders),
            "unique_users": len(user_ids),
            "avg_order_amount": round(orders["amount"].mean(), 2),
            "median_order_amount": round(orders["amount"].median(), 2),
            "low_value_ratio": round((orders["amount"] < 30).mean(), 3),
            "night_order_ratio": round(
                ((orders["order_hour"] >= 0) & (orders["order_hour"] <= 5)).mean(), 3
            ),
            "category_distribution": orders["category"].value_counts().to_dict(),
            "top_products": orders["product_name"].value_counts().head(5).to_dict(),
        }

        period_rules = defaultdict(int)
        period_rule_scores = defaultdict(int)
        for user_id in user_ids:
            if user_id in self.rule_results:
                for rule in self.rule_results[user_id]:
                    period_rules[rule["rule_name"]] += 1
                    period_rule_scores[rule["rule_name"]] += rule["score"]

        pattern["rule_hit_counts"] = dict(period_rules)
        pattern["rule_hit_scores"] = dict(period_rule_scores)
        pattern["top_rules"] = sorted(
            period_rules.items(), key=lambda x: x[1], reverse=True
        )[:5]

        period_users = self.users_df[self.users_df["user_id"].isin(user_ids)]
        pattern["avg_account_age"] = round(period_users["account_age_days"].mean(), 1)
        pattern["new_account_ratio"] = round(
            (period_users["account_age_days"] < 60).mean(), 3
        )

        return pattern

    def detect_pattern_changes(self, threshold=0.3):
        if len(self.pattern_history) < 2:
            return []

        changes = []
        for i in range(1, len(self.pattern_history)):
            prev = self.pattern_history[i - 1]
            curr = self.pattern_history[i]

            period_changes = {
                "period_id": curr["period_id"],
                "from_period": prev["period_id"],
                "to_period": curr["period_id"],
                "date_range": f"{prev['start_date']} → {curr['end_date']}",
                "changes": []
            }

            metrics_to_check = [
                ("avg_order_amount", "客单价"),
                ("low_value_ratio", "低价单占比"),
                ("night_order_ratio", "深夜单占比"),
                ("new_account_ratio", "新账号占比"),
            ]

            for metric, name in metrics_to_check:
                prev_val = prev[metric]
                curr_val = curr[metric]
                if prev_val > 0:
                    change_pct = (curr_val - prev_val) / prev_val
                    if abs(change_pct) >= threshold:
                        direction = "上升" if change_pct > 0 else "下降"
                        period_changes["changes"].append({
                            "metric": name,
                            "direction": direction,
                            "change_pct": round(change_pct, 3),
                            "prev_value": round(prev_val, 3),
                            "curr_value": round(curr_val, 3)
                        })

            prev_rules = set(prev["rule_hit_counts"].keys())
            curr_rules = set(curr["rule_hit_counts"].keys())
            new_rules = curr_rules - prev_rules
            disappeared_rules = prev_rules - curr_rules

            if new_rules:
                period_changes["changes"].append({
                    "metric": "新增触发规则",
                    "details": list(new_rules)
                })

            top_prev_products = set(prev["top_products"].keys())
            top_curr_products = set(curr["top_products"].keys())
            new_hot_products = top_curr_products - top_prev_products
            if new_hot_products:
                period_changes["changes"].append({
                    "metric": "新热门刷单商品",
                    "details": list(new_hot_products)
                })

            if period_changes["changes"]:
                changes.append(period_changes)

        self.changes = changes
        return changes

    def generate_alerts(self):
        alerts = []

        for change in self.changes:
            alert_level = self._assess_alert_level(change)
            if alert_level != "normal":
                alerts.append({
                    "alert_id": len(alerts) + 1,
                    "level": alert_level,
                    "period": change["date_range"],
                    "summary": self._generate_alert_summary(change),
                    "details": change["changes"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        if self.gang_analysis:
            high_risk_gangs = [
                g for g in self.gang_analysis.values()
                if "高危" in g["risk_level"]
            ]
            if high_risk_gangs:
                alerts.append({
                    "alert_id": len(alerts) + 1,
                    "level": "critical",
                    "period": "持续监测",
                    "summary": f"检测到{len(high_risk_gangs)}个高危刷单团伙",
                    "details": [
                        f"团伙{g['gang_id']}: {g['member_count']}人, 手法: {', '.join(g['modus_operandi'])}"
                        for g in high_risk_gangs
                    ],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        if self.pattern_history:
            latest = self.pattern_history[-1]
            if latest["new_account_ratio"] > 0.5:
                alerts.append({
                    "alert_id": len(alerts) + 1,
                    "level": "warning",
                    "period": latest["end_date"],
                    "summary": "近期新账号占比过高，可能存在注册机批量注册",
                    "details": [f"新账号占比: {latest['new_account_ratio']:.1%}"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

            if latest["night_order_ratio"] > 0.3:
                alerts.append({
                    "alert_id": len(alerts) + 1,
                    "level": "warning",
                    "period": latest["end_date"],
                    "summary": "深夜订单占比显著上升，疑似机器刷单",
                    "details": [f"深夜单占比: {latest['night_order_ratio']:.1%}"],
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

        self.alerts = alerts
        return alerts

    def _assess_alert_level(self, change):
        high_risk_metrics = ["低价单占比", "深夜单占比", "新账号占比"]
        for c in change["changes"]:
            if c.get("metric") in high_risk_metrics and c.get("direction") == "上升":
                if c.get("change_pct", 0) > 0.5:
                    return "critical"
                elif c.get("change_pct", 0) > 0.3:
                    return "warning"
        if any("新热门刷单商品" in c.get("metric", "") for c in change["changes"]):
            return "warning"
        return "normal"

    def _generate_alert_summary(self, change):
        summaries = []
        for c in change["changes"]:
            if "change_pct" in c:
                summaries.append(f"{c['metric']}{c['direction']}{c['change_pct']:.0%}")
            elif "details" in c:
                summaries.append(f"{c['metric']}: {', '.join(c['details'][:2])}")
        return "; ".join(summaries[:3])

    def get_pattern_trend_data(self):
        if not self.pattern_history:
            return pd.DataFrame()

        trend_data = []
        for pattern in self.pattern_history:
            trend_data.append({
                "period": f"P{pattern['period_id']}\n{pattern['start_date']}",
                "avg_order_amount": pattern["avg_order_amount"],
                "low_value_ratio": pattern["low_value_ratio"] * 100,
                "night_order_ratio": pattern["night_order_ratio"] * 100,
                "new_account_ratio": pattern["new_account_ratio"] * 100,
                "total_orders": pattern["total_orders"],
            })

        return pd.DataFrame(trend_data)

    def get_rule_trend_data(self):
        if not self.pattern_history:
            return pd.DataFrame()

        all_rules = set()
        for pattern in self.pattern_history:
            all_rules.update(pattern["rule_hit_counts"].keys())

        rule_data = []
        for pattern in self.pattern_history:
            row = {
                "period": f"P{pattern['period_id']}\n{pattern['start_date']}",
            }
            for rule in all_rules:
                row[rule] = pattern["rule_hit_counts"].get(rule, 0)
            rule_data.append(row)

        return pd.DataFrame(rule_data)
