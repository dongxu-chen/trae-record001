import random
import uuid
from datetime import datetime, timedelta
from typing import List, Dict

from data.models import (
    BusinessInfo, ShareholderInfo, ExecutiveInfo, JudicialRisk,
    IntellectualProperty, TaxRecord, FinancialInfo, LoanRecord, CompanyInput
)

INDUSTRIES = [
    "制造业", "信息技术", "金融业", "建筑业", "批发零售",
    "房地产", "交通运输", "新能源", "生物医药", "文化教育"
]

STATUSES = ["存续（在营）", "在营", "开业", "迁出", "注销"]


def random_date(years_ago: int = 10) -> str:
    days = random.randint(365, years_ago * 365)
    return (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")


def generate_company(
    risk_level: str = "medium",
    company_id: str = None,
    company_name: str = None
) -> CompanyInput:
    if company_id is None:
        company_id = f"COMP{uuid.uuid4().hex[:8].upper()}"
    if company_name is None:
        company_name = f"{random.choice(['华', '中', '大', '新', '鑫', '盛', '鸿', '永', '金', '恒'])}{random.choice(['瑞', '泰', '信', '诚', '源', '通', '博', '晟', '达', '铭'])}{random.choice(['科技', '实业', '贸易', '投资', '工程', '信息'])}有限公司"

    if risk_level == "high":
        return _generate_high_risk(company_id, company_name)
    elif risk_level == "low":
        return _generate_low_risk(company_id, company_name)
    else:
        return _generate_medium_risk(company_id, company_name)


def _generate_low_risk(company_id: str, company_name: str) -> CompanyInput:
    registered_capital = round(random.uniform(5000, 50000), 2)
    paid_in = round(registered_capital * random.uniform(0.85, 1.0), 2)

    business_info = BusinessInfo(
        company_id=company_id,
        company_name=company_name,
        registered_capital=registered_capital,
        paid_in_capital=paid_in,
        established_date=random_date(15),
        operating_status=random.choice(["存续（在营）", "在营"]),
        industry=random.choice(INDUSTRIES),
        business_scope="许可项目：各类工程建设活动；一般项目：技术服务、软件开发、企业管理咨询",
        number_of_employees=random.randint(100, 2000),
        registered_address="北京市海淀区中关村大街1号"
    )

    shareholders = [
        ShareholderInfo(
            company_id=company_id,
            shareholder_name=f"{random.choice(['张', '李', '王', '刘', '陈'])}{random.choice(['建国', '晓明', '伟', '芳', '磊'])}",
            share_ratio=round(random.uniform(0.3, 0.6), 4),
            shareholder_type="自然人股东"
        ),
        ShareholderInfo(
            company_id=company_id,
            shareholder_name=f"{random.choice(['控股', '投资', '资本'])}集团有限公司",
            share_ratio=round(random.uniform(0.2, 0.4), 4),
            shareholder_type="法人股东"
        )
    ]

    executives = [
        ExecutiveInfo(
            company_id=company_id,
            name=f"{random.choice(['赵', '孙', '周', '吴'])}总",
            position=random.choice(["董事长", "总经理", "CEO"]),
            tenure_years=round(random.uniform(5, 15), 1)
        )
    ]

    judicial_risk = JudicialRisk(
        company_id=company_id,
        lawsuit_count=random.randint(0, 3),
        executed_person_count=0,
        total_executed_amount=0.0,
        administrative_penalty_count=random.randint(0, 1),
        total_penalty_amount=round(random.uniform(0, 20000), 2),
        contract_breach_count=random.randint(0, 1),
        abnormal_operation_records=0,
        dishonest_records=0
    )

    ip = IntellectualProperty(
        company_id=company_id,
        patent_count=random.randint(10, 100),
        invention_patent_count=random.randint(3, 30),
        utility_model_count=random.randint(5, 50),
        trademark_count=random.randint(5, 50),
        copyright_count=random.randint(5, 100),
        patent_invalidation_count=0
    )

    tax_record = TaxRecord(
        company_id=company_id,
        tax_arrears_count=0,
        total_arrears_amount=0.0,
        tax_credit_rating=random.choice(["A", "A", "B"]),
        continuous_tax_years=random.randint(5, 15),
        annual_tax_amount=round(random.uniform(500, 5000), 2)
    )

    revenue = round(random.uniform(5000, 50000), 2)
    net_profit = round(revenue * random.uniform(0.1, 0.3), 2)
    total_assets = round(revenue * random.uniform(1.5, 5), 2)
    total_liabilities = round(total_assets * random.uniform(0.2, 0.4), 2)

    financial_info = FinancialInfo(
        company_id=company_id,
        revenue=revenue,
        net_profit=net_profit,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        current_ratio=round(total_assets / total_liabilities, 2),
        debt_to_equity_ratio=round(total_liabilities / (total_assets - total_liabilities), 2),
        roe=round(net_profit / (total_assets - total_liabilities), 4)
    )

    loan_records = [
        LoanRecord(
            company_id=company_id,
            loan_id=f"LOAN{uuid.uuid4().hex[:6].upper()}",
            principal_amount=round(random.uniform(500, 3000), 2),
            outstanding_amount=round(random.uniform(0, 500), 2),
            issue_date=random_date(5),
            maturity_date=(datetime.now() + timedelta(days=random.randint(365, 1095))).strftime("%Y-%m-%d"),
            interest_rate=round(random.uniform(0.04, 0.08), 4),
            repayment_status="正常还款",
            overdue_days=0
        )
    ]

    return CompanyInput(
        business_info=business_info,
        shareholders=shareholders,
        executives=executives,
        judicial_risk=judicial_risk,
        ip=ip,
        tax_record=tax_record,
        financial_info=financial_info,
        loan_records=loan_records
    )


def _generate_medium_risk(company_id: str, company_name: str) -> CompanyInput:
    registered_capital = round(random.uniform(500, 5000), 2)
    paid_in = round(registered_capital * random.uniform(0.4, 0.75), 2)

    business_info = BusinessInfo(
        company_id=company_id,
        company_name=company_name,
        registered_capital=registered_capital,
        paid_in_capital=paid_in,
        established_date=random_date(8),
        operating_status=random.choice(["存续（在营）", "在营", "开业"]),
        industry=random.choice(INDUSTRIES),
        business_scope="一般项目：企业管理咨询、软件开发；许可项目：建设工程施工",
        number_of_employees=random.randint(20, 300),
        registered_address="上海市浦东新区张江高科技园区"
    )

    shareholders = [
        ShareholderInfo(
            company_id=company_id,
            shareholder_name=f"{random.choice(['张', '李', '王', '刘', '陈'])}{random.choice(['建国', '晓明', '伟', '芳', '磊'])}",
            share_ratio=round(random.uniform(0.5, 0.9), 4),
            shareholder_type="自然人股东"
        )
    ]

    executives = [
        ExecutiveInfo(
            company_id=company_id,
            name=f"{random.choice(['赵', '孙', '周', '吴'])}总",
            position="总经理",
            tenure_years=round(random.uniform(1, 8), 1)
        )
    ]

    judicial_risk = JudicialRisk(
        company_id=company_id,
        lawsuit_count=random.randint(2, 8),
        executed_person_count=random.randint(0, 1),
        total_executed_amount=round(random.uniform(0, 100000), 2),
        administrative_penalty_count=random.randint(1, 3),
        total_penalty_amount=round(random.uniform(10000, 100000), 2),
        contract_breach_count=random.randint(1, 4),
        abnormal_operation_records=random.randint(0, 1),
        dishonest_records=0
    )

    ip = IntellectualProperty(
        company_id=company_id,
        patent_count=random.randint(2, 20),
        invention_patent_count=random.randint(0, 5),
        utility_model_count=random.randint(1, 10),
        trademark_count=random.randint(1, 10),
        copyright_count=random.randint(0, 20),
        patent_invalidation_count=random.randint(0, 2)
    )

    tax_record = TaxRecord(
        company_id=company_id,
        tax_arrears_count=random.randint(0, 1),
        total_arrears_amount=round(random.uniform(0, 50000), 2),
        tax_credit_rating=random.choice(["B", "B", "C"]),
        continuous_tax_years=random.randint(2, 8),
        annual_tax_amount=round(random.uniform(50, 500), 2)
    )

    revenue = round(random.uniform(500, 5000), 2)
    net_profit = round(revenue * random.uniform(-0.05, 0.1), 2)
    total_assets = round(revenue * random.uniform(1, 3), 2)
    total_liabilities = round(total_assets * random.uniform(0.4, 0.7), 2)

    financial_info = FinancialInfo(
        company_id=company_id,
        revenue=revenue,
        net_profit=net_profit,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        current_ratio=round(total_assets / total_liabilities, 2) if total_liabilities > 0 else 1.0,
        debt_to_equity_ratio=round(total_liabilities / max((total_assets - total_liabilities), 1), 2),
        roe=round(net_profit / max((total_assets - total_liabilities), 1), 4)
    )

    loan_records = [
        LoanRecord(
            company_id=company_id,
            loan_id=f"LOAN{uuid.uuid4().hex[:6].upper()}",
            principal_amount=round(random.uniform(100, 1000), 2),
            outstanding_amount=round(random.uniform(50, 500), 2),
            issue_date=random_date(3),
            maturity_date=(datetime.now() + timedelta(days=random.randint(180, 730))).strftime("%Y-%m-%d"),
            interest_rate=round(random.uniform(0.06, 0.12), 4),
            repayment_status=random.choice(["正常还款", "正常还款", "逾期"]),
            overdue_days=random.choice([0, 0, 0, random.randint(1, 30)])
        )
    ]

    return CompanyInput(
        business_info=business_info,
        shareholders=shareholders,
        executives=executives,
        judicial_risk=judicial_risk,
        ip=ip,
        tax_record=tax_record,
        financial_info=financial_info,
        loan_records=loan_records
    )


def _generate_high_risk(company_id: str, company_name: str) -> CompanyInput:
    registered_capital = round(random.uniform(50, 500), 2)
    paid_in = round(registered_capital * random.uniform(0.05, 0.3), 2)

    business_info = BusinessInfo(
        company_id=company_id,
        company_name=company_name,
        registered_capital=registered_capital,
        paid_in_capital=paid_in,
        established_date=random_date(4),
        operating_status=random.choice(["迁出", "注销", "存续（在营）"]),
        industry=random.choice(INDUSTRIES),
        business_scope="一般项目：企业管理咨询",
        number_of_employees=random.randint(1, 50),
        registered_address="深圳市南山区科技园"
    )

    shareholders = [
        ShareholderInfo(
            company_id=company_id,
            shareholder_name=f"{random.choice(['张', '李', '王'])}某",
            share_ratio=round(random.uniform(0.9, 1.0), 4),
            shareholder_type="自然人股东"
        )
    ]

    executives = [
        ExecutiveInfo(
            company_id=company_id,
            name="法人代表",
            position="执行董事",
            tenure_years=round(random.uniform(0.5, 3), 1)
        )
    ]

    judicial_risk = JudicialRisk(
        company_id=company_id,
        lawsuit_count=random.randint(8, 30),
        executed_person_count=random.randint(1, 5),
        total_executed_amount=round(random.uniform(100000, 2000000), 2),
        administrative_penalty_count=random.randint(3, 10),
        total_penalty_amount=round(random.uniform(50000, 500000), 2),
        contract_breach_count=random.randint(3, 10),
        abnormal_operation_records=random.randint(1, 3),
        dishonest_records=random.randint(1, 3)
    )

    ip = IntellectualProperty(
        company_id=company_id,
        patent_count=random.randint(0, 3),
        invention_patent_count=0,
        utility_model_count=random.randint(0, 2),
        trademark_count=random.randint(0, 3),
        copyright_count=0,
        patent_invalidation_count=random.randint(0, 3)
    )

    tax_record = TaxRecord(
        company_id=company_id,
        tax_arrears_count=random.randint(2, 5),
        total_arrears_amount=round(random.uniform(50000, 500000), 2),
        tax_credit_rating=random.choice(["C", "D"]),
        continuous_tax_years=random.randint(0, 3),
        annual_tax_amount=round(random.uniform(0, 30), 2)
    )

    revenue = round(random.uniform(50, 500), 2)
    net_profit = round(-revenue * random.uniform(0.1, 0.5), 2)
    total_assets = round(revenue * random.uniform(0.5, 1.5), 2)
    total_liabilities = round(total_assets * random.uniform(0.8, 1.2), 2)

    financial_info = FinancialInfo(
        company_id=company_id,
        revenue=revenue,
        net_profit=net_profit,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        current_ratio=round(total_assets / max(total_liabilities, 1), 2),
        debt_to_equity_ratio=round(total_liabilities / max((total_assets - total_liabilities), 1), 2),
        roe=round(net_profit / max((total_assets - total_liabilities), 1), 4)
    )

    loan_records = [
        LoanRecord(
            company_id=company_id,
            loan_id=f"LOAN{uuid.uuid4().hex[:6].upper()}",
            principal_amount=round(random.uniform(50, 500), 2),
            outstanding_amount=round(random.uniform(30, 300), 2),
            issue_date=random_date(2),
            maturity_date=(datetime.now() - timedelta(days=random.randint(0, 180))).strftime("%Y-%m-%d"),
            interest_rate=round(random.uniform(0.10, 0.20), 4),
            repayment_status="逾期",
            overdue_days=random.randint(30, 180)
        )
    ]

    return CompanyInput(
        business_info=business_info,
        shareholders=shareholders,
        executives=executives,
        judicial_risk=judicial_risk,
        ip=ip,
        tax_record=tax_record,
        financial_info=financial_info,
        loan_records=loan_records
    )


def generate_training_data(n_samples: int = 500) -> List[CompanyInput]:
    companies = []
    for i in range(n_samples):
        rand = random.random()
        if rand < 0.3:
            companies.append(generate_company("high"))
        elif rand < 0.7:
            companies.append(generate_company("medium"))
        else:
            companies.append(generate_company("low"))
    return companies
