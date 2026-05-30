import sys
import os
import json
from typing import Dict, List, Any

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class DrugInteractionChecker:
    def __init__(self):
        self.interactions = self._load_interactions()
        self.medicine_aliases = self._load_aliases()

    def _load_interactions(self) -> List[Dict]:
        return [
            {
                "drug_a": "阿莫西林", "drug_b": "布洛芬",
                "severity": "minor",
                "description": "布洛芬可能轻微降低阿莫西林的血药浓度，但一般不影响疗效",
                "mechanism": "非甾体抗炎药可能影响肾小球滤过率",
                "recommendation": "可联合使用，但建议间隔服用",
                "evidence_level": "C"
            },
            {
                "drug_a": "阿莫西林", "drug_b": "氨氯地平",
                "severity": "moderate",
                "description": "阿莫西林可能影响氨氯地平的代谢，增加低血压风险",
                "mechanism": "CYP3A4酶竞争性抑制",
                "recommendation": "联合使用时需监测血压，注意体位性低血压",
                "evidence_level": "B"
            },
            {
                "drug_a": "布洛芬", "drug_b": "氨氯地平",
                "severity": "major",
                "description": "布洛芬可减弱氨氯地平的降压效果，并增加肾损伤风险",
                "mechanism": "NSAIDs抑制前列腺素合成，导致血管收缩和水钠潴留",
                "recommendation": "🚫 不建议长期联用，如必须联用需密切监测血压和肾功能",
                "evidence_level": "A"
            },
            {
                "drug_a": "布洛芬", "drug_b": "二甲双胍",
                "severity": "moderate",
                "description": "布洛芬可能增加二甲双胍的乳酸酸中毒风险",
                "mechanism": "NSAIDs影响肾功能，可能减少二甲双胍排泄",
                "recommendation": "短期联用需监测肾功能，长期联用需谨慎",
                "evidence_level": "B"
            },
            {
                "drug_a": "奥美拉唑", "drug_b": "氨氯地平",
                "severity": "moderate",
                "description": "奥美拉唑可能增加氨氯地平的血药浓度",
                "mechanism": "奥美拉唑抑制CYP2C19和CYP3A4，影响氨氯地平代谢",
                "recommendation": "联用时注意监测血压，可能需要调整氨氯地平剂量",
                "evidence_level": "B"
            },
            {
                "drug_a": "奥美拉唑", "drug_b": "阿莫西林",
                "severity": "minor",
                "description": "奥美拉唑可提高胃内pH值，可能轻微影响阿莫西林吸收",
                "mechanism": "胃酸减少影响β-内酰胺类抗生素吸收",
                "recommendation": "一般可联用，实际上三联疗法中常联用",
                "evidence_level": "C"
            },
            {
                "drug_a": "二甲双胍", "drug_b": "氨氯地平",
                "severity": "minor",
                "description": "一般无显著相互作用",
                "mechanism": "两者代谢途径不同",
                "recommendation": "可安全联用",
                "evidence_level": "A"
            },
            {
                "drug_a": "利鲁唑", "drug_b": "奥美拉唑",
                "severity": "major",
                "description": "奥美拉唑可能显著增加利鲁唑的血药浓度，增加肝毒性风险",
                "mechanism": "CYP1A2酶抑制，减少利鲁唑代谢",
                "recommendation": "🚫 应避免联用，如必须联用需大幅减少利鲁唑剂量并监测肝功能",
                "evidence_level": "A"
            },
            {
                "drug_a": "环磷酰胺", "drug_b": "阿莫西林",
                "severity": "moderate",
                "description": "阿莫西林可能增加环磷酰胺的骨髓抑制风险",
                "mechanism": "抗生素导致的肠道菌群改变影响免疫抑制",
                "recommendation": "联用期间需加强血常规监测",
                "evidence_level": "B"
            },
            {
                "drug_a": "羟氯喹", "drug_b": "奥美拉唑",
                "severity": "minor",
                "description": "奥美拉唑可能轻微影响羟氯喹吸收",
                "mechanism": "胃酸减少影响弱碱性药物吸收",
                "recommendation": "建议间隔2小时以上服用",
                "evidence_level": "C"
            },
            {
                "drug_a": "左旋多巴", "drug_b": "布洛芬",
                "severity": "moderate",
                "description": "布洛芬可能增加左旋多巴的血药浓度",
                "mechanism": "NSAIDs影响肾功能从而减少左旋多巴排泄",
                "recommendation": "联用时注意观察左旋多巴的不良反应，必要时调整剂量",
                "evidence_level": "B"
            },
            {
                "drug_a": "干扰素β", "drug_b": "布洛芬",
                "severity": "minor",
                "description": "布洛芬可用于缓解干扰素β的流感样症状",
                "mechanism": "解热镇痛作用",
                "recommendation": "可联用，布洛芬有助于减轻干扰素不良反应",
                "evidence_level": "A"
            },
            {
                "drug_a": "阿司匹林", "drug_b": "布洛芬",
                "severity": "major",
                "description": "布洛芬可削弱阿司匹林的心血管保护作用，并增加胃肠道出血风险",
                "mechanism": "竞争性结合COX-1，阻止阿司匹林不可逆抑制血小板",
                "recommendation": "🚫 不建议联用，如需镇痛可选用对乙酰氨基酚替代布洛芬",
                "evidence_level": "A"
            },
            {
                "drug_a": "阿司匹林", "drug_b": "氨氯地平",
                "severity": "minor",
                "description": "一般无显著相互作用",
                "mechanism": "代谢途径不同",
                "recommendation": "可联用",
                "evidence_level": "A"
            }
        ]

    def _load_aliases(self) -> Dict[str, str]:
        return {
            "阿司匹林": "阿司匹林",
            "aspirin": "阿司匹林",
            "布洛芬": "布洛芬",
            "ibuprofen": "布洛芬",
            "阿莫西林": "阿莫西林",
            "amoxicillin": "阿莫西林"
        }

    def resolve_name(self, name: str) -> str:
        return self.medicine_aliases.get(name, name)

    def check_interaction(self, drug_names: List[str]) -> Dict[str, Any]:
        resolved = [self.resolve_name(n) for n in drug_names]
        found_interactions = []
        checked_pairs = set()
        
        for i, drug_a in enumerate(resolved):
            for j, drug_b in enumerate(resolved):
                if i >= j:
                    continue
                pair_key = f"{drug_a}|{drug_b}"
                if pair_key in checked_pairs:
                    continue
                checked_pairs.add(pair_key)
                
                interaction = self._find_interaction(drug_a, drug_b)
                if interaction:
                    found_interactions.append(interaction)
        
        overall_risk = self._assess_overall_risk(found_interactions)
        
        return {
            "drugs": drug_names,
            "resolved_drugs": resolved,
            "interactions": found_interactions,
            "interaction_count": len(found_interactions),
            "overall_risk": overall_risk,
            "summary": self._generate_summary(found_interactions, overall_risk),
            "recommendation": self._generate_recommendation(found_interactions, overall_risk)
        }

    def _find_interaction(self, drug_a: str, drug_b: str) -> Dict:
        for interaction in self.interactions:
            if ((interaction["drug_a"] == drug_a and interaction["drug_b"] == drug_b) or
                (interaction["drug_a"] == drug_b and interaction["drug_b"] == drug_a)):
                return interaction
        return None

    def _assess_overall_risk(self, interactions: List[Dict]) -> Dict:
        if not interactions:
            return {"level": "safe", "score": 0, "description": "未发现已知药物相互作用"}
        
        severity_scores = {"minor": 1, "moderate": 3, "major": 5}
        total_score = sum(severity_scores.get(i["severity"], 1) for i in interactions)
        max_severity = max(interactions, key=lambda x: severity_scores.get(x["severity"], 0))
        
        if total_score >= 5 or max_severity["severity"] == "major":
            level = "high"
            description = "存在严重药物相互作用，建议避免联用或密切监测"
        elif total_score >= 3:
            level = "moderate"
            description = "存在中等程度药物相互作用，需注意监测"
        else:
            level = "low"
            description = "存在轻微药物相互作用，一般可安全联用"
        
        return {
            "level": level,
            "score": total_score,
            "description": description,
            "max_severity": max_severity["severity"]
        }

    def _generate_summary(self, interactions: List[Dict], risk: Dict) -> str:
        if not interactions:
            return "✅ 未发现已知的药物相互作用，联合用药相对安全。"
        
        severity_emoji = {"minor": "ℹ️", "moderate": "⚠️", "major": "🚫"}
        
        summary = f"联合用药风险评估：{risk['level'].upper()}\n\n"
        summary += f"共发现 {len(interactions)} 项药物相互作用：\n\n"
        
        for i, inter in enumerate(interactions, 1):
            emoji = severity_emoji.get(inter["severity"], "ℹ️")
            summary += f"{i}. {emoji} {inter['drug_a']} + {inter['drug_b']}\n"
            summary += f"   严重程度：{inter['severity'].upper()}\n"
            summary += f"   说明：{inter['description']}\n"
            summary += f"   建议：{inter['recommendation']}\n"
            summary += f"   证据等级：{inter['evidence_level']}\n\n"
        
        return summary

    def _generate_recommendation(self, interactions: List[Dict], risk: Dict) -> str:
        if not interactions:
            return "当前药物组合未见明显相互作用，可按医嘱使用。"
        
        if risk["level"] == "high":
            return "🚨 存在严重药物相互作用风险！强烈建议咨询医生或药师调整用药方案，不要自行联合使用这些药物。"
        elif risk["level"] == "moderate":
            return "⚠️ 存在中等程度相互作用，建议在医生指导下使用，注意监测相关指标。"
        else:
            return "ℹ️ 存在轻微相互作用，一般可安全联用，如有不适请及时咨询医生。"
