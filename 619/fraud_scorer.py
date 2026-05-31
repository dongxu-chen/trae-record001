import pandas as pd
from datetime import datetime


class FraudScorer:
    def __init__(self, users_df, orders_df, rule_results, ml_scores, graph_features, community_stats,
                 is_promotion=False, promotion_scale=0.75, custom_thresholds=None):
        self.users_df = users_df
        self.orders_df = orders_df
        self.rule_results = rule_results
        self.ml_scores = ml_scores
        self.graph_features = graph_features
        self.community_stats = community_stats
        self.is_promotion = is_promotion
        self.promotion_scale = promotion_scale
        self.scored_df = None
        self.used_thresholds = self._get_thresholds(custom_thresholds)

    RULE_WEIGHT = 0.45
    ML_WEIGHT = 0.35
    GRAPH_WEIGHT = 0.20

    def _get_thresholds(self, custom_thresholds):
        default = {
            "high_risk": 70,
            "medium_risk": 45,
            "low_risk": 25
        }
        if self.is_promotion:
            for key in default:
                default[key] = default[key] / self.promotion_scale
        if custom_thresholds:
            default.update(custom_thresholds)
        return default

    def set_promotion_mode(self, is_promotion, scale=0.75):
        self.is_promotion = is_promotion
        self.promotion_scale = scale
        self.used_thresholds = self._get_thresholds(None)

    def compute_composite_scores(self):
        records = []
        for _, user_row in self.users_df.iterrows():
            user_id = user_row["user_id"]
            rule_score, rules = self._get_rule_score(user_id)
            ml_score = self._get_ml_score(user_id)
            graph_score = self._get_graph_score(user_id)

            composite = (
                rule_score * self.RULE_WEIGHT
                + ml_score * self.ML_WEIGHT
                + graph_score * self.GRAPH_WEIGHT
            )
            composite = min(composite, 100)

            if self.is_promotion:
                composite = composite * self.promotion_scale

            risk_level = self._get_risk_level(composite)
            risk_orders = self._get_risk_orders(user_id)
            suggestions, actions = self._get_suggestions(risk_level, rules, ml_score, graph_score, composite)
            linked_users = self._get_linked_users(user_id)

            records.append({
                "user_id": user_id,
                "username": user_row["username"],
                "register_date": user_row["register_date"],
                "account_age_days": user_row["account_age_days"],
                "rule_score": round(rule_score, 1),
                "ml_score": round(ml_score, 1),
                "graph_score": round(graph_score, 1),
                "composite_score": round(composite, 1),
                "raw_composite_score": round(composite / self.promotion_scale if self.is_promotion else composite, 1),
                "risk_level": risk_level,
                "rule_details": rules,
                "n_risk_orders": len(risk_orders),
                "risk_order_ids": [o["order_id"] for o in risk_orders],
                "suggestions": suggestions,
                "enforcement_actions": actions,
                "linked_users": linked_users,
                "is_fraud_actual": user_row["is_fraud"],
            })

        self.scored_df = pd.DataFrame(records)
        self.scored_df = self.scored_df.sort_values("composite_score", ascending=False)
        return self.scored_df

    def _get_rule_score(self, user_id):
        if user_id not in self.rule_results:
            return 0, []
        rules = self.rule_results[user_id]
        total = sum(r["score"] for r in rules)
        return min(total, 100), rules

    def _get_ml_score(self, user_id):
        if user_id in self.ml_scores:
            return self.ml_scores[user_id]["ml_anomaly_score"]
        return 0

    def _get_graph_score(self, user_id):
        gf = self.graph_features.get(user_id, {})
        score = 0

        shared_dev = gf.get("shared_device_count", 0)
        shared_ip = gf.get("shared_ip_count", 0)
        shared_addr = gf.get("shared_address_count", 0)
        total_linked = gf.get("total_linked_users", 0)

        score += min(shared_dev * 8, 25)
        score += min(shared_ip * 6, 20)
        score += min(shared_addr * 7, 20)

        if total_linked >= 5:
            score += min(total_linked * 3, 20)
        elif total_linked >= 3:
            score += total_linked * 2

        for comm in self.community_stats:
            if user_id in comm["members"]:
                if comm["member_count"] >= 5:
                    score += 10
                elif comm["member_count"] >= 3:
                    score += 5
                break

        return min(score, 100)

    def _get_risk_level(self, score):
        if score >= self.used_thresholds["high_risk"]:
            return "高风险"
        elif score >= self.used_thresholds["medium_risk"]:
            return "中风险"
        elif score >= self.used_thresholds["low_risk"]:
            return "低风险"
        else:
            return "正常"

    def _get_risk_orders(self, user_id):
        user_orders = self.orders_df[self.orders_df["user_id"] == user_id]
        risk_orders = []
        for _, order in user_orders.iterrows():
            order_risk = 0
            if order["amount"] < 30:
                order_risk += 10
            if order["order_hour"] >= 0 and order["order_hour"] <= 5:
                order_risk += 15
            if order_risk > 0:
                risk_orders.append({
                    "order_id": order["order_id"],
                    "product_name": order["product_name"],
                    "amount": order["amount"],
                    "order_time": order["order_time"],
                    "order_risk": order_risk
                })
        return risk_orders

    def _get_suggestions(self, risk_level, rules, ml_score, graph_score, composite_score):
        suggestions = []
        actions = []

        if self.is_promotion:
            suggestions.append(f"🎉 当前为大促模式，阈值已放宽（系数：{self.promotion_scale}）")

        rule_names = [r["rule_name"] for r in rules]

        if "同设备多账号" in rule_names:
            suggestions.append("� 检查设备指纹是否被篡改")
            actions.append({"action": "设备校验", "severity": "中"})
        if "同IP多账号" in rule_names:
            suggestions.append("🌐 核查IP归属地及代理使用情况")
            actions.append({"action": "IP风险标记", "severity": "中"})
        if "同收货地址多账号" in rule_names:
            suggestions.append("📦 核实收货地址真实性")
            actions.append({"action": "地址复核", "severity": "高"})
        if "可疑IP类型" in rule_names:
            suggestions.append("� 建议启用二次验证")
            actions.append({"action": "二次验证", "severity": "中"})
        if "短时爆发下单(1h)" in rule_names or "短时爆发下单(6h)" in rule_names or "短时爆发下单(24h)" in rule_names:
            suggestions.append("⏱️ 检测到爆发式下单")
            actions.append({"action": "下单频率限制", "severity": "高"})
        if "新账号高频下单" in rule_names:
            suggestions.append("👶 新账号行为异常")
            actions.append({"action": "新账号观察期", "severity": "低"})
        if "深夜下单占比过高" in rule_names:
            suggestions.append("🌙 深夜下单模式可疑")
            actions.append({"action": "时段监控", "severity": "低"})

        if ml_score > 60:
            suggestions.append("🤖 ML模型检测到异常行为模式")
        if graph_score > 50:
            suggestions.append("🔗 图分析发现较强关联网络")
            actions.append({"action": "关联账号排查", "severity": "高"})

        if risk_level == "高风险":
            suggestions.insert(0, "🚫 立即冻结账号，进行人工审核")
            suggestions.insert(1, "� 关联账号需一并排查")
            actions.extend([
                {"action": "账号冻结", "severity": "紧急"},
                {"action": "限制下单权限", "severity": "高"},
                {"action": "订单取消/拦截", "severity": "高"},
                {"action": "佣金冻结", "severity": "高"},
                {"action": "店铺降权（卖家）", "severity": "高"},
            ])
        elif risk_level == "中风险":
            suggestions.insert(0, "⚠️ 建议人工复核近期订单")
            suggestions.insert(1, "🔍 加强该账号监控频率")
            actions.extend([
                {"action": "限制优惠券使用", "severity": "中"},
                {"action": "限制积分获取", "severity": "中"},
                {"action": "限制评价权限", "severity": "中"},
                {"action": "延长结算周期", "severity": "中"},
                {"action": "要求身份验证", "severity": "中"},
                {"action": "店铺降权警告（卖家）", "severity": "中"},
            ])
        elif risk_level == "低风险":
            suggestions.insert(0, "👁️ 持续关注账号行为")
            suggestions.insert(1, "📊 纳入观察名单")
            actions.extend([
                {"action": "搜索结果降权", "severity": "低"},
                {"action": "降低推荐曝光", "severity": "低"},
                {"action": "下单限速", "severity": "低"},
                {"action": "限制大额优惠券", "severity": "低"},
            ])
        else:
            suggestions.insert(0, "✅ 账号行为正常，无需处理")

        return suggestions, actions

    def _get_linked_users(self, user_id):
        gf = self.graph_features.get(user_id, {})
        linked = set()
        for key in ["shared_device_users", "shared_ip_users", "shared_address_users"]:
            for uid in gf.get(key, []):
                linked.add(uid)
        return list(linked)

    def get_summary(self):
        if self.scored_df is None:
            return None
        total = len(self.scored_df)
        high = len(self.scored_df[self.scored_df["risk_level"] == "高风险"])
        medium = len(self.scored_df[self.scored_df["risk_level"] == "中风险"])
        low = len(self.scored_df[self.scored_df["risk_level"] == "低风险"])
        normal = len(self.scored_df[self.scored_df["risk_level"] == "正常"])
        return {
            "total_users": total,
            "high_risk": high,
            "medium_risk": medium,
            "low_risk": low,
            "normal": normal,
            "avg_score": round(self.scored_df["composite_score"].mean(), 1),
            "max_score": round(self.scored_df["composite_score"].max(), 1),
            "is_promotion": self.is_promotion,
            "promotion_scale": self.promotion_scale,
            "thresholds": self.used_thresholds,
        }
