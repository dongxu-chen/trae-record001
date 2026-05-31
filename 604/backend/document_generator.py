import re
from typing import List, Dict, Any, Optional
from datetime import datetime


class DocumentGenerator:
    TEMPLATES = {
        "民事起诉状": {
            "sections": ["当事人信息", "诉讼请求", "事实与理由", "证据清单", "此致"],
            "structure": [
                "header",
                "parties",
                "claims",
                "facts_and_reasons",
                "evidence_list",
                "footer",
            ],
        },
        "民事答辩状": {
            "sections": ["当事人信息", "答辩意见", "事实与理由", "证据清单", "此致"],
            "structure": [
                "header",
                "parties",
                "defense_opinion",
                "facts_and_reasons",
                "evidence_list",
                "footer",
            ],
        },
        "代理词": {
            "sections": ["案件概述", "代理意见", "法律分析", "结论"],
            "structure": [
                "header",
                "case_overview",
                "representation_opinion",
                "legal_analysis",
                "conclusion",
            ],
        },
    }

    def generate(
        self,
        doc_type: str,
        query_analysis: Dict[str, Any],
        similar_cases: List[Dict[str, Any]],
        recommended_laws: List[Dict[str, str]],
        dispute_analysis: Dict[str, Any] = None,
        judgment_prediction: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        template = self.TEMPLATES.get(doc_type)
        if not template:
            return {"success": False, "error": f"不支持的文书类型: {doc_type}"}

        entities = query_analysis.get("legal_entities", {})
        key_points = query_analysis.get("key_points", [])
        case_type = query_analysis.get("case_type", "")
        summary = query_analysis.get("summary", "")

        plaintiff = self._get_entity(entities, "原告", "原告XXX")
        defendant = self._get_entity(entities, "被告", "被告XXX")
        amounts = entities.get("金额", [])
        evidence = entities.get("证据", [])
        dates = entities.get("日期", [])

        if doc_type == "民事起诉状":
            content = self._generate_complaint(
                plaintiff, defendant, amounts, evidence, dates,
                key_points, case_type, summary, recommended_laws,
                dispute_analysis, judgment_prediction, similar_cases,
            )
        elif doc_type == "民事答辩状":
            content = self._generate_defense(
                plaintiff, defendant, amounts, evidence, dates,
                key_points, case_type, summary, recommended_laws,
                dispute_analysis, similar_cases,
            )
        elif doc_type == "代理词":
            content = self._generate_representation(
                plaintiff, defendant, key_points, case_type, summary,
                recommended_laws, dispute_analysis, judgment_prediction,
                similar_cases,
            )
        else:
            content = "暂不支持该文书类型"

        return {
            "success": True,
            "doc_type": doc_type,
            "content": content,
            "metadata": {
                "plaintiff": plaintiff,
                "defendant": defendant,
                "case_type": case_type,
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "reference_cases": [c.get("case_id", "") for c in similar_cases[:3]],
                "reference_laws": [l.get("law_id", "") for l in recommended_laws[:3]],
                "word_count": len(content),
            },
        }

    def _get_entity(self, entities: Dict[str, List[str]], key: str, default: str) -> str:
        values = entities.get(key, [])
        return values[0] if values else default

    def _generate_complaint(
        self, plaintiff, defendant, amounts, evidence, dates,
        key_points, case_type, summary, recommended_laws,
        dispute_analysis, judgment_prediction, similar_cases,
    ) -> str:
        sections = []

        sections.append("                    民事起诉状\n")

        sections.append("一、当事人信息\n")
        sections.append(f"  原告：{plaintiff}")
        sections.append(f"  被告：{defendant}\n")

        sections.append("二、诉讼请求\n")
        claims = self._generate_claims(plaintiff, defendant, amounts, case_type, dispute_analysis)
        for i, claim in enumerate(claims, 1):
            sections.append(f"  {i}、{claim}")
        sections.append(f"  {len(claims) + 1}、被告承担本案全部诉讼费用。\n")

        sections.append("三、事实与理由\n")
        facts = self._generate_facts(plaintiff, defendant, amounts, dates, key_points, case_type)
        sections.append(facts)
        sections.append("")

        if recommended_laws:
            sections.append("  法律依据：")
            for law in recommended_laws[:3]:
                sections.append(f"  根据《{law.get('law_id', '')}》规定：{law.get('content', '')[:80]}")
            sections.append("")

        if similar_cases:
            sections.append("  参考案例：")
            for case in similar_cases[:2]:
                sections.append(f"  - {case.get('case_title', '')}（{case.get('court', '')}，{case.get('judgment_date', '')}）")
            sections.append("")

        sections.append("  综上所述，被告的行为已侵害原告合法权益，特依照相关法律规定，")
        sections.append("  向贵院提起诉讼，恳请依法裁判。\n")

        sections.append("四、证据清单\n")
        for i, ev in enumerate(evidence, 1):
            sections.append(f"  {i}、{ev}")
        if not evidence:
            sections.append("  （待补充）")
        sections.append("")

        sections.append("五、此致\n")
        court = self._infer_court(case_type)
        sections.append(f"  {court}\n")

        sections.append(f"                  起诉人：{plaintiff}")
        sections.append(f"                  {datetime.now().strftime('%Y年%m月%d日')}")

        return "\n".join(sections)

    def _generate_defense(
        self, plaintiff, defendant, amounts, evidence, dates,
        key_points, case_type, summary, recommended_laws,
        dispute_analysis, similar_cases,
    ) -> str:
        sections = []

        sections.append("                    民事答辩状\n")

        sections.append("一、当事人信息\n")
        sections.append(f"  答辩人（被告）：{defendant}")
        sections.append(f"  被答辩人（原告）：{plaintiff}\n")

        sections.append("二、答辩意见\n")
        defenses = self._generate_defenses(plaintiff, defendant, amounts, case_type, dispute_analysis)
        for i, defense in enumerate(defenses, 1):
            sections.append(f"  {i}、{defense}")
        sections.append("")

        sections.append("三、事实与理由\n")
        sections.append(f"  答辩人认为：")
        if dispute_analysis and dispute_analysis.get("defendant_stance"):
            for stance in dispute_analysis["defendant_stance"][:3]:
                sections.append(f"  {stance.get('content', '')}")
        else:
            sections.append(f"  关于原告所诉事实，答辩人认为部分与客观事实不符。")
            if amounts:
                sections.append(f"  关于原告主张的金额{', '.join(amounts[:2])}，答辩人对其计算方式持有异议。")
        sections.append("")

        if recommended_laws:
            sections.append("  法律依据：")
            for law in recommended_laws[:2]:
                sections.append(f"  根据《{law.get('law_id', '')}》规定：{law.get('content', '')[:80]}")
            sections.append("")

        sections.append("  综上所述，恳请法院依法驳回原告不合理的诉讼请求。\n")

        sections.append("四、证据清单\n")
        for i, ev in enumerate(evidence, 1):
            sections.append(f"  {i}、{ev}")
        if not evidence:
            sections.append("  （待补充）")
        sections.append("")

        sections.append("五、此致\n")
        court = self._infer_court(case_type)
        sections.append(f"  {court}\n")

        sections.append(f"                  答辩人：{defendant}")
        sections.append(f"                  {datetime.now().strftime('%Y年%m月%d日')}")

        return "\n".join(sections)

    def _generate_representation(
        self, plaintiff, defendant, key_points, case_type, summary,
        recommended_laws, dispute_analysis, judgment_prediction,
        similar_cases,
    ) -> str:
        sections = []

        sections.append("                    代理词\n")

        sections.append("一、案件概述\n")
        sections.append(f"  本案系{plaintiff}与{defendant}之间的{case_type}纠纷。")
        sections.append(f"  {summary}\n")

        sections.append("二、代理意见\n")
        if dispute_analysis:
            core = dispute_analysis.get("core_dispute", {})
            sections.append(f"  本案核心争议焦点：{core.get('core_issue', '待认定')}。")

            foci = dispute_analysis.get("dispute_foci", [])
            if foci:
                sections.append("  具体争议焦点分析如下：")
                for i, focus in enumerate(foci[:4], 1):
                    sections.append(f"  {i}、{focus.get('focus', '')}（{focus.get('category', '')}）")
        sections.append("")

        sections.append("三、法律分析\n")
        sections.append(f"  关于本案的法律适用：")
        if recommended_laws:
            for law in recommended_laws[:3]:
                sections.append(f"  《{law.get('law_id', '')}》：{law.get('content', '')[:100]}")
        sections.append("")

        if judgment_prediction:
            sections.append("四、判决预测分析\n")
            outcome = judgment_prediction.get("predicted_outcome", "")
            confidence = judgment_prediction.get("confidence", 0)
            sections.append(f"  基于相似案例统计分析，判决预测结果为：{outcome}（置信度：{confidence:.1%}）。")
            reasoning = judgment_prediction.get("reasoning", [])
            for r in reasoning[:3]:
                sections.append(f"  {r}")
        sections.append("")

        sections.append("五、结论\n")
        sections.append("  综上，代理人认为，原告的诉讼请求具有事实和法律依据，")
        sections.append("  恳请法庭依法支持原告的合理诉求。\n")

        sections.append(f"                  代理人：XXX")
        sections.append(f"                  {datetime.now().strftime('%Y年%m月%d日')}")

        return "\n".join(sections)

    def _generate_claims(self, plaintiff, defendant, amounts, case_type, dispute_analysis) -> List[str]:
        claims = []

        if "借贷" in case_type:
            if amounts:
                claims.append(f"判令被告{defendant}偿还原告{plaintiff}借款本金{amounts[0]}；")
                if len(amounts) > 1:
                    claims.append(f"判令被告支付利息（以{amounts[-1]}为基数，按法定利率计算至实际清偿之日止）；")
                else:
                    claims.append("判令被告支付逾期利息（按法定利率计算至实际清偿之日止）；")
            else:
                claims.append(f"判令被告偿还借款本金及利息；")
        elif "合同" in case_type:
            if amounts:
                claims.append(f"判令被告{defendant}支付{plaintiff}款项{amounts[0]}；")
                claims.append("判令被告支付违约金；")
            else:
                claims.append("判令被告继续履行合同义务；")
                claims.append("判令被告承担违约责任；")
        elif "劳动" in case_type:
            if amounts:
                claims.append(f"判令被告支付拖欠工资{amounts[0] if len(amounts) > 0 else ''}；")
                if len(amounts) > 1:
                    claims.append(f"判令被告支付经济赔偿金{amounts[-1]}；")
            else:
                claims.append("判令被告支付拖欠工资及经济补偿金；")
        else:
            if amounts:
                claims.append(f"判令被告向原告支付{amounts[0]}；")
            else:
                claims.append("判令被告承担相应法律责任；")

        if dispute_analysis:
            foci = dispute_analysis.get("dispute_foci", [])
            for focus in foci:
                if "解除" in focus.get("focus", ""):
                    claims.append("判令解除双方签订的相关合同/协议；")
                    break

        return claims

    def _generate_defenses(self, plaintiff, defendant, amounts, case_type, dispute_analysis) -> List[str]:
        defenses = []

        if dispute_analysis:
            foci = dispute_analysis.get("dispute_foci", [])
            for focus in foci[:3]:
                sub = focus.get("subcategory", "")
                if sub == "质量问题":
                    defenses.append("原告提供的标的物存在质量问题，被告有权拒付相应款项。")
                elif sub == "利率合法性":
                    defenses.append("原告主张的利率超过法定上限，超出部分不应得到支持。")
                elif sub == "诉讼时效":
                    defenses.append("原告的诉讼请求已超过诉讼时效，依法应予驳回。")
                elif sub == "不可抗力认定":
                    defenses.append("被告未履行义务系因不可抗力/情势变更，不应承担违约责任。")
                elif sub == "债务合法性":
                    defenses.append("涉案债务不具合法性，不受法律保护。")
                elif sub == "解除合法性":
                    defenses.append("被告解除合同符合法定条件，不应承担赔偿责任。")

        if not defenses:
            if amounts:
                defenses.append(f"对原告主张的金额{amounts[0]}不予认可，实际金额有误。")
            defenses.append("原告的部分诉讼请求缺乏事实和法律依据，请求法院依法驳回。")

        defenses.append("被告愿在合理范围内承担相应责任。")

        return defenses

    def _generate_facts(self, plaintiff, defendant, amounts, dates, key_points, case_type) -> str:
        lines = []
        date_str = dates[0] if dates else "XXXX年XX月XX日"

        if "借贷" in case_type:
            lines.append(f"  {date_str}，被告{defendant}因资金周转需要向原告{plaintiff}借款。")
            if amounts:
                lines.append(f"  原告于当日向被告交付借款{amounts[0]}。")
            lines.append(f"  双方约定了借款期限和利息。")
            lines.append(f"  借款到期后，经原告多次催讨，被告未按约定偿还借款本息。")
        elif "合同" in case_type:
            lines.append(f"  {date_str}，原被告双方签订相关合同/协议。")
            lines.append(f"  原告按照合同约定履行了己方义务。")
            if amounts:
                lines.append(f"  被告未按约定支付款项{amounts[0]}，已构成违约。")
            else:
                lines.append(f"  被告未按合同约定履行义务，已构成违约。")
        elif "劳动" in case_type:
            lines.append(f"  原告于{date_str}入职被告单位工作。")
            lines.append(f"  被告未依法支付劳动报酬，且违法解除劳动合同。")
            if amounts:
                lines.append(f"  被告拖欠工资及应支付赔偿金共计{amounts[-1] if len(amounts) > 1 else amounts[0]}。")
        else:
            if key_points:
                for kp in key_points[:4]:
                    lines.append(f"  {kp}。")
            else:
                lines.append(f"  原被告之间存在纠纷，被告的行为侵害了原告的合法权益。")

        return "\n".join(lines)

    def _infer_court(self, case_type: str) -> str:
        court_map = {
            "民间借贷纠纷": "XXX人民法院",
            "合同纠纷": "XXX人民法院",
            "买卖合同纠纷": "XXX人民法院",
            "租赁合同纠纷": "XXX人民法院",
            "劳动争议": "XXX人民法院",
            "交通事故责任纠纷": "XXX人民法院",
        }
        return court_map.get(case_type, "XXX人民法院")
