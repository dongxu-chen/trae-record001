import re
from typing import List, Dict, Set, Tuple
from collections import defaultdict

from app.models.schemas import (
    ResumeData,
    CompetitorAnalysis,
    TalentFlowRecord,
    CompetitorResponse,
)


class CompetitorAnalyzer:
    def __init__(self):
        self._company_keywords = self._init_company_keywords()
        self._company_stats: Dict[str, dict] = defaultdict(lambda: {
            "count": 0,
            "total_score": 0.0,
            "positions": defaultdict(int),
            "skills": defaultdict(int),
            "outflow": defaultdict(int),
            "durations": [],
        })
        self._flow_matrix: Dict[Tuple[str, str], dict] = defaultdict(lambda: {
            "count": 0,
            "skills": [],
            "durations": [],
        })

    def _init_company_keywords(self) -> Dict[str, List[str]]:
        return {
            "阿里巴巴": ["阿里", "alibaba", "淘宝", "天猫", "支付宝", "菜鸟", "饿了么"],
            "腾讯": ["腾讯", "tencent", "微信", "qq", "腾讯云", "wegame"],
            "字节跳动": ["字节", "字节跳动", "bytedance", "抖音", "tiktok", "头条"],
            "百度": ["百度", "baidu", "百度智能云", "爱奇艺"],
            "华为": ["华为", "huawei", "荣耀", "honor", "华为云"],
            "美团": ["美团", "meituan", "大众点评"],
            "京东": ["京东", "jd", "京东健康", "京东物流"],
            "拼多多": ["拼多多", "pdd", "拼夕夕"],
            "小米": ["小米", "xiaomi", "mi", "红米", "redmi"],
            "快手": ["快手", "kuaishou"],
            "网易": ["网易", "netease", "云音乐", "有道"],
            "滴滴": ["滴滴", "didi", "滴滴出行"],
            "微软": ["微软", "microsoft", "ms"],
            "谷歌": ["谷歌", "google", "gg"],
            "亚马逊": ["亚马逊", "amazon", "aws"],
            "苹果": ["苹果", "apple"],
            "IBM": ["ibm"],
            "甲骨文": ["甲骨文", "oracle"],
            "SAP": ["sap"],
        }

    def add_candidate(
        self,
        resume: ResumeData,
        match_score: float = 0.0,
        target_company: str = "本公司",
    ):
        companies = self._extract_companies(resume)
        if not companies:
            return

        flow_path = self._build_flow_path(resume, target_company)
        for i in range(len(flow_path) - 1):
            from_co = flow_path[i]
            to_co = flow_path[i + 1]
            if from_co and to_co and from_co != to_co:
                key = (from_co, to_co)
                self._flow_matrix[key]["count"] += 1
                self._flow_matrix[key]["skills"].extend(resume.skills)
                if i == len(flow_path) - 2:
                    self._flow_matrix[key]["durations"].append(self._get_last_duration(resume))

        for company in companies:
            stats = self._company_stats[company]
            stats["count"] += 1
            stats["total_score"] += match_score

            last_exp = resume.work_experience[0] if resume.work_experience else {}
            position = last_exp.get("position", "")
            if position:
                stats["positions"][position] += 1

            for skill in resume.skills:
                stats["skills"][skill] += 1

            duration = self._get_last_duration(resume)
            if duration:
                stats["durations"].append(duration)

            if len(flow_path) > 1:
                next_idx = flow_path.index(company) + 1
                if next_idx < len(flow_path):
                    next_company = flow_path[next_idx]
                    if next_company and next_company != company:
                        stats["outflow"][next_company] += 1

    def _extract_companies(self, resume: ResumeData) -> List[str]:
        companies = []
        seen = set()

        for exp in resume.work_experience:
            company_name = exp.get("company", "")
            if not company_name:
                continue

            normalized = self._normalize_company_name(company_name)
            if normalized and normalized not in seen:
                companies.append(normalized)
                seen.add(normalized)

        return companies

    def _normalize_company_name(self, name: str) -> str:
        name_lower = name.strip().lower()

        for standard_name, keywords in self._company_keywords.items():
            for kw in keywords:
                if kw.lower() in name_lower:
                    return standard_name

        clean_name = re.sub(r"(科技|信息技术|网络|软件|集团|股份|有限公司|公司|控股)$", "", name.strip())
        clean_name = re.sub(r"^[A-Za-z]+\s*", "", clean_name)
        if len(clean_name) >= 2:
            return clean_name[:15]

        return name.strip()[:15] if name.strip() else ""

    def _build_flow_path(self, resume: ResumeData, target_company: str) -> List[str]:
        path = []
        for exp in reversed(resume.work_experience):
            company = exp.get("company", "")
            if company:
                normalized = self._normalize_company_name(company)
                if normalized:
                    path.append(normalized)
        path.append(target_company)
        return path

    def _get_last_duration(self, resume: ResumeData) -> float:
        if not resume.work_experience:
            return 0.0

        last_exp = resume.work_experience[0]
        start = last_exp.get("start_date", "")
        end = last_exp.get("end_date", "至今")

        try:
            start_year = int(re.search(r"\d{4}", start).group()) if re.search(r"\d{4}", start) else 2020
            if end in ("至今", "现在", "present", ""):
                end_year = 2026
            else:
                end_year = int(re.search(r"\d{4}", end).group()) if re.search(r"\d{4}", end) else 2020
            return max(0.0, end_year - start_year)
        except Exception:
            return 0.0

    def analyze(
        self,
        target_company: str = "本公司",
        top_n: int = 10,
    ) -> CompetitorResponse:
        competitor_list = []
        for company, stats in self._company_stats.items():
            if company == target_company or stats["count"] == 0:
                continue

            avg_score = stats["total_score"] / stats["count"] if stats["count"] > 0 else 0

            top_positions = sorted(
                stats["positions"].items(), key=lambda x: x[1], reverse=True
            )[:5]

            top_skills = sorted(
                stats["skills"].items(), key=lambda x: x[1], reverse=True
            )[:8]

            outflow = sorted(
                stats["outflow"].items(), key=lambda x: x[1], reverse=True
            )[:5]

            flow_score = stats["count"] * (1 + avg_score)

            competitor_list.append(CompetitorAnalysis(
                company_name=company,
                candidate_count=stats["count"],
                avg_match_score=round(avg_score, 4),
                common_positions=[p[0] for p in top_positions],
                common_skills=[s[0] for s in top_skills],
                outflow_direction=[{"company": c, "count": cnt} for c, cnt in outflow],
                talent_flow_score=round(flow_score, 2),
            ))

        competitor_list.sort(key=lambda x: x.candidate_count, reverse=True)
        top_competitors = competitor_list[:top_n]

        talent_flow = []
        for (from_co, to_co), data in self._flow_matrix.items():
            if data["count"] >= 1:
                skill_counter = defaultdict(int)
                for skill in data["skills"]:
                    skill_counter[skill] += 1

                common_skills = sorted(
                    skill_counter.items(), key=lambda x: x[1], reverse=True
                )[:5]

                avg_duration = sum(data["durations"]) / len(data["durations"]) if data["durations"] else None

                talent_flow.append(TalentFlowRecord(
                    from_company=from_co,
                    to_company=to_co,
                    candidate_count=data["count"],
                    common_skills=[s[0] for s in common_skills],
                    avg_duration=round(avg_duration, 1) if avg_duration else None,
                ))

        talent_flow.sort(key=lambda x: x.candidate_count, reverse=True)

        top_sources = [c.company_name for c in top_competitors[:5]]

        insights = self._generate_insights(top_competitors, talent_flow)

        return CompetitorResponse(
            total_companies=len([c for c in self._company_stats.keys() if c != target_company]),
            competitor_analysis=top_competitors,
            talent_flow=talent_flow[:top_n],
            top_sources=top_sources,
            market_insights=insights,
        )

    def _generate_insights(
        self,
        competitors: List[CompetitorAnalysis],
        talent_flow: List[TalentFlowRecord],
    ) -> List[str]:
        insights = []

        if competitors:
            top_source = competitors[0]
            insights.append(
                f"主要人才来源：{top_source.company_name}（{top_source.candidate_count}人，平均匹配度{top_source.avg_match_score:.1%}）"
            )

        skill_demand = defaultdict(int)
        for comp in competitors:
            for skill in comp.common_skills[:3]:
                skill_demand[skill] += comp.candidate_count

        top_skills = sorted(skill_demand.items(), key=lambda x: x[1], reverse=True)[:3]
        if top_skills:
            skill_names = "、".join([s[0] for s in top_skills])
            insights.append(f"市场热门技能：{skill_names}")

        target_inflow = [f for f in talent_flow if f.to_company == "本公司"]
        if len(target_inflow) >= 3:
            insights.append("人才来源多元化，人才池健康")
        elif len(target_inflow) >= 1:
            insights.append("人才来源较为集中，建议拓宽招聘渠道")
        else:
            insights.append("人才流动数据不足，建议持续积累")

        avg_durations = [f.avg_duration for f in talent_flow if f.avg_duration]
        if avg_durations:
            avg_tenure = sum(avg_durations) / len(avg_durations)
            if avg_tenure < 2:
                insights.append(f"市场平均任职周期较短（{avg_tenure:.1f}年），建议关注人才稳定性")
            elif avg_tenure > 4:
                insights.append(f"市场人才稳定性较好（平均{avg_tenure:.1f}年）")

        total_candidates = sum(c.candidate_count for c in competitors)
        if total_candidates >= 10:
            insights.append(f"已积累{total_candidates}条竞对人才数据，分析可靠性较高")
        elif total_candidates >= 5:
            insights.append(f"已积累{total_candidates}条竞对人才数据，建议继续积累")
        else:
            insights.append("竞对数据量较少，建议持续积累以提高分析准确性")

        outflow_countries = defaultdict(int)
        for comp in competitors:
            for outflow in comp.outflow_direction[:2]:
                outflow_countries[outflow["company"]] += outflow["count"]

        top_outflow = sorted(outflow_countries.items(), key=lambda x: x[1], reverse=True)[:2]
        if top_outflow and top_outflow[0][1] >= 3:
            targets = "、".join([c[0] for c in top_outflow])
            insights.append(f"主要人才流失方向：{targets}，建议关注薪酬竞争力")

        return insights[:8]

    def get_company_list(self) -> List[str]:
        return list(self._company_stats.keys())

    def clear_data(self):
        self._company_stats.clear()
        self._flow_matrix.clear()

    def add_company_alias(self, standard_name: str, aliases: List[str]):
        if standard_name not in self._company_keywords:
            self._company_keywords[standard_name] = []
        self._company_keywords[standard_name].extend(aliases)