import json
import os
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from collections import defaultdict
from datetime import datetime

TAX_DEDUCTIBLE_CATEGORIES = {
    "餐饮": {
        "deductible": False,
        "rate": 0.0,
        "description": "个人餐饮消费不可抵扣个税",
        "max_amount": 0.0
    },
    "交通": {
        "deductible": True,
        "rate": 1.0,
        "description": "公务交通费用可申请报销抵扣",
        "max_amount": 18000.0,
        "conditions": ["公务用车补贴", "上下班交通", "出差交通"]
    },
    "购物": {
        "deductible": False,
        "rate": 0.0,
        "description": "个人购物消费不可抵扣",
        "max_amount": 0.0
    },
    "娱乐": {
        "deductible": False,
        "rate": 0.0,
        "description": "个人娱乐消费不可抵扣",
        "max_amount": 0.0
    },
    "医疗": {
        "deductible": True,
        "rate": 1.0,
        "description": "大病医疗专项附加扣除（超过15000元部分）",
        "max_amount": 80000.0,
        "min_threshold": 15000.0
    }
}

SPECIAL_DEDUCTIONS = {
    "子女教育": {
        "deductible": True,
        "amount": 12000.0,
        "description": "每个子女每年12000元（每月1000元）"
    },
    "继续教育": {
        "deductible": True,
        "amount": 4800.0,
        "description": "学历教育每年4800元，职业资格教育每年3600元"
    },
    "大病医疗": {
        "deductible": True,
        "amount": 80000.0,
        "description": "超过15000元的部分，每年限额80000元"
    },
    "住房贷款利息": {
        "deductible": True,
        "amount": 12000.0,
        "description": "首套住房贷款利息每年12000元（每月1000元）"
    },
    "住房租金": {
        "deductible": True,
        "amount": 18000.0,
        "description": "根据城市不同，每年14400-18000元"
    },
    "赡养老人": {
        "deductible": True,
        "amount": 24000.0,
        "description": "独生子女每年24000元，非独生子女分摊"
    },
    "3岁以下婴幼儿照护": {
        "deductible": True,
        "amount": 12000.0,
        "description": "每个婴幼儿每年12000元（每月1000元）"
    }
}

BUSINESS_DEDUCTIBLE_RULES = {
    "餐饮": {
        "deductible": True,
        "rate": 0.60,
        "description": "业务招待费按60%扣除，最高不超过当年销售收入的5‰",
        "max_ratio": 0.005
    },
    "交通": {
        "deductible": True,
        "rate": 1.0,
        "description": "差旅费、交通费可全额扣除",
        "conditions": ["出差", "公务", "差旅"]
    },
    "购物": {
        "deductible": True,
        "rate": 1.0,
        "description": "办公用品、办公设备购置可全额扣除",
        "conditions": ["办公", "设备", "用品"]
    },
    "娱乐": {
        "deductible": True,
        "rate": 0.60,
        "description": "业务招待费按60%扣除",
        "max_ratio": 0.005
    },
    "医疗": {
        "deductible": True,
        "rate": 1.0,
        "description": "补充医疗保险可在职工福利费中扣除"
    }
}

@dataclass
class TaxConfig:
    tax_type: str = "personal"
    annual_income: float = 200000.0
    tax_rate: float = 0.25
    special_deductions: Dict[str, float] = field(default_factory=dict)
    other_deductions: float = 0.0

class TaxCalculator:
    def __init__(self, config_path: str = "data/tax_config.json"):
        self.config_path = config_path
        self.config = TaxConfig()
        self._load_config()
    
    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.config = TaxConfig(**data)
            except Exception:
                pass
    
    def _save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.config), f, ensure_ascii=False, indent=2)
    
    def update_config(self, config: TaxConfig):
        self.config = config
        self._save_config()
    
    def calculate_personal_deduction(
        self,
        transactions: List[Dict],
        tax_year: Optional[int] = None
    ) -> Dict[str, Any]:
        if tax_year is None:
            tax_year = datetime.now().year
        
        df = pd.DataFrame(transactions)
        if df.empty:
            return {}
        
        df['date'] = pd.to_datetime(df['date'])
        df_year = df[df['date'].dt.year == tax_year]
        
        if df_year.empty:
            return {}
        
        category_totals = df_year.groupby('category')['amount'].sum().to_dict()
        
        deductions = []
        total_deductible = 0.0
        
        for category, amount in category_totals.items():
            cat_info = TAX_DEDUCTIBLE_CATEGORIES.get(category, {})
            
            if cat_info.get("deductible", False):
                max_amount = cat_info.get("max_amount", 0.0)
                rate = cat_info.get("rate", 0.0)
                min_threshold = cat_info.get("min_threshold", 0.0)
                
                eligible_amount = max(0, amount - min_threshold)
                deductible_amount = min(eligible_amount * rate, max_amount) if max_amount > 0 else eligible_amount * rate
                
                reason = cat_info.get("description", "")
                if min_threshold > 0 and amount <= min_threshold:
                    reason = f"未达到起扣点{min_threshold:.0f}元"
                    deductible_amount = 0.0
                
                deductions.append({
                    'category': category,
                    'total_amount': round(amount, 2),
                    'deductible_amount': round(deductible_amount, 2),
                    'rate': rate,
                    'description': cat_info.get("description", ""),
                    'eligible': deductible_amount > 0,
                    'reason': reason
                })
                
                total_deductible += deductible_amount
            else:
                deductions.append({
                    'category': category,
                    'total_amount': round(amount, 2),
                    'deductible_amount': 0.0,
                    'rate': 0.0,
                    'description': '不可抵扣',
                    'eligible': False,
                    'reason': cat_info.get("description", "该类别不可抵扣个税")
                })
        
        special_total = sum(self.config.special_deductions.values())
        total_deduction = total_deductible + special_total + self.config.other_deductions
        
        taxable_income = max(0, self.config.annual_income - 60000 - total_deduction)
        
        tax_brackets = [
            (0, 36000, 0.03, 0),
            (36000, 144000, 0.10, 2520),
            (144000, 300000, 0.20, 16920),
            (300000, 420000, 0.25, 31920),
            (420000, 660000, 0.30, 52920),
            (660000, 960000, 0.35, 85920),
            (960000, float('inf'), 0.45, 181920)
        ]
        
        tax_payable = 0.0
        for low, high, rate, quick in tax_brackets:
            if taxable_income <= 0:
                tax_payable = 0.0
                break
            elif low < taxable_income <= high:
                tax_payable = taxable_income * rate - quick
                break
        
        tax_without_deduction = max(0, self.config.annual_income - 60000)
        for low, high, rate, quick in tax_brackets:
            if tax_without_deduction <= 0:
                tax_without_deduction = 0.0
                break
            elif low < tax_without_deduction <= high:
                tax_without_deduction = tax_without_deduction * rate - quick
                break
        
        return {
            'tax_year': tax_year,
            'annual_income': self.config.annual_income,
            'category_deductions': deductions,
            'special_deductions': self.config.special_deductions,
            'special_total': special_total,
            'other_deductions': self.config.other_deductions,
            'basic_deduction': 60000,
            'total_deduction': round(total_deduction + 60000, 2),
            'taxable_income': round(taxable_income, 2),
            'tax_payable': round(tax_payable, 2),
            'tax_without_deduction': round(tax_without_deduction, 2),
            'tax_saved': round(tax_without_deduction - tax_payable, 2),
            'effective_tax_rate': round(tax_payable / self.config.annual_income * 100, 2) if self.config.annual_income > 0 else 0
        }
    
    def calculate_business_deduction(
        self,
        transactions: List[Dict],
        business_type: str = "enterprise",
        annual_revenue: float = 0.0
    ) -> Dict[str, Any]:
        df = pd.DataFrame(transactions)
        
        if df.empty:
            return {}
        
        df['date'] = pd.to_datetime(df['date'])
        
        category_totals = df.groupby('category')['amount'].sum().to_dict()
        
        deductions = []
        total_deductible = 0.0
        
        for category, amount in category_totals.items():
            rule = BUSINESS_DEDUCTIBLE_RULES.get(category, {})
            
            if rule.get("deductible", False):
                rate = rule.get("rate", 0.0)
                max_ratio = rule.get("max_ratio", 0.0)
                
                deductible_amount = amount * rate
                
                if max_ratio > 0 and annual_revenue > 0:
                    max_deductible = annual_revenue * max_ratio
                    deductible_amount = min(deductible_amount, max_deductible)
                
                deductions.append({
                    'category': category,
                    'total_amount': round(amount, 2),
                    'deductible_amount': round(deductible_amount, 2),
                    'rate': rate,
                    'description': rule.get("description", ""),
                    'eligible': True
                })
                
                total_deductible += deductible_amount
            else:
                deductions.append({
                    'category': category,
                    'total_amount': round(amount, 2),
                    'deductible_amount': 0.0,
                    'rate': 0.0,
                    'description': '不可抵扣',
                    'eligible': False
                })
        
        tax_saved = total_deductible * self.config.tax_rate
        
        return {
            'business_type': business_type,
            'annual_revenue': annual_revenue,
            'category_deductions': deductions,
            'total_deductible': round(total_deductible, 2),
            'tax_saved': round(tax_saved, 2),
            'effective_tax_rate': self.config.tax_rate
        }
    
    def get_deduction_summary(
        self,
        transactions: List[Dict],
        mode: str = "personal"
    ) -> pd.DataFrame:
        if mode == "personal":
            result = self.calculate_personal_deduction(transactions)
        else:
            result = self.calculate_business_deduction(transactions)
        
        if not result:
            return pd.DataFrame()
        
        deductions = result.get('category_deductions', [])
        return pd.DataFrame(deductions)
    
    def get_tax_summary(
        self,
        transactions: List[Dict],
        mode: str = "personal"
    ) -> Dict[str, Any]:
        if mode == "personal":
            return self.calculate_personal_deduction(transactions)
        else:
            return self.calculate_business_deduction(transactions)
