import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from scipy import stats


class SalaryTrendAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df["发布日期"] = pd.to_datetime(self.df["发布日期"])
        self.df["年月"] = self.df["发布日期"].dt.to_period("M")
        self.df["薪资中位数"] = (self.df["薪资下限"] + self.df["薪资上限"]) / 2
    
    def get_city_trend(self, city: str = None, 
                       resample_freq: str = "M") -> pd.DataFrame:
        df = self.df.copy()
        if city and city in df["地区"].unique():
            df = df[df["地区"] == city]
        
        df = df.set_index("发布日期")
        
        if resample_freq == "M":
            trend = df.resample("M").agg({
                "薪资中位数": ["mean", "median", "std", "count"],
                "薪资下限": "mean",
                "薪资上限": "mean"
            }).round(0)
        elif resample_freq == "Q":
            trend = df.resample("Q").agg({
                "薪资中位数": ["mean", "median", "std", "count"],
                "薪资下限": "mean",
                "薪资上限": "mean"
            }).round(0)
        else:
            trend = df.resample("W").agg({
                "薪资中位数": ["mean", "median", "std", "count"],
                "薪资下限": "mean",
                "薪资上限": "mean"
            }).round(0)
        
        trend.columns = ["薪资均值", "薪资中位数", "薪资标准差", "样本量", "下限均值", "上限均值"]
        trend["同比增长率"] = trend["薪资均值"].pct_change(12).round(4) * 100
        trend["环比增长率"] = trend["薪资均值"].pct_change(1).round(4) * 100
        
        return trend.reset_index()
    
    def get_job_category_trend(self, category: str = None,
                                resample_freq: str = "M") -> pd.DataFrame:
        df = self.df.copy()
        
        def get_category(title):
            if any(k in title for k in ["开发", "工程师", "架构师", "运维", "测试"]):
                return "技术开发"
            elif any(k in title for k in ["数据", "科学", "算法"]):
                return "数据科学"
            elif any(k in title for k in ["产品", "运营", "市场", "销售"]):
                return "产品运营"
            elif any(k in title for k in ["设计", "UI", "UE"]):
                return "设计创意"
            else:
                return "职能支持"
        
        df["岗位类型"] = df["岗位标题"].apply(get_category)
        
        if category and category in df["岗位类型"].unique():
            df = df[df["岗位类型"] == category]
        
        df = df.set_index("发布日期")
        
        if resample_freq == "M":
            trend = df.resample("M").agg({
                "薪资中位数": ["mean", "count"],
                "岗位类型": lambda x: x.mode()[0] if len(x) > 0 else None
            }).round(0)
        else:
            trend = df.resample("Q").agg({
                "薪资中位数": ["mean", "count"],
                "岗位类型": lambda x: x.mode()[0] if len(x) > 0 else None
            }).round(0)
        
        trend.columns = ["薪资均值", "样本量", "岗位类型"]
        trend["同比增长率"] = trend["薪资均值"].pct_change(4).round(4) * 100
        trend["环比增长率"] = trend["薪资均值"].pct_change(1).round(4) * 100
        
        return trend.reset_index()
    
    def get_cross_comparison(self, group_by: str = "地区") -> pd.DataFrame:
        if group_by not in ["地区", "公司规模", "学历要求"]:
            group_by = "地区"
        
        comparison = self.df.groupby(group_by).agg({
            "薪资中位数": ["mean", "median", "std", "min", "max", "count"],
            "薪资下限": "mean",
            "薪资上限": "mean"
        }).round(0)
        
        comparison.columns = ["薪资均值", "薪资中位数", "薪资标准差", "薪资最低", "薪资最高", "样本量", "下限均值", "上限均值"]
        comparison["薪资范围"] = comparison.apply(
            lambda x: f"{int(x['下限均值'])}-{int(x['上限均值'])}", axis=1
        )
        comparison["变异系数"] = (comparison["薪资标准差"] / comparison["薪资均值"]).round(3)
        
        return comparison.sort_values("薪资均值", ascending=False).reset_index()


class JobCompetitionScorer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df["薪资中位数"] = (self.df["薪资下限"] + self.df["薪资上限"]) / 2
        self._build_reference_data()
    
    def _build_reference_data(self):
        self.city_ref = self.df.groupby("地区")["薪资中位数"].agg(
            ["mean", "median", "std", lambda x: np.percentile(x, 25), 
             lambda x: np.percentile(x, 75), "count"]
        ).round(0)
        self.city_ref.columns = ["均值", "中位数", "标准差", "P25", "P75", "样本量"]
        
        self.df["岗位类型"] = self.df["岗位标题"].apply(self._get_job_type)
        self.job_ref = self.df.groupby("岗位类型")["薪资中位数"].agg(
            ["mean", "median", "std", lambda x: np.percentile(x, 25), 
             lambda x: np.percentile(x, 75), "count"]
        ).round(0)
        self.job_ref.columns = ["均值", "中位数", "标准差", "P25", "P75", "样本量"]
        
        self.city_job_ref = self.df.groupby(["地区", "岗位类型"])["薪资中位数"].agg(
            ["mean", "median", "std", "count"]
        ).round(0)
        self.city_job_ref.columns = ["均值", "中位数", "标准差", "样本量"]
    
    def _get_job_type(self, title: str) -> str:
        if any(k in title for k in ["开发", "工程师", "架构师", "运维", "测试"]):
            return "技术开发"
        elif any(k in title for k in ["数据", "科学", "算法"]):
            return "数据科学"
        elif any(k in title for k in ["产品", "运营", "市场", "销售"]):
            return "产品运营"
        elif any(k in title for k in ["设计", "UI", "UE"]):
            return "设计创意"
        else:
            return "职能支持"
    
    def calculate_score(self, job_title: str, city: str, 
                        salary_lower: int, salary_upper: int) -> Dict:
        salary_median = (salary_lower + salary_upper) / 2
        job_type = self._get_job_type(job_title)
        
        city_stats = self.city_ref.loc[city] if city in self.city_ref.index else None
        job_stats = self.job_ref.loc[job_type] if job_type in self.job_ref.index else None
        
        try:
            city_job_stats = self.city_job_ref.loc[(city, job_type)]
        except KeyError:
            city_job_stats = None
        
        city_percentile = 50
        job_percentile = 50
        city_job_percentile = 50
        
        if city_stats is not None:
            city_data = self.df[self.df["地区"] == city]["薪资中位数"]
            city_percentile = stats.percentileofscore(city_data, salary_median).round(1)
        
        if job_stats is not None:
            job_data = self.df[self.df["岗位类型"] == job_type]["薪资中位数"]
            job_percentile = stats.percentileofscore(job_data, salary_median).round(1)
        
        if city_job_stats is not None:
            city_job_data = self.df[
                (self.df["地区"] == city) & (self.df["岗位类型"] == job_type)
            ]["薪资中位数"]
            if len(city_job_data) > 10:
                city_job_percentile = stats.percentileofscore(city_job_data, salary_median).round(1)
        
        competition_score = int((city_percentile * 0.3 + job_percentile * 0.3 + 
                                  city_job_percentile * 0.4))
        
        if competition_score >= 80:
            level = "S - 极具竞争力"
            color = "green"
        elif competition_score >= 65:
            level = "A - 竞争力较强"
            color = "lightgreen"
        elif competition_score >= 50:
            level = "B - 中等竞争力"
            color = "yellow"
        elif competition_score >= 30:
            level = "C - 竞争力一般"
            color = "orange"
        else:
            level = "D - 竞争力较弱"
            color = "red"
        
        city_diff = 0
        if city_stats is not None:
            city_diff = ((salary_median - city_stats["均值"]) / city_stats["均值"] * 100).round(1)
        
        job_diff = 0
        if job_stats is not None:
            job_diff = ((salary_median - job_stats["均值"]) / job_stats["均值"] * 100).round(1)
        
        return {
            "岗位类型": job_type,
            "薪资中位数": salary_median,
            "竞争力评分": competition_score,
            "竞争力等级": level,
            "等级颜色": color,
            "同地区百分位": city_percentile,
            "同岗位百分位": job_percentile,
            "同地区同岗位百分位": city_job_percentile,
            "同地区薪资对比": f"{salary_median:.0f} vs {city_stats['均值']:.0f} ({city_diff:+.1f}%)" if city_stats is not None else "数据不足",
            "同岗位薪资对比": f"{salary_median:.0f} vs {job_stats['均值']:.0f} ({job_diff:+.1f}%)" if job_stats is not None else "数据不足",
            "同地区同岗位样本量": int(city_job_stats["样本量"]) if city_job_stats is not None else 0
        }


class SkillPremiumAnalyzer:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self.df["薪资中位数"] = (self.df["薪资下限"] + self.df["薪资上限"]) / 2
        
        self.target_skills = {
            "云原生": ["Kubernetes", "K8s", "Docker", "容器", "微服务"],
            "AI/ML": ["PyTorch", "TensorFlow", "深度学习", "机器学习", "Transformer"],
            "大数据": ["Spark", "Hadoop", "Kafka", "Flink", "数据仓库"],
            "前端框架": ["React", "Vue", "Angular", "Next.js", "TypeScript"],
            "后端框架": ["Spring", "Django", "FastAPI", "Go", "Rust"],
            "数据库": ["PostgreSQL", "MongoDB", "Redis", "Elasticsearch"],
            "DevOps": ["CI/CD", "Jenkins", "GitLab", "Prometheus", "Grafana"],
            "安全": ["安全", "渗透", "漏洞", "加密", "安全审计"]
        }
        
        self.skill_premiums = {}
        self._calculate_premiums()
    
    def _extract_skills(self, text: str) -> List[str]:
        found_skills = []
        text_lower = str(text).lower()
        
        for category, skills in self.target_skills.items():
            for skill in skills:
                if skill.lower() in text_lower:
                    found_skills.append(skill)
        
        return found_skills
    
    def _calculate_premiums(self):
        baseline_avg = self.df["薪资中位数"].mean()
        
        for category, skills in self.target_skills.items():
            category_premiums = []
            
            for skill in skills:
                has_skill = self.df["岗位描述"].str.lower().str.contains(skill.lower(), na=False)
                skill_df = self.df[has_skill]
                
                if len(skill_df) >= 20:
                    skill_avg = skill_df["薪资中位数"].mean()
                    premium_pct = ((skill_avg - baseline_avg) / baseline_avg * 100).round(1)
                    premium_amount = int(skill_avg - baseline_avg)
                    
                    category_premiums.append({
                        "技能": skill,
                        "样本量": len(skill_df),
                        "薪资均值": int(skill_avg),
                        "溢价比例": premium_pct,
                        "溢价金额": premium_amount
                    })
            
            if category_premiums:
                self.skill_premiums[category] = sorted(
                    category_premiums, key=lambda x: x["溢价比例"], reverse=True
                )
    
    def get_top_skills(self, top_n: int = 10) -> pd.DataFrame:
        all_skills = []
        for category, skills in self.skill_premiums.items():
            for skill in skills:
                skill["分类"] = category
                all_skills.append(skill)
        
        df = pd.DataFrame(all_skills)
        df = df.sort_values("溢价比例", ascending=False).head(top_n)
        
        return df[["分类", "技能", "样本量", "薪资均值", "溢价比例", "溢价金额"]]
    
    def get_premium_by_category(self) -> pd.DataFrame:
        category_stats = []
        
        for category, skills in self.skill_premiums.items():
            if skills:
                avg_premium = np.mean([s["溢价比例"] for s in skills])
                avg_salary = np.mean([s["薪资均值"] for s in skills])
                total_samples = sum([s["样本量"] for s in skills])
                
                category_stats.append({
                    "技能分类": category,
                    "技能数量": len(skills),
                    "平均溢价比例": round(avg_premium, 1),
                    "平均薪资": int(avg_salary),
                    "总样本量": total_samples
                })
        
        return pd.DataFrame(category_stats).sort_values("平均溢价比例", ascending=False)
    
    def get_skill_detail(self, skill_name: str) -> Dict:
        skill_lower = skill_name.lower()
        
        for category, skills in self.skill_premiums.items():
            for skill in skills:
                if skill["技能"].lower() == skill_lower:
                    return {
                        **skill,
                        "分类": category
                    }
        
        has_skill = self.df["岗位描述"].str.lower().str.contains(skill_lower, na=False)
        skill_df = self.df[has_skill]
        
        if len(skill_df) == 0:
            return {"error": "未找到该技能数据"}
        
        baseline_avg = self.df["薪资中位数"].mean()
        skill_avg = skill_df["薪资中位数"].mean()
        
        return {
            "技能": skill_name,
            "分类": "其他",
            "样本量": len(skill_df),
            "薪资均值": int(skill_avg),
            "溢价比例": round((skill_avg - baseline_avg) / baseline_avg * 100, 1),
            "溢价金额": int(skill_avg - baseline_avg)
        }
    
    def analyze_job_skills(self, job_description: str) -> Dict:
        found_skills = self._extract_skills(job_description)
        
        if not found_skills:
            return {
                "识别技能": [],
                "技能溢价汇总": 0,
                "平均溢价": 0,
                "技能增值潜力": "暂无特定技能数据"
            }
        
        skill_details = []
        total_premium = 0
        premium_count = 0
        
        for skill in found_skills:
            detail = self.get_skill_detail(skill)
            if "error" not in detail:
                skill_details.append(detail)
                total_premium += detail["溢价金额"]
                premium_count += 1
        
        avg_premium = total_premium / premium_count if premium_count > 0 else 0
        
        if avg_premium >= 5000:
            potential = "高增值技能组合"
        elif avg_premium >= 3000:
            potential = "中高增值技能组合"
        elif avg_premium >= 1500:
            potential = "中等增值技能组合"
        else:
            potential = "基础技能组合"
        
        return {
            "识别技能": found_skills,
            "技能详情": skill_details,
            "技能溢价汇总": total_premium,
            "平均单技能溢价": int(avg_premium),
            "技能增值潜力": potential
        }


if __name__ == "__main__":
    print("=" * 70)
    print("薪资分析模块测试")
    print("=" * 70)
    
    df = pd.read_csv("job_salary_data_v2.csv", encoding="utf-8-sig")
    print(f"\n加载数据: {len(df)} 条")
    
    print("\n[1/3] 薪资趋势分析...")
    trend_analyzer = SalaryTrendAnalyzer(df)
    city_trend = trend_analyzer.get_city_trend("北京")
    print(f"北京薪资趋势: {len(city_trend)} 个月数据")
    print(city_trend[["发布日期", "薪资均值", "同比增长率"]].tail(6))
    
    print("\n[2/3] 岗位竞争力评分...")
    scorer = JobCompetitionScorer(df)
    score = scorer.calculate_score("Python开发工程师", "北京", 25000, 35000)
    print(f"竞争力评分: {score['竞争力评分']}分 - {score['竞争力等级']}")
    print(f"同地区百分位: {score['同地区百分位']}%")
    print(f"同岗位百分位: {score['同岗位百分位']}%")
    
    print("\n[3/3] 技能溢价分析...")
    skill_analyzer = SkillPremiumAnalyzer(df)
    top_skills = skill_analyzer.get_top_skills(10)
    print("Top 10 高溢价技能:")
    print(top_skills[["技能", "分类", "薪资均值", "溢价比例", "样本量"]])
    
    print("\n" + "=" * 70)
    print("所有分析模块测试通过！")
    print("=" * 70)
