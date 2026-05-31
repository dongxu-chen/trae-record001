import re
from typing import List, Dict, Any, Optional
from collections import Counter


class JudgmentPredictor:
    JUDGMENT_TEMPLATES = {
        "民间借贷纠纷": {
            "likely_outcomes": ["支持全部诉讼请求", "部分支持诉讼请求", "驳回诉讼请求"],
            "amount_fields": ["本金", "利息", "违约金", "诉讼费"],
            "typical_results": {
                "支持全部诉讼请求": 0.45,
                "部分支持诉讼请求": 0.45,
                "驳回诉讼请求": 0.10,
            },
            "partial_support_patterns": [
                "利率超过法定上限",
                "利息约定不明确",
                "部分款项无证据支持",
                "诉讼时效抗辩成立",
            ],
            "key_determinants": [
                "是否有书面借据",
                "是否实际交付借款",
                "利率是否超过法定上限",
                "是否超过诉讼时效",
                "被告是否认可借款事实",
            ],
        },
        "合同纠纷": {
            "likely_outcomes": ["支持全部诉讼请求", "部分支持诉讼请求", "驳回诉讼请求"],
            "amount_fields": ["合同款", "违约金", "赔偿金", "诉讼费"],
            "typical_results": {
                "支持全部诉讼请求": 0.35,
                "部分支持诉讼请求": 0.50,
                "驳回诉讼请求": 0.15,
            },
            "partial_support_patterns": [
                "违约金过高予以调整",
                "双方均有违约行为",
                "损失举证不足",
                "合同部分无效",
            ],
            "key_determinants": [
                "合同是否有效",
                "是否构成根本违约",
                "违约金是否过高",
                "是否存在不可抗力",
                "损失金额是否可证明",
            ],
        },
        "买卖合同纠纷": {
            "likely_outcomes": ["支持全部诉讼请求", "部分支持诉讼请求", "驳回诉讼请求"],
            "amount_fields": ["货款", "违约金", "赔偿金", "诉讼费"],
            "typical_results": {
                "支持全部诉讼请求": 0.40,
                "部分支持诉讼请求": 0.45,
                "驳回诉讼请求": 0.15,
            },
            "partial_support_patterns": [
                "货物存在质量问题扣减",
                "违约金过高予以调整",
                "部分货物未验收",
            ],
            "key_determinants": [
                "是否完成交付",
                "货物是否符合约定",
                "是否验收合格",
                "货款金额是否确认",
            ],
        },
        "劳动争议": {
            "likely_outcomes": ["支持全部诉讼请求", "部分支持诉讼请求", "驳回诉讼请求"],
            "amount_fields": ["工资", "经济补偿金", "赔偿金", "诉讼费"],
            "typical_results": {
                "支持全部诉讼请求": 0.30,
                "部分支持诉讼请求": 0.55,
                "驳回诉讼请求": 0.15,
            },
            "partial_support_patterns": [
                "赔偿金计算标准调整",
                "部分工资请求超过仲裁时效",
                "经济补偿金年限认定差异",
            ],
            "key_determinants": [
                "是否存在劳动关系",
                "解除是否合法",
                "工资标准是否可证明",
                "是否经过仲裁前置",
            ],
        },
    }

    DEFAULT_TEMPLATE = {
        "likely_outcomes": ["支持全部诉讼请求", "部分支持诉讼请求", "驳回诉讼请求"],
        "amount_fields": ["诉讼标的", "利息/违约金", "诉讼费"],
        "typical_results": {
            "支持全部诉讼请求": 0.35,
            "部分支持诉讼请求": 0.45,
            "驳回诉讼请求": 0.20,
        },
        "partial_support_patterns": ["部分请求缺乏证据支持", "金额计算有误"],
        "key_determinants": ["事实认定", "法律适用", "证据充分性"],
    }

    def predict(
        self,
        query_analysis: Dict[str, Any],
        similar_cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        case_type = query_analysis.get("case_type", "")
        template = self.JUDGMENT_TEMPLATES.get(case_type, self.DEFAULT_TEMPLATE)

        base_probs = dict(template["typical_results"])

        case_weighted = self._adjust_by_similar_cases(base_probs, similar_cases)

        determinants = self._analyze_determinants(query_analysis, template)

        amount_prediction = self._predict_amounts(query_analysis, similar_cases, case_type)

        confidence = self._calculate_confidence(similar_cases, query_analysis)

        most_likely = max(case_weighted, key=case_weighted.get)

        reasoning = self._generate_reasoning(
            most_likely, case_type, determinants, similar_cases
        )

        return {
            "predicted_outcome": most_likely,
            "outcome_probabilities": {
                k: round(v, 4) for k, v in case_weighted.items()
            },
            "amount_prediction": amount_prediction,
            "key_determinants": determinants,
            "confidence": round(confidence, 4),
            "reasoning": reasoning,
            "partial_support_risks": template.get("partial_support_patterns", []),
            "reference_case_count": len(similar_cases),
        }

    def _adjust_by_similar_cases(
        self,
        base_probs: Dict[str, float],
        similar_cases: List[Dict[str, Any]],
    ) -> Dict[str, float]:
        if not similar_cases:
            return base_probs

        adjusted = dict(base_probs)

        favorable_indicators = ["支持", "偿还", "支付", "返还", "解除", "赔偿"]
        unfavorable_indicators = ["驳回", "不予支持", "无事实依据", "缺乏证据"]

        favorable_weight = 0.0
        unfavorable_weight = 0.0

        for case in similar_cases[:5]:
            score = case.get("similarity_score", 0.5)
            desc = case.get("description", "") + case.get("summary", "")

            fav_count = sum(1 for kw in favorable_indicators if kw in desc)
            unfav_count = sum(1 for kw in unfavorable_indicators if kw in desc)

            favorable_weight += fav_count * score
            unfavorable_weight += unfav_count * score

        total = favorable_weight + unfavorable_weight
        if total > 0:
            favor_ratio = favorable_weight / total
            adjusted["支持全部诉讼请求"] = base_probs.get("支持全部诉讼请求", 0.35) * (0.5 + favor_ratio * 0.5)
            adjusted["驳回诉讼请求"] = base_probs.get("驳回诉讼请求", 0.20) * (1.5 - favor_ratio * 0.5)
            adjusted["部分支持诉讼请求"] = 1.0 - adjusted["支持全部诉讼请求"] - adjusted["驳回诉讼请求"]

        total_prob = sum(adjusted.values())
        if total_prob > 0:
            for k in adjusted:
                adjusted[k] /= total_prob

        return adjusted

    def _analyze_determinants(
        self,
        query_analysis: Dict[str, Any],
        template: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        determinants = []
        entities = query_analysis.get("legal_entities", {})
        key_points = query_analysis.get("key_points", [])

        all_text = " ".join(key_points) + str(entities)

        evidence_list = entities.get("证据", [])
        has_written_evidence = any(
            kw in " ".join(evidence_list)
            for kw in ["合同", "协议", "借条", "欠条"]
        )
        has_payment_evidence = any(
            kw in " ".join(evidence_list)
            for kw in ["转账", "银行流水", "收据"]
        )

        if has_written_evidence:
            determinants.append({
                "factor": "书面证据充分",
                "impact": "positive",
                "description": "存在合同/借条等书面证据，有利于事实认定",
                "weight": 0.8,
            })
        else:
            determinants.append({
                "factor": "书面证据不足",
                "impact": "negative",
                "description": "缺乏合同/借条等书面证据，事实认定可能存在困难",
                "weight": 0.6,
            })

        if has_payment_evidence:
            determinants.append({
                "factor": "交付凭证充分",
                "impact": "positive",
                "description": "存在转账记录等交付凭证，可证明款项实际交付",
                "weight": 0.7,
            })

        amounts = entities.get("金额", [])
        if amounts:
            determinants.append({
                "factor": "金额明确",
                "impact": "positive",
                "description": f"涉案金额明确（{', '.join(amounts[:3])}），有利于裁判量化",
                "weight": 0.6,
            })

        if "未偿还" in all_text or "拖欠" in all_text or "未还" in all_text:
            determinants.append({
                "factor": "违约事实明确",
                "impact": "positive",
                "description": "对方未履行还款/付款义务，违约事实较为明确",
                "weight": 0.7,
            })

        if "质量" in all_text or "瑕疵" in all_text:
            determinants.append({
                "factor": "质量争议",
                "impact": "negative",
                "description": "存在质量问题争议，可能影响判决支持程度",
                "weight": 0.5,
            })

        if "经济困难" in all_text or "疫情影响" in all_text:
            determinants.append({
                "factor": "客观困难抗辩",
                "impact": "neutral",
                "description": "对方提出客观困难抗辩，可能影响履行方式但一般不影响判决结果",
                "weight": 0.3,
            })

        for det_kw in template.get("key_determinants", []):
            already_covered = any(d["factor"] == det_kw for d in determinants)
            if not already_covered:
                determinants.append({
                    "factor": det_kw,
                    "impact": "neutral",
                    "description": f"需进一步查明：{det_kw}",
                    "weight": 0.4,
                })

        determinants.sort(key=lambda x: x["weight"], reverse=True)
        return determinants[:8]

    def _predict_amounts(
        self,
        query_analysis: Dict[str, Any],
        similar_cases: List[Dict[str, Any]],
        case_type: str,
    ) -> Dict[str, Any]:
        entities = query_analysis.get("legal_entities", {})
        amounts_str = entities.get("金额", [])

        claimed_amount = 0.0
        for a in amounts_str:
            val = self._parse_amount(a)
            if val > claimed_amount:
                claimed_amount = val

        if claimed_amount == 0 and similar_cases:
            case_amounts = []
            for case in similar_cases[:5]:
                case_entities = case.get("legal_entities", {})
                for a in case_entities.get("金额", []):
                    val = self._parse_amount(a)
                    if val > 0:
                        case_amounts.append(val)
            if case_amounts:
                claimed_amount = sum(case_amounts) / len(case_amounts)

        template = self.JUDGMENT_TEMPLATES.get(case_type, self.DEFAULT_TEMPLATE)
        amount_fields = template.get("amount_fields", ["诉讼标的"])

        predictions = {}
        if claimed_amount > 0:
            support_rate = 0.75
            for case in similar_cases[:5]:
                score = case.get("similarity_score", 0.5)
                if score > 0.6:
                    support_rate = min(support_rate + 0.05, 0.95)
                elif score < 0.4:
                    support_rate = max(support_rate - 0.05, 0.40)

            principal = claimed_amount
            interest_rate = 0.0
            all_text = " ".join(query_analysis.get("key_points", []))
            if "月利率2%" in all_text or "年利率24%" in all_text:
                interest_rate = 0.24
            elif "月利率3%" in all_text:
                interest_rate = 0.24
            elif "年利率15%" in all_text:
                interest_rate = 0.15
            elif "利率" in all_text:
                interest_rate = 0.18

            interest_amount = principal * interest_rate * 0.5 if interest_rate > 0 else 0

            predicted_total = principal * support_rate + interest_amount * support_rate * 0.8

            predictions = {
                "claimed_amount": claimed_amount,
                "predicted_principal": round(principal * support_rate, 2),
                "predicted_interest": round(interest_amount * support_rate * 0.8, 2),
                "predicted_total": round(predicted_total, 2),
                "support_rate": round(support_rate, 4),
                "breakdown": {
                    field: round(predicted_total / len(amount_fields), 2) if amount_fields else round(predicted_total, 2)
                    for field in amount_fields
                },
            }
        else:
            predictions = {
                "claimed_amount": 0,
                "predicted_principal": 0,
                "predicted_interest": 0,
                "predicted_total": 0,
                "support_rate": 0,
                "breakdown": {},
            }

        return predictions

    def _parse_amount(self, amount_str: str) -> float:
        amount_str = amount_str.replace(",", "").replace("元", "")
        if "万" in amount_str:
            amount_str = amount_str.replace("万", "")
            try:
                return float(amount_str) * 10000
            except ValueError:
                return 0
        try:
            return float(amount_str)
        except ValueError:
            return 0

    def _calculate_confidence(
        self,
        similar_cases: List[Dict[str, Any]],
        query_analysis: Dict[str, Any],
    ) -> float:
        if not similar_cases:
            return 0.2

        avg_similarity = sum(c.get("similarity_score", 0) for c in similar_cases) / len(similar_cases)

        type_match = sum(
            1 for c in similar_cases
            if c.get("case_type") == query_analysis.get("case_type")
        ) / len(similar_cases) if similar_cases else 0

        evidence_count = len(query_analysis.get("legal_entities", {}).get("证据", []))
        evidence_bonus = min(evidence_count * 0.05, 0.15)

        confidence = avg_similarity * 0.5 + type_match * 0.3 + evidence_bonus + 0.1
        return min(confidence, 0.95)

    def _generate_reasoning(
        self,
        predicted_outcome: str,
        case_type: str,
        determinants: List[Dict[str, Any]],
        similar_cases: List[Dict[str, Any]],
    ) -> List[str]:
        reasoning = []

        positive_factors = [d for d in determinants if d["impact"] == "positive"]
        negative_factors = [d for d in determinants if d["impact"] == "negative"]

        if predicted_outcome == "支持全部诉讼请求":
            reasoning.append(f"基于{len(similar_cases)}个相似{case_type}案例统计分析，判决预测为支持全部诉讼请求。")
            if positive_factors:
                reasons = "、".join(f["factor"] for f in positive_factors[:3])
                reasoning.append(f"有利因素：{reasons}。")
        elif predicted_outcome == "部分支持诉讼请求":
            reasoning.append(f"基于{len(similar_cases)}个相似{case_type}案例统计分析，判决预测为部分支持诉讼请求。")
            if positive_factors:
                reasons = "、".join(f["factor"] for f in positive_factors[:2])
                reasoning.append(f"有利因素：{reasons}。")
            if negative_factors:
                risks = "、".join(f["factor"] for f in negative_factors[:2])
                reasoning.append(f"风险因素：{risks}，可能导致部分请求不被支持。")
        else:
            reasoning.append(f"基于{len(similar_cases)}个相似{case_type}案例统计分析，判决预测为驳回诉讼请求。")
            if negative_factors:
                risks = "、".join(f["factor"] for f in negative_factors[:3])
                reasoning.append(f"不利因素：{risks}。")

        if similar_cases:
            high_sim = [c for c in similar_cases if c.get("similarity_score", 0) >= 0.6]
            if high_sim:
                reasoning.append(f"其中{len(high_sim)}个高度相似案例可作为强参考依据。")

        return reasoning
