import pandas as pd
import numpy as np
import random
from typing import List, Dict

random.seed(42)
np.random.seed(42)

JOB_TITLES = [
    "Python开发工程师", "Java后端开发", "前端开发工程师", "全栈开发工程师",
    "数据分析师", "数据科学家", "机器学习工程师", "算法工程师",
    "产品经理", "运营专员", "市场经理", "销售代表",
    "人力资源专员", "财务分析师", "UI设计师", "测试工程师",
    "运维工程师", "架构师", "项目经理", "技术支持工程师"
]

LOCATIONS = [
    "北京", "上海", "深圳", "广州", "杭州", "成都", "武汉",
    "西安", "南京", "苏州", "重庆", "天津"
]

LOCATION_WEIGHTS = {
    "北京": 1.3, "上海": 1.28, "深圳": 1.25, "广州": 1.1,
    "杭州": 1.15, "成都": 0.9, "武汉": 0.85, "西安": 0.82,
    "南京": 0.95, "苏州": 0.92, "重庆": 0.8, "天津": 0.88
}

COMPANY_SIZES = ["少于50人", "50-150人", "150-500人", "500-1000人", "1000人以上"]
COMPANY_SIZE_WEIGHTS = {
    "少于50人": 0.85, "50-150人": 0.95, "150-500人": 1.0,
    "500-1000人": 1.1, "1000人以上": 1.2
}

EDUCATION_LEVELS = ["大专", "本科", "硕士", "博士"]
EDUCATION_WEIGHTS = {
    "大专": 0.8, "本科": 1.0, "硕士": 1.3, "博士": 1.8
}

JOB_LEVEL_BASE = {
    "工程师": {"base": 12000, "range": 8000},
    "经理": {"base": 18000, "range": 12000},
    "专员": {"base": 8000, "range": 5000},
    "分析师": {"base": 14000, "range": 8000},
    "科学家": {"base": 25000, "range": 15000},
    "设计师": {"base": 12000, "range": 7000},
    "总监": {"base": 35000, "range": 20000}
}

JOB_DESCRIPTIONS = {
    "技术": [
        "负责公司核心产品的开发与维护，参与技术方案设计",
        "参与系统架构设计，优化系统性能，提升用户体验",
        "负责后端服务开发，确保代码质量和系统稳定性",
        "参与需求分析，提供技术解决方案，推动项目落地"
    ],
    "数据": [
        "负责数据分析和挖掘，为业务决策提供数据支持",
        "构建机器学习模型，解决实际业务问题",
        "设计和维护数据报表，监控业务指标变化"
    ],
    "产品": [
        "负责产品规划和设计，推动产品迭代优化",
        "协调研发、设计、运营团队，确保产品按时交付",
        "分析用户需求和市场动态，制定产品发展策略"
    ],
    "运营": [
        "负责日常运营工作，提升用户活跃度和留存率",
        "策划运营活动，提升品牌影响力和用户增长",
        "分析运营数据，优化运营策略和流程"
    ],
    "市场": [
        "负责市场推广和品牌建设，拓展市场渠道",
        "策划营销活动，提升产品知名度和市场份额",
        "分析市场趋势和竞争对手，制定市场策略"
    ]
}

SKILL_KEYWORDS = {
    "Python开发工程师": ["Python", "Django", "Flask", "FastAPI", "MySQL", "Redis"],
    "Java后端开发": ["Java", "Spring", "SpringBoot", "MySQL", "Redis", "Dubbo"],
    "前端开发工程师": ["JavaScript", "React", "Vue", "TypeScript", "HTML", "CSS"],
    "全栈开发工程师": ["JavaScript", "React", "Node.js", "MySQL", "MongoDB"],
    "数据分析师": ["SQL", "Excel", "Python", "Tableau", "统计学"],
    "数据科学家": ["Python", "机器学习", "深度学习", "TensorFlow", "PyTorch"],
    "机器学习工程师": ["Python", "机器学习", "特征工程", "模型调优"],
    "算法工程师": ["算法", "数据结构", "Python", "机器学习", "深度学习"],
    "产品经理": ["产品设计", "需求分析", "Axure", "用户研究", "数据分析"],
    "运营专员": ["运营", "活动策划", "数据分析", "用户增长"],
    "市场经理": ["市场营销", "品牌建设", "渠道拓展", "活动策划"],
    "销售代表": ["销售", "客户关系", "商务谈判", "业绩目标"],
    "人力资源专员": ["招聘", "培训", "绩效考核", "员工关系"],
    "财务分析师": ["财务分析", "预算编制", "Excel", "财务报表"],
    "UI设计师": ["UI设计", "Figma", "Sketch", "用户体验", "交互设计"],
    "测试工程师": ["测试", "自动化测试", "性能测试", "缺陷管理"],
    "运维工程师": ["运维", "Linux", "Docker", "K8s", "监控"],
    "架构师": ["系统架构", "技术选型", "性能优化", "微服务"],
    "项目经理": ["项目管理", "进度控制", "团队协调", "风险控制"],
    "技术支持工程师": ["技术支持", "问题排查", "客户沟通", "文档编写"]
}


def get_job_category(title: str) -> str:
    if any(key in title for key in ["开发", "工程师", "架构师", "运维", "测试"]):
        return "技术"
    elif any(key in title for key in ["数据", "科学"]):
        return "数据"
    elif "产品" in title:
        return "产品"
    elif "运营" in title:
        return "运营"
    elif any(key in title for key in ["市场", "销售"]):
        return "市场"
    else:
        return "技术"


def get_level_keyword(title: str) -> str:
    if "总监" in title:
        return "总监"
    elif "经理" in title:
        return "经理"
    elif "科学家" in title:
        return "科学家"
    elif "分析师" in title:
        return "分析师"
    elif "设计师" in title:
        return "设计师"
    elif "专员" in title:
        return "专员"
    else:
        return "工程师"


def generate_description(title: str) -> str:
    category = get_job_category(title)
    base_desc = random.choice(JOB_DESCRIPTIONS.get(category, JOB_DESCRIPTIONS["技术"]))
    skills = SKILL_KEYWORDS.get(title, ["沟通能力", "团队协作"])
    skill_str = "、".join(random.sample(skills, min(3, len(skills))))
    return f"{base_desc}。要求熟悉{skill_str}等相关技术，具备良好的沟通能力和团队协作精神。"


def calculate_salary(title: str, location: str, company_size: str, education: str) -> tuple:
    level_key = get_level_keyword(title)
    base_info = JOB_LEVEL_BASE[level_key]
    
    base_salary = base_info["base"]
    salary_range = base_info["range"]
    
    loc_factor = LOCATION_WEIGHTS[location]
    size_factor = COMPANY_SIZE_WEIGHTS[company_size]
    edu_factor = EDUCATION_WEIGHTS[education]
    
    total_factor = loc_factor * size_factor * edu_factor
    
    mid_salary = base_salary * total_factor
    noise = np.random.normal(0, 0.1)
    
    mid_salary = mid_salary * (1 + noise)
    
    lower = int(mid_salary - salary_range * total_factor * 0.4)
    upper = int(mid_salary + salary_range * total_factor * 0.4)
    
    lower = max(lower, 5000)
    upper = max(upper, lower + 2000)
    
    return lower, upper


def generate_dataset(n_samples: int = 5000) -> pd.DataFrame:
    data = []
    
    for _ in range(n_samples):
        title = random.choice(JOB_TITLES)
        location = random.choice(LOCATIONS)
        company_size = random.choice(COMPANY_SIZES)
        education = random.choice(EDUCATION_LEVELS)
        description = generate_description(title)
        
        salary_lower, salary_upper = calculate_salary(title, location, company_size, education)
        
        data.append({
            "岗位标题": title,
            "岗位描述": description,
            "地区": location,
            "公司规模": company_size,
            "学历要求": education,
            "薪资下限": salary_lower,
            "薪资上限": salary_upper
        })
    
    df = pd.DataFrame(data)
    
    outliers = int(n_samples * 0.03)
    outlier_indices = np.random.choice(n_samples, outliers, replace=False)
    
    for idx in outlier_indices:
        factor = random.choice([0.4, 0.5, 2.5, 3.0])
        df.loc[idx, "薪资下限"] = int(df.loc[idx, "薪资下限"] * factor)
        df.loc[idx, "薪资上限"] = int(df.loc[idx, "薪资上限"] * factor)
    
    return df


if __name__ == "__main__":
    df = generate_dataset(5000)
    df.to_csv("job_salary_data.csv", index=False, encoding="utf-8-sig")
    print(f"数据集生成完成，共 {len(df)} 条数据")
    print("\n数据集前5行:")
    print(df.head())
    print("\n薪资统计信息:")
    print(df[["薪资下限", "薪资上限"]].describe())
    print("\n各地区岗位数量:")
    print(df["地区"].value_counts())
