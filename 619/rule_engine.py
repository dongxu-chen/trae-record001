import pandas as pd
from collections import defaultdict
from datetime import datetime, timedelta


class RuleEngine:
    def __init__(self, users_df, orders_df, devices_df, ip_records_df, addresses_df, graph_features):
        self.users_df = users_df
        self.orders_df = orders_df
        self.devices_df = devices_df
        self.ip_records_df = ip_records_df
        self.addresses_df = addresses_df
        self.graph_features = graph_features
        self.rule_results = {}

    def evaluate_all(self):
        self._rule_shared_device()
        self._rule_shared_ip()
        self._rule_shared_address()
        self._rule_burst_orders()
        self._rule_new_account_high_freq()
        self._rule_night_orders()
        self._rule_same_product_cluster()
        self._rule_low_price_high_freq()
        self._rule_suspicious_ip_type()
        self._rule_short_account_age()
        return self.rule_results

    def _add_rule_result(self, user_id, rule_name, score, detail):
        if user_id not in self.rule_results:
            self.rule_results[user_id] = []
        self.rule_results[user_id].append({
            "rule_name": rule_name,
            "score": score,
            "detail": detail
        })

    def _rule_shared_device(self):
        for user_id, features in self.graph_features.items():
            count = features["shared_device_count"]
            if count >= 5:
                self._add_rule_result(user_id, "同设备多账号", 30, f"该账号与{count}个其他账号共用设备")
            elif count >= 3:
                self._add_rule_result(user_id, "同设备多账号", 20, f"该账号与{count}个其他账号共用设备")
            elif count >= 1:
                self._add_rule_result(user_id, "同设备多账号", 8, f"该账号与{count}个其他账号共用设备")

    def _rule_shared_ip(self):
        for user_id, features in self.graph_features.items():
            count = features["shared_ip_count"]
            if count >= 5:
                self._add_rule_result(user_id, "同IP多账号", 25, f"该账号与{count}个其他账号共用IP")
            elif count >= 3:
                self._add_rule_result(user_id, "同IP多账号", 15, f"该账号与{count}个其他账号共用IP")
            elif count >= 1:
                self._add_rule_result(user_id, "同IP多账号", 5, f"该账号与{count}个其他账号共用IP")

    def _rule_shared_address(self):
        for user_id, features in self.graph_features.items():
            count = features["shared_address_count"]
            if count >= 5:
                self._add_rule_result(user_id, "同收货地址多账号", 28, f"该账号与{count}个其他账号共用收货地址")
            elif count >= 3:
                self._add_rule_result(user_id, "同收货地址多账号", 18, f"该账号与{count}个其他账号共用收货地址")
            elif count >= 1:
                self._add_rule_result(user_id, "同收货地址多账号", 6, f"该账号与{count}个其他账号共用收货地址")

    def _rule_burst_orders(self):
        user_orders = self.orders_df.groupby("user_id")
        for user_id, group in user_orders:
            if len(group) < 3:
                continue
            times = pd.to_datetime(group["order_time"]).sort_values()
            for window_hours in [1, 6, 24]:
                window_str = f"{window_hours}h"
                max_count = 0
                for i, t in enumerate(times):
                    end_time = t + timedelta(hours=window_hours)
                    count = ((times >= t) & (times <= end_time)).sum()
                    max_count = max(max_count, count)
                threshold = {1: 5, 6: 10, 24: 15}.get(window_hours, 10)
                if max_count >= threshold:
                    self._add_rule_result(
                        user_id, f"短时爆发下单({window_str})",
                        min(25, max_count * 2),
                        f"{window_str}内最多下单{max_count}单"
                    )
                    break

    def _rule_new_account_high_freq(self):
        user_orders = self.orders_df.groupby("user_id")
        for user_id, group in user_orders:
            user_row = self.users_df[self.users_df["user_id"] == user_id]
            if len(user_row) == 0:
                continue
            account_age = user_row.iloc[0]["account_age_days"]
            order_count = len(group)
            if account_age < 60 and order_count > 8:
                self._add_rule_result(
                    user_id, "新账号高频下单",
                    22,
                    f"注册{account_age}天，下单{order_count}单"
                )
            elif account_age < 90 and order_count > 15:
                self._add_rule_result(
                    user_id, "新账号高频下单",
                    18,
                    f"注册{account_age}天，下单{order_count}单"
                )

    def _rule_night_orders(self):
        user_orders = self.orders_df.groupby("user_id")
        for user_id, group in user_orders:
            night_orders = group[(group["order_hour"] >= 0) & (group["order_hour"] <= 5)]
            ratio = len(night_orders) / len(group) if len(group) > 0 else 0
            if ratio > 0.6 and len(group) > 5:
                self._add_rule_result(
                    user_id, "深夜下单占比过高",
                    15,
                    f"深夜下单占比{ratio:.1%}({len(night_orders)}/{len(group)}单)"
                )

    def _rule_same_product_cluster(self):
        user_orders = self.orders_df.groupby("user_id")
        for user_id, group in user_orders:
            if len(group) < 3:
                continue
            product_counts = group["product_name"].value_counts()
            max_same = product_counts.max()
            same_ratio = max_same / len(group)
            if same_ratio > 0.7 and len(group) > 5:
                self._add_rule_result(
                    user_id, "同商品集中购买",
                    15,
                    f"同一商品占比{same_ratio:.1%}"
                )

    def _rule_low_price_high_freq(self):
        user_orders = self.orders_df.groupby("user_id")
        for user_id, group in user_orders:
            avg_amount = group["amount"].mean()
            order_count = len(group)
            if avg_amount < 50 and order_count > 8:
                self._add_rule_result(
                    user_id, "低价高频下单",
                    18,
                    f"均价{avg_amount:.1f}元，共{order_count}单"
                )

    def _rule_suspicious_ip_type(self):
        suspicious_types = {"VPN", "代理", "机房"}
        user_ips = self.ip_records_df.groupby("user_id")
        for user_id, group in user_ips:
            sus_count = group[group["ip_type"].isin(suspicious_types)].shape[0]
            total = len(group)
            if sus_count > 0:
                self._add_rule_result(
                    user_id, "可疑IP类型",
                    min(20, sus_count * 10),
                    f"使用{suspicious_types & set(group['ip_type'].unique())}类型IP({sus_count}/{total})"
                )

    def _rule_short_account_age(self):
        for _, row in self.users_df.iterrows():
            user_id = row["user_id"]
            age = row["account_age_days"]
            if age < 30:
                self._add_rule_result(user_id, "极新账号", 10, f"账号仅注册{age}天")
            elif age < 60:
                self._add_rule_result(user_id, "较新账号", 5, f"账号注册{age}天")

    def get_user_total_rule_score(self, user_id):
        if user_id not in self.rule_results:
            return 0, []
        rules = self.rule_results[user_id]
        total = sum(r["score"] for r in rules)
        return min(total, 100), rules
