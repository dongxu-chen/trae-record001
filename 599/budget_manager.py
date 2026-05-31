import json
import os
import pandas as pd
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from collections import defaultdict

DEFAULT_BUDGETS = {
    "餐饮": 2000,
    "交通": 1000,
    "购物": 3000,
    "娱乐": 1500,
    "医疗": 500,
    "其他": 500
}

@dataclass
class Budget:
    category: str
    monthly_budget: float
    period: str = "monthly"
    warning_threshold: float = 0.80
    critical_threshold: float = 0.95
    start_date: Optional[str] = None
    notes: str = ""

@dataclass
class BudgetAlert:
    category: str
    current_spending: float
    budget: float
    ratio: float
    alert_level: str
    message: str
    remaining_days: int
    remaining_budget: float
    daily_allowed: float
    projected_spending: float

class BudgetManager:
    def __init__(self, data_path: str = "data/budgets.json"):
        self.data_path = data_path
        self.budgets: Dict[str, Budget] = {}
        self._load_budgets()
    
    def _load_budgets(self):
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for cat, budget_data in data.items():
                        self.budgets[cat] = Budget(**budget_data)
            except Exception:
                self._init_default_budgets()
        else:
            self._init_default_budgets()
    
    def _init_default_budgets(self):
        for category, amount in DEFAULT_BUDGETS.items():
            self.budgets[category] = Budget(
                category=category,
                monthly_budget=amount
            )
        self._save_budgets()
    
    def _save_budgets(self):
        os.makedirs(os.path.dirname(self.data_path), exist_ok=True)
        data = {cat: asdict(budget) for cat, budget in self.budgets.items()}
        with open(self.data_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def set_budget(self, category: str, amount: float, **kwargs):
        if category in self.budgets:
            self.budgets[category].monthly_budget = amount
            for key, value in kwargs.items():
                if hasattr(self.budgets[category], key):
                    setattr(self.budgets[category], key, value)
        else:
            self.budgets[category] = Budget(
                category=category,
                monthly_budget=amount,
                **kwargs
            )
        self._save_budgets()
    
    def get_budget(self, category: str) -> Optional[Budget]:
        return self.budgets.get(category)
    
    def get_all_budgets(self) -> Dict[str, Budget]:
        return self.budgets
    
    def delete_budget(self, category: str):
        if category in self.budgets:
            del self.budgets[category]
            self._save_budgets()
    
    def calculate_period_spending(
        self,
        transactions: List[Dict],
        period: str = "current_month"
    ) -> Dict[str, float]:
        df = pd.DataFrame(transactions)
        if df.empty:
            return {}
        
        df['date'] = pd.to_datetime(df['date'])
        now = datetime.now()
        
        if period == "current_month":
            start_date = now.replace(day=1)
            df_period = df[df['date'] >= start_date]
        elif period == "last_month":
            last_month = now.replace(day=1) - timedelta(days=1)
            start_date = last_month.replace(day=1)
            end_date = last_month.replace(day=28) + timedelta(days=4)
            end_date = end_date - timedelta(days=end_date.day)
            df_period = df[(df['date'] >= start_date) & (df['date'] <= end_date)]
        elif period == "current_quarter":
            quarter = (now.month - 1) // 3 + 1
            start_month = (quarter - 1) * 3 + 1
            start_date = now.replace(month=start_month, day=1)
            df_period = df[df['date'] >= start_date]
        elif period == "current_year":
            start_date = now.replace(month=1, day=1)
            df_period = df[df['date'] >= start_date]
        else:
            df_period = df
        
        category_spending = df_period.groupby('category')['amount'].sum().to_dict()
        return category_spending
    
    def get_daily_average(
        self,
        transactions: List[Dict],
        category: str,
        days: int = 30
    ) -> float:
        df = pd.DataFrame(transactions)
        if df.empty:
            return 0.0
        
        df['date'] = pd.to_datetime(df['date'])
        cutoff = datetime.now() - timedelta(days=days)
        df_filtered = df[(df['category'] == category) & (df['date'] >= cutoff)]
        
        if df_filtered.empty:
            return 0.0
        
        return df_filtered['amount'].sum() / days
    
    def check_budget_alerts(
        self,
        transactions: List[Dict],
        period: str = "current_month"
    ) -> List[BudgetAlert]:
        spending = self.calculate_period_spending(transactions, period)
        alerts = []
        
        now = datetime.now()
        if period == "current_month":
            days_in_month = (now.replace(month=now.month % 12 + 1, day=1) - timedelta(days=1)).day
            remaining_days = days_in_month - now.day + 1
            days_passed = now.day
        else:
            remaining_days = 0
            days_passed = 30
        
        for category, budget in self.budgets.items():
            current_spending = spending.get(category, 0.0)
            budget_amount = budget.monthly_budget
            
            if budget_amount <= 0:
                continue
            
            ratio = current_spending / budget_amount
            remaining_budget = max(0, budget_amount - current_spending)
            daily_allowed = remaining_budget / remaining_days if remaining_days > 0 else 0
            
            daily_avg = self.get_daily_average(transactions, category)
            projected_spending = current_spending + daily_avg * remaining_days
            
            if ratio >= budget.critical_threshold:
                alert_level = "critical"
                message = f"【严重警告】{category}消费已达预算的{ratio:.1%}，即将超支！"
            elif ratio >= budget.warning_threshold:
                alert_level = "warning"
                message = f"【提醒】{category}消费已达预算的{ratio:.1%}，请注意控制。"
            elif projected_spending > budget_amount:
                alert_level = "warning"
                message = f"【提醒】按当前趋势，{category}预计超支¥{projected_spending - budget_amount:.2f}"
            else:
                continue
            
            alerts.append(BudgetAlert(
                category=category,
                current_spending=round(current_spending, 2),
                budget=budget_amount,
                ratio=round(ratio, 4),
                alert_level=alert_level,
                message=message,
                remaining_days=remaining_days,
                remaining_budget=round(remaining_budget, 2),
                daily_allowed=round(daily_allowed, 2),
                projected_spending=round(projected_spending, 2)
            ))
        
        alerts.sort(key=lambda x: x.ratio, reverse=True)
        return alerts
    
    def get_budget_summary(
        self,
        transactions: List[Dict],
        period: str = "current_month"
    ) -> pd.DataFrame:
        spending = self.calculate_period_spending(transactions, period)
        
        data = []
        for category, budget in self.budgets.items():
            current_spending = spending.get(category, 0.0)
            budget_amount = budget.monthly_budget
            ratio = current_spending / budget_amount if budget_amount > 0 else 0
            remaining = max(0, budget_amount - current_spending)
            
            if ratio >= budget.critical_threshold:
                status = "严重超支"
            elif ratio >= budget.warning_threshold:
                status = "即将超支"
            elif ratio >= 0.5:
                status = "正常消费"
            else:
                status = "消费较少"
            
            data.append({
                '类别': category,
                '预算金额': round(budget_amount, 2),
                '已消费': round(current_spending, 2),
                '剩余预算': round(remaining, 2),
                '完成比例': round(ratio * 100, 2),
                '状态': status
            })
        
        return pd.DataFrame(data)
    
    def get_budget_vs_actual(
        self,
        transactions: List[Dict],
        months: int = 6
    ) -> pd.DataFrame:
        df = pd.DataFrame(transactions)
        if df.empty:
            return pd.DataFrame()
        
        df['date'] = pd.to_datetime(df['date'])
        
        end_date = datetime.now().replace(day=1)
        start_date = end_date - timedelta(days=30 * months)
        
        df_filtered = df[(df['date'] >= start_date) & (df['date'] < end_date)].copy()
        
        df_filtered.loc[:, 'year_month'] = df_filtered['date'].dt.to_period('M')
        
        monthly_spending = df_filtered.groupby(['year_month', 'category'])['amount'].sum().unstack(fill_value=0)
        
        data = []
        for period in monthly_spending.index:
            period_str = str(period)
            for category in self.budgets.keys():
                budget_amount = self.budgets[category].monthly_budget
                actual_spending = monthly_spending.loc[period, category] if category in monthly_spending.columns else 0
                
                data.append({
                    '月份': period_str,
                    '类别': category,
                    '预算': budget_amount,
                    '实际': round(actual_spending, 2),
                    '差额': round(actual_spending - budget_amount, 2),
                    '完成率': round(actual_spending / budget_amount * 100, 2) if budget_amount > 0 else 0
                })
        
        return pd.DataFrame(data)
    
    def suggest_budget_adjustment(
        self,
        transactions: List[Dict],
        months: int = 3
    ) -> List[Dict]:
        df = pd.DataFrame(transactions)
        if df.empty:
            return []
        
        df['date'] = pd.to_datetime(df['date'])
        
        end_date = datetime.now().replace(day=1)
        start_date = end_date - timedelta(days=30 * months)
        
        df_filtered = df[(df['date'] >= start_date) & (df['date'] < end_date)].copy()
        
        df_filtered.loc[:, 'year_month'] = df_filtered['date'].dt.to_period('M')
        
        suggestions = []
        for category, budget in self.budgets.items():
            cat_data = df_filtered[df_filtered['category'] == category]
            
            if cat_data.empty:
                continue
            
            monthly_avg = cat_data.groupby('year_month')['amount'].sum().mean()
            current_budget = budget.monthly_budget
            
            if current_budget <= 0:
                continue
            
            diff_ratio = (monthly_avg - current_budget) / current_budget
            
            if abs(diff_ratio) > 0.2:
                if diff_ratio > 0:
                    suggestion = "建议上调预算"
                    new_budget = round(monthly_avg * 1.1, 0)
                else:
                    suggestion = "可考虑下调预算"
                    new_budget = round(monthly_avg * 0.9, 0)
                
                suggestions.append({
                    'category': category,
                    'current_budget': current_budget,
                    'monthly_average': round(monthly_avg, 2),
                    'deviation': round(diff_ratio * 100, 2),
                    'suggestion': suggestion,
                    'recommended_budget': new_budget
                })
        
        suggestions.sort(key=lambda x: abs(x['deviation']), reverse=True)
        return suggestions
