import re
from typing import List, Dict, Any, Tuple
from collections import defaultdict


class DisputeFocusAnalyzer:
    DISPUTE_PATTERNS = {
        "事实争议": [
            {
                "keywords": ["质量", "瑕疵", "不合格", "不符合约定", "存在缺陷"],
                "focus": "标的物质量是否符合约定",
                "subcategory": "质量问题",
            },
            {
                "keywords": ["未交付", "未履行", "未供货", "未支付", "未偿还"],
                "focus": "义务是否已实际履行",
                "subcategory": "履行争议",
            },
            {
                "keywords": ["金额不符", "数额有误", "计算错误", "多算", "少算"],
                "focus": "金额/数额是否准确",
                "subcategory": "金额争议",
            },
            {
                "keywords": ["赌债", "非法债务", "不受法律保护", "高利贷"],
                "focus": "债务是否合法有效",
                "subcategory": "债务合法性",
            },
            {
                "keywords": ["口头约定", "未签订", "没有书面", "口头协议"],
                "focus": "合同/协议是否成立",
                "subcategory": "合同成立争议",
            },
            {
                "keywords": ["并非借款", "不是欠款", "系投资", "系赠与", "系合伙"],
                "focus": "法律关系性质认定",
                "subcategory": "法律关系性质",
            },
        ],
        "法律适用争议": [
            {
                "keywords": ["利率", "利息过高", "高利贷", "超过法定"],
                "focus": "利率/利息是否符合法定标准",
                "subcategory": "利率合法性",
            },
            {
                "keywords": ["违约金过高", "违约金不合理", "违约金调整"],
                "focus": "违约金是否过高需调整",
                "subcategory": "违约金合理性",
            },
            {
                "keywords": ["诉讼时效", "超过时效", "时效届满"],
                "focus": "是否超过诉讼时效",
                "subcategory": "诉讼时效",
            },
            {
                "keywords": ["不可抗力", "情势变更", "疫情影响"],
                "focus": "是否存在不可抗力/情势变更",
                "subcategory": "不可抗力认定",
            },
            {
                "keywords": ["解除合同", "合同无效", "撤销合同"],
                "focus": "合同效力及解除条件是否成就",
                "subcategory": "合同效力",
            },
            {
                "keywords": ["违法解除", "合法解除", "解除程序"],
                "focus": "解除行为是否合法",
                "subcategory": "解除合法性",
            },
        ],
        "程序争议": [
            {
                "keywords": ["管辖权", "管辖异议", "移送管辖"],
                "focus": "法院管辖权是否适当",
                "subcategory": "管辖权异议",
            },
            {
                "keywords": ["仲裁", "仲裁前置", "劳动仲裁"],
                "focus": "是否经过仲裁前置程序",
                "subcategory": "仲裁前置",
            },
            {
                "keywords": ["举证期限", "证据逾期", "新证据"],
                "focus": "举证期限及证据效力",
                "subcategory": "举证程序",
            },
            {
                "keywords": ["鉴定", "评估", "审计"],
                "focus": "是否需要启动鉴定/评估程序",
                "subcategory": "鉴定程序",
            },
        ],
        "证据争议": [
            {
                "keywords": ["无证据", "证据不足", "举证不能"],
                "focus": "举证责任分配及证据充分性",
                "subcategory": "举证责任",
            },
            {
                "keywords": ["证据真实性", "伪造", "变造", "虚假"],
                "focus": "证据真实性存疑",
                "subcategory": "证据真实性",
            },
            {
                "keywords": ["证据关联性", "与本案无关", "不具有关联性"],
                "focus": "证据与待证事实的关联性",
                "subcategory": "证据关联性",
            },
        ],
    }

    PLAINTIFF_STANCE_PATTERNS = [
        (r'原告[^\n]*?诉称[，：:]\s*([^。；;\n]+)', "原告诉称"),
        (r'请求判令[，：:]\s*([^。；;\n]+)', "原告诉讼请求"),
        (r'请求[：:]\s*([^。；;\n]+)', "原告请求"),
    ]

    DEFENDANT_STANCE_PATTERNS = [
        (r'被告[^\n]*?辩称[，：:]\s*([^。；;\n]+)', "被告辩称"),
        (r'被告[^\n]*?答辩[，：:]\s*([^。；;\n]+)', "被告答辩"),
        (r'不同意[，：:]?\s*([^。；;\n]+)', "被告反对意见"),
    ]

    def analyze(self, text: str, query_analysis: Dict[str, Any] = None) -> Dict[str, Any]:
        dispute_foci = self._identify_dispute_foci(text)

        plaintiff_stance = self._extract_stance(text, self.PLAINTIFF_STANCE_PATTERNS)
        defendant_stance = self._extract_stance(text, self.DEFENDANT_STANCE_PATTERNS)

        core_dispute = self._determine_core_dispute(dispute_foci, plaintiff_stance, defendant_stance)

        dispute_chain = self._build_dispute_chain(dispute_foci, core_dispute)

        resolution_suggestions = self._suggest_resolution(dispute_foci, core_dispute)

        return {
            "dispute_foci": dispute_foci,
            "plaintiff_stance": plaintiff_stance,
            "defendant_stance": defendant_stance,
            "core_dispute": core_dispute,
            "dispute_chain": dispute_chain,
            "resolution_suggestions": resolution_suggestions,
        }

    def _identify_dispute_foci(self, text: str) -> List[Dict[str, Any]]:
        foci = []

        for category, patterns in self.DISPUTE_PATTERNS.items():
            for pattern in patterns:
                matched_keywords = [kw for kw in pattern["keywords"] if kw in text]
                if matched_keywords:
                    foci.append({
                        "category": category,
                        "subcategory": pattern["subcategory"],
                        "focus": pattern["focus"],
                        "matched_keywords": matched_keywords,
                        "importance": self._assess_importance(category, matched_keywords, text),
                    })

        foci.sort(key=lambda x: x["importance"], reverse=True)
        return foci

    def _assess_importance(self, category: str, keywords: List[str], text: str) -> float:
        importance_map = {
            "事实争议": 0.85,
            "法律适用争议": 0.90,
            "程序争议": 0.60,
            "证据争议": 0.80,
        }
        base = importance_map.get(category, 0.5)

        keyword_boost = min(len(keywords) * 0.05, 0.15)

        conflict_indicators = ["辩称", "异议", "不同意", "反驳", "否认"]
        conflict_count = sum(1 for ind in conflict_indicators if ind in text)
        conflict_boost = min(conflict_count * 0.03, 0.10)

        return min(base + keyword_boost + conflict_boost, 1.0)

    def _extract_stance(self, text: str, patterns: List[Tuple]) -> List[Dict[str, str]]:
        stances = []
        for pattern, source in patterns:
            matches = re.findall(pattern, text)
            for match in matches:
                if match and len(match.strip()) > 3:
                    stances.append({
                        "source": source,
                        "content": match.strip()[:200],
                    })
        return stances

    def _determine_core_dispute(
        self,
        foci: List[Dict[str, Any]],
        plaintiff_stance: List[Dict[str, str]],
        defendant_stance: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        if not foci:
            return {
                "core_issue": "事实认定",
                "description": "案件核心争议点需要进一步分析",
                "dispute_type": "待定",
                "intensity": "中",
            }

        top_focus = foci[0]
        core_issue = top_focus["focus"]
        dispute_type = top_focus["category"]

        plaintiff_points = [s["content"] for s in plaintiff_stance]
        defendant_points = [s["content"] for s in defendant_stance]

        if plaintiff_points and defendant_points:
            intensity = "高"
        elif plaintiff_points or defendant_points:
            intensity = "中"
        else:
            intensity = "低"

        description = core_issue
        if plaintiff_points:
            description += f"。原告主张：{plaintiff_points[0][:60]}"
        if defendant_points:
            description += f"。被告主张：{defendant_points[0][:60]}"

        return {
            "core_issue": core_issue,
            "description": description,
            "dispute_type": dispute_type,
            "intensity": intensity,
        }

    def _build_dispute_chain(
        self,
        foci: List[Dict[str, Any]],
        core_dispute: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        chain = []

        factual = [f for f in foci if f["category"] == "事实争议"]
        legal = [f for f in foci if f["category"] == "法律适用争议"]
        evidential = [f for f in foci if f["category"] == "证据争议"]
        procedural = [f for f in foci if f["category"] == "程序争议"]

        if evidential:
            chain.append({
                "stage": "第一层：证据认定",
                "foci": [{"focus": f["focus"], "subcategory": f["subcategory"]} for f in evidential[:2]],
                "description": "首先需确定证据的效力与可采性",
            })

        if factual:
            chain.append({
                "stage": "第二层：事实认定",
                "foci": [{"focus": f["focus"], "subcategory": f["subcategory"]} for f in factual[:3]],
                "description": "基于有效证据认定案件基本事实",
            })

        if legal:
            chain.append({
                "stage": "第三层：法律适用",
                "foci": [{"focus": f["focus"], "subcategory": f["subcategory"]} for f in legal[:3]],
                "description": "在事实认定的基础上确定法律适用",
            })

        if procedural:
            chain.append({
                "stage": "程序问题",
                "foci": [{"focus": f["focus"], "subcategory": f["subcategory"]} for f in procedural[:2]],
                "description": "需先行解决的程序性事项",
            })

        return chain

    def _suggest_resolution(
        self,
        foci: List[Dict[str, Any]],
        core_dispute: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        suggestions = []

        for focus in foci[:5]:
            suggestion = self._get_focus_suggestion(focus)
            if suggestion:
                suggestions.append(suggestion)

        if core_dispute.get("intensity") == "高":
            suggestions.append({
                "type": "调解建议",
                "description": "双方争议较大，建议先行调解，就部分无争议事项达成一致",
                "priority": "高",
            })

        suggestions.append({
            "type": "证据补强",
            "description": "建议补充收集和固定关键证据，特别是书面证据和转账凭证",
            "priority": "中",
        })

        return suggestions

    def _get_focus_suggestion(self, focus: Dict[str, Any]) -> Dict[str, Any]:
        subcategory_suggestions = {
            "质量问题": {"type": "鉴定建议", "description": "建议对标的物质量申请专业鉴定", "priority": "高"},
            "履行争议": {"type": "举证建议", "description": "建议提供交付凭证或验收记录等履行证据", "priority": "高"},
            "金额争议": {"type": "审计建议", "description": "建议对争议金额进行专业核算或审计", "priority": "中"},
            "利率合法性": {"type": "法律分析", "description": "需核验约定利率是否超过LPR四倍（约14.6%年利率）", "priority": "高"},
            "违约金合理性": {"type": "损失举证", "description": "建议就实际损失进行举证，以便法院判断违约金是否过高", "priority": "中"},
            "诉讼时效": {"type": "时效审查", "description": "需审查是否存在时效中断、中止事由", "priority": "高"},
            "不可抗力认定": {"type": "事实查明", "description": "需查明不可抗力事件是否确实影响合同履行", "priority": "中"},
            "合同效力": {"type": "法律审查", "description": "需审查合同是否存在无效事由", "priority": "高"},
            "解除合法性": {"type": "程序审查", "description": "需审查解除是否符合法定条件和程序", "priority": "高"},
            "举证责任": {"type": "证据补强", "description": "建议补充证据，强化举证能力", "priority": "高"},
            "债务合法性": {"type": "法律审查", "description": "需审查债务形成是否合法，排除非法债务", "priority": "高"},
            "合同成立争议": {"type": "证据补强", "description": "建议收集微信记录、短信、邮件等辅助证明合同成立", "priority": "高"},
            "仲裁前置": {"type": "程序建议", "description": "需先经过劳动仲裁程序", "priority": "高"},
        }

        suggestion_data = subcategory_suggestions.get(focus["subcategory"])
        if suggestion_data:
            return {
                "type": suggestion_data["type"],
                "description": f"【{focus['focus']}】{suggestion_data['description']}",
                "priority": suggestion_data["priority"],
            }
        return None
