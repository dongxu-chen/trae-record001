import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import uuid


class ContractManager:
    def __init__(self):
        self.contract_statuses = ['草稿', '待审核', '已签署', '执行中', '已完成', '已终止', '违约']
        self.payment_statuses = ['待支付', '部分支付', '已支付', '逾期', '退款中', '已退款']
        self.contract_types = ['单条内容合作', '月度框架合作', '季度框架合作', '年度独家合作', '活动冠名合作']
        self.performance_milestones = ['内容发布', '数据验收', '效果达标', '合同完成']
    
    def generate_contract_id(self) -> str:
        return f"CNT{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def generate_payment_id(self) -> str:
        return f"PAY{datetime.now().strftime('%Y%m%d')}{str(uuid.uuid4())[:8].upper()}"
    
    def create_contract(self, influencer_data: pd.Series, 
                        contract_type: str = '单条内容合作',
                        total_amount: float = 0,
                        start_date: str = None,
                        end_date: str = None,
                        deliverables: List[str] = None,
                        payment_terms: str = '30%预付款，70%验收后支付') -> Dict:
        if start_date is None:
            start_date = datetime.now().strftime('%Y-%m-%d')
        if end_date is None:
            end_date = (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')
        if deliverables is None:
            deliverables = ['1条原创视频内容', '内容包含品牌信息露出', '发布后7天数据报告']
        
        if total_amount == 0:
            total_amount = influencer_data.get('cooperation_price', 10000)
        
        contract_id = self.generate_contract_id()
        
        payment_schedule = self._generate_payment_schedule(total_amount, payment_terms, start_date)
        
        return {
            'contract_id': contract_id,
            'influencer_id': influencer_data['id'],
            'influencer_name': influencer_data['name'],
            'platform': influencer_data['platform'],
            'category': influencer_data['category'],
            'followers': influencer_data['followers'],
            'contract_type': contract_type,
            'total_amount': total_amount,
            'currency': 'CNY',
            'start_date': start_date,
            'end_date': end_date,
            'contract_duration_days': (datetime.strptime(end_date, '%Y-%m-%d') - 
                                      datetime.strptime(start_date, '%Y-%m-%d')).days,
            'deliverables': deliverables,
            'payment_terms': payment_terms,
            'payment_schedule': payment_schedule,
            'status': '草稿',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'signed_at': None,
            'completed_at': None,
            'performance_targets': {
                'min_views': int(influencer_data['followers'] * 0.1),
                'min_engagement_rate': 3.0,
                'min_conversions': int(influencer_data['followers'] * 0.001)
            },
            'kpi_terms': {
                'views_weight': 0.3,
                'engagement_weight': 0.4,
                'conversion_weight': 0.3
            },
            'tags': [influencer_data['category'], influencer_data['platform']],
            'notes': ''
        }
    
    def _generate_payment_schedule(self, total_amount: float, payment_terms: str, 
                                    contract_start_date: str) -> List[Dict]:
        schedule = []
        start_date = datetime.strptime(contract_start_date, '%Y-%m-%d')
        
        if '30%预付款' in payment_terms:
            schedule.append({
                'payment_id': self.generate_payment_id(),
                'payment_type': '预付款',
                'amount': total_amount * 0.3,
                'percentage': 30,
                'due_date': start_date.strftime('%Y-%m-%d'),
                'status': '待支付',
                'paid_at': None
            })
            schedule.append({
                'payment_id': self.generate_payment_id(),
                'payment_type': '尾款',
                'amount': total_amount * 0.7,
                'percentage': 70,
                'due_date': (start_date + timedelta(days=45)).strftime('%Y-%m-%d'),
                'status': '待支付',
                'paid_at': None,
                'milestone': '内容发布并验收通过'
            })
        elif '50%' in payment_terms:
            schedule.append({
                'payment_id': self.generate_payment_id(),
                'payment_type': '首款',
                'amount': total_amount * 0.5,
                'percentage': 50,
                'due_date': start_date.strftime('%Y-%m-%d'),
                'status': '待支付',
                'paid_at': None
            })
            schedule.append({
                'payment_id': self.generate_payment_id(),
                'payment_type': '尾款',
                'amount': total_amount * 0.5,
                'percentage': 50,
                'due_date': (start_date + timedelta(days=30)).strftime('%Y-%m-%d'),
                'status': '待支付',
                'paid_at': None,
                'milestone': '合同完成'
            })
        else:
            schedule.append({
                'payment_id': self.generate_payment_id(),
                'payment_type': '全款',
                'amount': total_amount,
                'percentage': 100,
                'due_date': (start_date + timedelta(days=30)).strftime('%Y-%m-%d'),
                'status': '待支付',
                'paid_at': None,
                'milestone': '内容发布并验收通过'
            })
        
        return schedule
    
    def generate_sample_contracts(self, influencer_df: pd.DataFrame, count: int = 20) -> pd.DataFrame:
        contracts = []
        np.random.seed(42)
        
        for i in range(min(count, len(influencer_df))):
            influencer = influencer_df.iloc[i]
            
            contract_type = np.random.choice(self.contract_types)
            status = np.random.choice(self.contract_statuses, p=[0.1, 0.1, 0.15, 0.35, 0.2, 0.05, 0.05])
            
            days_ago = np.random.randint(1, 180)
            start_date = (datetime.now() - timedelta(days=days_ago)).strftime('%Y-%m-%d')
            duration = np.random.choice([15, 30, 60, 90, 180])
            end_date = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=duration)).strftime('%Y-%m-%d')
            
            contract = self.create_contract(
                influencer,
                contract_type=contract_type,
                start_date=start_date,
                end_date=end_date
            )
            contract['status'] = status
            
            if status in ['已签署', '执行中', '已完成']:
                contract['signed_at'] = (datetime.strptime(start_date, '%Y-%m-%d') - timedelta(days=3)).strftime('%Y-%m-%d')
            
            if status == '已完成':
                contract['completed_at'] = end_date
            
            for payment in contract['payment_schedule']:
                if status in ['执行中', '已完成']:
                    if payment['payment_type'] in ['预付款', '首款']:
                        payment['status'] = '已支付'
                        payment['paid_at'] = (datetime.strptime(start_date, '%Y-%m-%d') + timedelta(days=2)).strftime('%Y-%m-%d')
                if status == '已完成':
                    payment['status'] = '已支付'
                    payment['paid_at'] = (datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=5)).strftime('%Y-%m-%d')
            
            contracts.append(contract)
        
        return pd.DataFrame(contracts)
    
    def get_contract_summary(self, contracts_df: pd.DataFrame) -> Dict:
        total_contracts = len(contracts_df)
        total_amount = contracts_df['total_amount'].sum()
        
        status_breakdown = contracts_df.groupby('status').agg({
            'contract_id': 'count',
            'total_amount': 'sum'
        }).reset_index()
        status_breakdown.columns = ['状态', '合同数量', '合同金额']
        
        type_breakdown = contracts_df.groupby('contract_type').agg({
            'contract_id': 'count',
            'total_amount': 'sum'
        }).sort_values('total_amount', ascending=False).reset_index()
        type_breakdown.columns = ['合同类型', '合同数量', '合同金额']
        
        total_paid = 0
        total_pending = 0
        for _, contract in contracts_df.iterrows():
            for payment in contract['payment_schedule']:
                if payment['status'] == '已支付':
                    total_paid += payment['amount']
                else:
                    total_pending += payment['amount']
        
        active_contracts = contracts_df[contracts_df['status'] == '执行中']
        
        return {
            'total_contracts': total_contracts,
            'total_contract_value': total_amount,
            'total_paid_amount': total_paid,
            'total_pending_amount': total_pending,
            'payment_completion_rate': round(total_paid / total_amount * 100 if total_amount > 0 else 0, 1),
            'active_contracts_count': len(active_contracts),
            'avg_contract_value': round(total_amount / total_contracts, 2) if total_contracts > 0 else 0,
            'status_breakdown': status_breakdown.to_dict('records'),
            'type_breakdown': type_breakdown.to_dict('records')
        }
    
    def get_payment_tracking(self, contracts_df: pd.DataFrame) -> pd.DataFrame:
        payment_records = []
        
        for _, contract in contracts_df.iterrows():
            for payment in contract['payment_schedule']:
                payment_records.append({
                    'payment_id': payment['payment_id'],
                    'contract_id': contract['contract_id'],
                    'influencer_name': contract['influencer_name'],
                    'payment_type': payment['payment_type'],
                    'amount': payment['amount'],
                    'percentage': payment['percentage'],
                    'due_date': payment['due_date'],
                    'status': payment['status'],
                    'paid_at': payment.get('paid_at'),
                    'milestone': payment.get('milestone', ''),
                    'is_overdue': self._check_overdue(payment['due_date'], payment['status'])
                })
        
        return pd.DataFrame(payment_records)
    
    def _check_overdue(self, due_date: str, status: str) -> bool:
        if status == '已支付':
            return False
        try:
            due = datetime.strptime(due_date, '%Y-%m-%d')
            return due < datetime.now()
        except:
            return False
    
    def track_performance(self, contract: Dict, actual_data: Dict = None) -> Dict:
        targets = contract['performance_targets']
        kpi_weights = contract['kpi_terms']
        
        if actual_data is None:
            np.random.seed(hash(contract['contract_id']) % 10000)
            actual_data = {
                'actual_views': int(targets['min_views'] * np.random.uniform(0.5, 2.0)),
                'actual_engagement_rate': round(targets['min_engagement_rate'] * np.random.uniform(0.6, 1.5), 2),
                'actual_conversions': int(targets['min_conversions'] * np.random.uniform(0.4, 1.8))
            }
        
        views_score = min(actual_data['actual_views'] / targets['min_views'] * 100, 150)
        engagement_score = min(actual_data['actual_engagement_rate'] / targets['min_engagement_rate'] * 100, 150)
        conversion_score = min(actual_data['actual_conversions'] / targets['min_conversions'] * 100, 150)
        
        overall_score = (
            views_score * kpi_weights['views_weight'] +
            engagement_score * kpi_weights['engagement_weight'] +
            conversion_score * kpi_weights['conversion_weight']
        )
        
        performance_level = 'S - 超额完成' if overall_score >= 120 else \
                          'A - 优秀' if overall_score >= 100 else \
                          'B - 达标' if overall_score >= 80 else \
                          'C - 待改进' if overall_score >= 60 else 'D - 未达标'
        
        bonus_eligibility = overall_score >= 100
        bonus_amount = contract['total_amount'] * 0.1 if overall_score >= 120 else \
                       contract['total_amount'] * 0.05 if overall_score >= 100 else 0
        
        return {
            'contract_id': contract['contract_id'],
            'influencer_name': contract['influencer_name'],
            'targets': targets,
            'actual_data': actual_data,
            'scores': {
                'views_score': round(views_score, 1),
                'engagement_score': round(engagement_score, 1),
                'conversion_score': round(conversion_score, 1),
                'overall_score': round(overall_score, 1)
            },
            'performance_level': performance_level,
            'bonus_eligibility': bonus_eligibility,
            'bonus_amount': bonus_amount,
            'kpi_met': overall_score >= 80,
            'recommendations': self._get_performance_recommendations(overall_score, actual_data, targets)
        }
    
    def _get_performance_recommendations(self, overall_score: float, 
                                          actual_data: Dict, targets: Dict) -> List[str]:
        recommendations = []
        
        if overall_score >= 120:
            recommendations.append('效果远超预期，建议考虑长期合作')
            recommendations.append('可探讨升级为框架合作或独家合作')
            recommendations.append('可作为标杆案例进行内部复盘')
        elif overall_score >= 100:
            recommendations.append('效果达标且表现优秀')
            recommendations.append('建议继续保持合作关系')
        elif overall_score >= 80:
            recommendations.append('基本达成KPI目标')
            recommendations.append('可优化内容方向进一步提升效果')
        elif overall_score >= 60:
            recommendations.append('效果未达预期，需分析原因')
            recommendations.append('建议调整合作策略或内容形式')
        else:
            recommendations.append('效果严重不达标，建议暂停合作')
            recommendations.append('需深入分析失败原因，避免重复踩坑')
        
        if actual_data['actual_views'] < targets['min_views']:
            recommendations.append('触达量不足，建议评估网红粉丝质量或增加投放时长')
        
        if actual_data['actual_engagement_rate'] < targets['min_engagement_rate']:
            recommendations.append('互动率偏低，建议优化内容创意和互动引导')
        
        if actual_data['actual_conversions'] < targets['min_conversions']:
            recommendations.append('转化效果不佳，建议优化转化路径或产品匹配度')
        
        return recommendations
    
    def get_contract_details(self, contract: Dict, influencer_df: pd.DataFrame = None) -> Dict:
        influencer_data = None
        if influencer_df is not None:
            influencer_match = influencer_df[influencer_df['id'] == contract['influencer_id']]
            if len(influencer_match) > 0:
                influencer_data = influencer_match.iloc[0]
        
        performance_tracking = self.track_performance(contract)
        
        payment_summary = {
            'total_amount': contract['total_amount'],
            'paid_amount': sum(p['amount'] for p in contract['payment_schedule'] if p['status'] == '已支付'),
            'pending_amount': sum(p['amount'] for p in contract['payment_schedule'] if p['status'] != '已支付'),
            'payment_count': len(contract['payment_schedule']),
            'paid_count': sum(1 for p in contract['payment_schedule'] if p['status'] == '已支付')
        }
        payment_summary['payment_progress'] = round(
            payment_summary['paid_amount'] / payment_summary['total_amount'] * 100 
            if payment_summary['total_amount'] > 0 else 0, 1
        )
        
        days_remaining = 0
        if contract['end_date']:
            end_date = datetime.strptime(contract['end_date'], '%Y-%m-%d')
            days_remaining = (end_date - datetime.now()).days
        
        return {
            'basic_info': {
                'contract_id': contract['contract_id'],
                'contract_type': contract['contract_type'],
                'status': contract['status'],
                'created_at': contract['created_at'],
                'signed_at': contract['signed_at'],
                'start_date': contract['start_date'],
                'end_date': contract['end_date'],
                'days_remaining': max(days_remaining, 0),
                'duration_days': contract['contract_duration_days']
            },
            'influencer_info': influencer_data,
            'financial_summary': payment_summary,
            'payment_schedule': contract['payment_schedule'],
            'deliverables': contract['deliverables'],
            'performance_tracking': performance_tracking,
            'milestones': self._generate_milestones(contract)
        }
    
    def _generate_milestones(self, contract: Dict) -> List[Dict]:
        milestones = []
        start_date = datetime.strptime(contract['start_date'], '%Y-%m-%d')
        
        milestone_definitions = [
            ('合同签署', -3, 'contract_signed'),
            ('内容创作', 7, 'content_creation'),
            ('内容审核确认', 14, 'content_approved'),
            ('内容发布', 21, 'content_published'),
            ('数据验收', 28, 'data_verified'),
            ('合同完成', contract['contract_duration_days'], 'contract_completed')
        ]
        
        for name, days_offset, key in milestone_definitions:
            milestone_date = start_date + timedelta(days=days_offset)
            status = '已完成' if milestone_date <= datetime.now() else \
                     '进行中' if (milestone_date - datetime.now()).days <= 7 else '待开始'
            
            milestones.append({
                'name': name,
                'key': key,
                'date': milestone_date.strftime('%Y-%m-%d'),
                'status': status,
                'is_overdue': milestone_date < datetime.now() and status != '已完成'
            })
        
        return milestones
    
    def get_aging_report(self, contracts_df: pd.DataFrame) -> Dict:
        payment_df = self.get_payment_tracking(contracts_df)
        
        overdue_payments = payment_df[payment_df['is_overdue']]
        pending_payments = payment_df[payment_df['status'] == '待支付']
        
        aging_buckets = {
            '0-30天逾期': 0,
            '31-60天逾期': 0,
            '61-90天逾期': 0,
            '90天以上逾期': 0
        }
        
        today = datetime.now()
        for _, payment in overdue_payments.iterrows():
            due_date = datetime.strptime(payment['due_date'], '%Y-%m-%d')
            days_overdue = (today - due_date).days
            
            if days_overdue <= 30:
                aging_buckets['0-30天逾期'] += payment['amount']
            elif days_overdue <= 60:
                aging_buckets['31-60天逾期'] += payment['amount']
            elif days_overdue <= 90:
                aging_buckets['61-90天逾期'] += payment['amount']
            else:
                aging_buckets['90天以上逾期'] += payment['amount']
        
        return {
            'total_outstanding': pending_payments['amount'].sum(),
            'total_overdue': overdue_payments['amount'].sum(),
            'overdue_count': len(overdue_payments),
            'aging_buckets': aging_buckets,
            'overdue_details': overdue_payments.to_dict('records')
        }
    
    def get_monthly_spending_forecast(self, contracts_df: pd.DataFrame, 
                                       months: int = 6) -> pd.DataFrame:
        forecast = []
        today = datetime.now()
        
        for i in range(months):
            month_date = today + timedelta(days=i * 30)
            month_str = month_date.strftime('%Y-%m')
            
            month_payments = 0
            contract_count = 0
            
            for _, contract in contracts_df.iterrows():
                for payment in contract['payment_schedule']:
                    if payment['due_date'].startswith(month_str) and payment['status'] != '已支付':
                        month_payments += payment['amount']
                        contract_count += 1
            
            forecast.append({
                '月份': month_str,
                '预计支付笔数': contract_count,
                '预计支付金额': month_payments
            })
        
        return pd.DataFrame(forecast)
