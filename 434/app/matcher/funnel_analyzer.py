from typing import List, Dict, Optional
from datetime import datetime

from app.models.schemas import (
    FunnelStage,
    FunnelAnalysisResponse,
)


DEFAULT_FUNNEL_STAGES = [
    {"code": "applied", "name": "简历投递", "detail": "候选人提交申请"},
    {"code": "screened", "name": "简历筛选", "detail": "通过初筛进入面试"},
    {"code": "phone_interview", "name": "电话面试", "detail": "HR电话沟通阶段"},
    {"code": "tech_interview", "name": "技术面试", "detail": "技术能力考察"},
    {"code": "final_interview", "name": "终面", "detail": "最终面试/高管面试"},
    {"code": "offer", "name": "Offer发放", "detail": "发出录用通知"},
    {"code": "hired", "name": "已入职", "detail": "候选人确认入职"},
]


class FunnelAnalyzer:
    def __init__(self):
        self._stage_data: Dict[str, Dict[str, dict]] = {}

    def add_candidate_stage(
        self,
        job_title: str,
        candidate_id: str,
        stage_code: str,
        stage_date: Optional[datetime] = None,
        duration_days: Optional[float] = None,
    ):
        if job_title not in self._stage_data:
            self._stage_data[job_title] = {}

        if candidate_id not in self._stage_data[job_title]:
            self._stage_data[job_title][candidate_id] = {
                "stages": [],
                "highest_stage": 0,
            }

        stage_index = self._get_stage_index(stage_code)
        if stage_index is not None:
            candidate_data = self._stage_data[job_title][candidate_id]
            candidate_data["stages"].append({
                "code": stage_code,
                "date": stage_date or datetime.now(),
                "duration": duration_days,
            })
            if stage_index > candidate_data["highest_stage"]:
                candidate_data["highest_stage"] = stage_index

    def _get_stage_index(self, stage_code: str) -> Optional[int]:
        for i, stage in enumerate(DEFAULT_FUNNEL_STAGES):
            if stage["code"] == stage_code:
                return i
        return None

    def analyze_funnel(
        self,
        job_title: str,
        custom_stages: Optional[List[dict]] = None,
    ) -> FunnelAnalysisResponse:
        stages_config = custom_stages or DEFAULT_FUNNEL_STAGES

        if job_title not in self._stage_data:
            return FunnelAnalysisResponse(
                job_title=job_title,
                total_applicants=0,
                stages=[],
                overall_conversion=0.0,
                bottlenecks=[],
                suggestions=["暂无招聘数据"],
            )

        candidates = self._stage_data[job_title]
        total_applicants = len(candidates)

        stage_counts = [0] * len(stages_config)
        stage_durations: Dict[str, List[float]] = {s["code"]: [] for s in stages_config}

        for candidate_data in candidates.values():
            highest = candidate_data["highest_stage"]
            for i in range(highest + 1):
                if i < len(stage_counts):
                    stage_counts[i] += 1

            for stage_entry in candidate_data["stages"]:
                code = stage_entry["code"]
                if stage_entry.get("duration") is not None and code in stage_durations:
                    stage_durations[code].append(stage_entry["duration"])

        funnel_stages = []
        for i, stage_config in enumerate(stages_config):
            count = stage_counts[i]
            prev_count = stage_counts[i - 1] if i > 0 else total_applicants

            conversion_rate = count / prev_count if prev_count > 0 else 0.0
            overall_rate = count / total_applicants if total_applicants > 0 else 0.0

            durations = stage_durations.get(stage_config["code"], [])
            avg_days = sum(durations) / len(durations) if durations else None

            funnel_stages.append(FunnelStage(
                stage_name=stage_config["name"],
                stage_code=stage_config["code"],
                candidate_count=count,
                conversion_rate=round(conversion_rate, 4) if i > 0 else None,
                overall_rate=round(overall_rate, 4),
                avg_days=round(avg_days, 1) if avg_days else None,
                stage_detail=stage_config.get("detail"),
            ))

        hired_count = stage_counts[-1] if stage_counts else 0
        overall_conversion = hired_count / total_applicants if total_applicants > 0 else 0.0

        total_days = []
        for candidate_data in candidates.values():
            if candidate_data["highest_stage"] >= len(stages_config) - 1:
                stages = candidate_data["stages"]
                if len(stages) >= 2:
                    first_date = stages[0]["date"]
                    last_date = stages[-1]["date"]
                    if first_date and last_date:
                        days = (last_date - first_date).days
                        total_days.append(days)

        avg_hiring_days = sum(total_days) / len(total_days) if total_days else None

        bottlenecks = self._identify_bottlenecks(funnel_stages, total_applicants)
        suggestions = self._generate_suggestions(funnel_stages, overall_conversion, avg_hiring_days)

        return FunnelAnalysisResponse(
            job_title=job_title,
            total_applicants=total_applicants,
            stages=funnel_stages,
            overall_conversion=round(overall_conversion, 4),
            avg_hiring_days=round(avg_hiring_days, 1) if avg_hiring_days else None,
            bottlenecks=bottlenecks,
            suggestions=suggestions,
        )

    def _identify_bottlenecks(
        self,
        stages: List[FunnelStage],
        total_applicants: int,
    ) -> List[str]:
        bottlenecks = []

        if total_applicants < 10:
            return bottlenecks

        benchmark_rates = {
            "screened": 0.30,
            "phone_interview": 0.60,
            "tech_interview": 0.50,
            "final_interview": 0.50,
            "offer": 0.70,
            "hired": 0.80,
        }

        for stage in stages:
            code = stage.stage_code
            rate = stage.conversion_rate

            if rate is None:
                continue

            benchmark = benchmark_rates.get(code, 0.5)
            if rate < benchmark * 0.7:
                bottlenecks.append(
                    f"{stage.stage_name}转化率偏低（实际{rate:.1%}，基准{benchmark:.0%}）"
                )

        if len(stages) >= 2:
            for i in range(1, len(stages)):
                if stages[i].avg_days and stages[i].avg_days > 7:
                    bottlenecks.append(
                        f"{stages[i].stage_name}周期过长（平均{stages[i].avg_days:.0f}天）"
                    )

        return bottlenecks[:5]

    def _generate_suggestions(
        self,
        stages: List[FunnelStage],
        overall_conversion: float,
        avg_hiring_days: Optional[float],
    ) -> List[str]:
        suggestions = []

        if not stages:
            return ["建议完善招聘流程数据记录"]

        first_stage = stages[0] if stages else None
        if first_stage and first_stage.candidate_count < 20:
            suggestions.append("简历投递量较少，建议拓宽招聘渠道")

        applied_stage = next((s for s in stages if s.stage_code == "applied"), None)
        screened_stage = next((s for s in stages if s.stage_code == "screened"), None)
        if applied_stage and screened_stage:
            ratio = screened_stage.candidate_count / applied_stage.candidate_count if applied_stage.candidate_count > 0 else 0
            if ratio < 0.2:
                suggestions.append("简历筛选通过率过低，建议优化JD描述或降低门槛")
            elif ratio > 0.5:
                suggestions.append("简历筛选通过率过高，建议加强筛选标准")

        offer_stage = next((s for s in stages if s.stage_code == "offer"), None)
        hired_stage = next((s for s in stages if s.stage_code == "hired"), None)
        if offer_stage and hired_stage:
            offer_acceptance = hired_stage.candidate_count / offer_stage.candidate_count if offer_stage.candidate_count > 0 else 0
            if offer_acceptance < 0.6:
                suggestions.append("Offer接受率偏低，建议调研市场薪酬水平和候选人诉求")

        if avg_hiring_days and avg_hiring_days > 30:
            suggestions.append(f"招聘周期较长（平均{avg_hiring_days:.0f}天），建议简化流程加快决策")

        if overall_conversion < 0.02:
            suggestions.append("整体录取率偏低（<2%），建议评估招聘标准合理性")

        if not suggestions:
            suggestions.append("招聘漏斗健康，建议持续监控关键指标")

        return suggestions[:6]

    def get_batch_analysis(
        self,
        job_titles: List[str],
    ) -> Dict[str, FunnelAnalysisResponse]:
        results = {}
        for job_title in job_titles:
            results[job_title] = self.analyze_funnel(job_title)
        return results

    def get_stage_definitions(self) -> List[dict]:
        return DEFAULT_FUNNEL_STAGES.copy()

    def import_existing_data(
        self,
        job_title: str,
        stage_counts: Dict[str, int],
    ):
        for i, stage_config in enumerate(DEFAULT_FUNNEL_STAGES):
            code = stage_config["code"]
            count = stage_counts.get(code, 0)
            for idx in range(count):
                candidate_id = f"imported_{code}_{idx}"
                self.add_candidate_stage(job_title, candidate_id, code)

    def clear_data(self, job_title: Optional[str] = None):
        if job_title:
            if job_title in self._stage_data:
                del self._stage_data[job_title]
        else:
            self._stage_data.clear()