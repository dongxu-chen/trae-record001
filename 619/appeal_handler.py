import pandas as pd
import uuid
from datetime import datetime
from collections import defaultdict


class AppealHandler:
    def __init__(self, users_df, orders_df, scored_df):
        self.users_df = users_df
        self.orders_df = orders_df
        self.scored_df = scored_df
        self.appeals = []
        self.appeal_id_counter = 1

    def create_appeal(self, order_id, appeal_reason, evidence="",
                      submitter_role="商家"):
        order = self.orders_df[self.orders_df["order_id"] == order_id]
        if len(order) == 0:
            return None, "订单不存在"

        order = order.iloc[0]
        user_id = order["user_id"]

        user_risk = self.scored_df[self.scored_df["user_id"] == user_id]
        risk_level = user_risk["risk_level"].values[0] if len(user_risk) > 0 else "正常"

        appeal = {
            "appeal_id": f"AP{self.appeal_id_counter:06d}",
            "order_id": order_id,
            "user_id": user_id,
            "submitter_role": submitter_role,
            "appeal_reason": appeal_reason,
            "evidence": evidence,
            "submit_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "status": "待审核",
            "original_risk_level": risk_level,
            "reviewer": None,
            "review_time": None,
            "review_comment": "",
            "final_decision": None,
            "adjusted_risk_level": None,
        }
        self.appeals.append(appeal)
        self.appeal_id_counter += 1

        return appeal, "申诉提交成功"

    def review_appeal(self, appeal_id, decision, reviewer, comment="", adjust_score=None):
        for appeal in self.appeals:
            if appeal["appeal_id"] == appeal_id:
                appeal["status"] = "已审核"
                appeal["reviewer"] = reviewer
                appeal["review_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                appeal["review_comment"] = comment
                appeal["final_decision"] = decision

                if decision == "通过":
                    appeal["adjusted_risk_level"] = "正常"
                elif decision == "部分通过":
                    appeal["adjusted_risk_level"] = "低风险"
                else:
                    appeal["adjusted_risk_level"] = appeal["original_risk_level"]

                return appeal, "审核完成"
        return None, "申诉不存在"

    def get_appeals_by_status(self, status=None):
        if status:
            return [a for a in self.appeals if a["status"] == status]
        return self.appeals

    def get_appeals_by_user(self, user_id):
        return [a for a in self.appeals if a["user_id"] == user_id]

    def get_appeal_statistics(self):
        stats = {
            "total": len(self.appeals),
            "pending": len([a for a in self.appeals if a["status"] == "待审核"]),
            "approved": len([a for a in self.appeals if a["final_decision"] == "通过"]),
            "partial": len([a for a in self.appeals if a["final_decision"] == "部分通过"]),
            "rejected": len([a for a in self.appeals if a["final_decision"] == "驳回"]),
            "approval_rate": 0
        }
        if len(self.appeals) > 0:
            stats["approval_rate"] = round(
                (stats["approved"] + stats["partial"]) / len(self.appeals), 2
            )
        return stats

    def generate_mock_appeals(self, n=15):
        import random
        risk_orders = self.scored_df[
            self.scored_df["risk_level"].isin(["高风险", "中风险"])]
        for _, row in risk_orders.iterrows():
            if len(self.appeals) >= n:
                break

            user_id = row["user_id"]
            user_orders = self.orders_df[self.orders_df["user_id"] == user_id]
            if len(user_orders) > 0:
                order_id = user_orders.iloc[0]["order_id"]
                reasons = [
                    "正常交易，客户真实订单为正常采购",
                    "老客户复购，非刷单",
                    "批量采购用于员工福利",
                    "误判，所有订单均为真实消费",
                    "客户正常行为，非刷单",
                ]
                reviewer_names = ["张经理", "李主管", "王总监", "赵组长"]

                reason = random.choice(reasons)

                appeal, _ = self.create_appeal(
                    order_id,
                    reason,
                    evidence="提供了聊天记录截图、物流凭证、支付凭证",
                    submitter_role="商家"
                )

                if random.random() > 0.3:
                    decision = random.choice(["通过", "部分通过", "驳回"])
                    self.review_appeal(
                        appeal["appeal_id"],
                        decision,
                        random.choice(reviewer_names),
                        comment="审核完成",
                    )

    def get_fraud_reasons_distribution(self):
        reason_counts = defaultdict(int)
        for appeal in self.appeals:
            reason_counts[appeal["appeal_reason"]] += 1
        return dict(reason_counts)
