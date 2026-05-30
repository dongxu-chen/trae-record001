import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')


class ReferralAnalyzer:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
    
    def run_full_analysis(self, data_dict, loyalty_results=None):
        referrals_df = data_dict.get('referrals')
        if referrals_df is None or len(referrals_df) == 0:
            return self._empty_results()
        
        results = {
            'referral_overview': self._analyze_overview(referrals_df),
            'referrer_analysis': self._analyze_referrers(referrals_df),
            'conversion_analysis': self._analyze_conversion(referrals_df),
            'channel_effectiveness': self._analyze_channels(referrals_df),
            'referred_customer_value': self._analyze_referred_value(referrals_df),
            'referral_prediction': self._predict_referral_potential(data_dict, referrals_df),
            'viral_coefficient': self._calculate_viral_coefficient(referrals_df, data_dict),
            'optimization_strategies': self._generate_optimization_strategies(referrals_df)
        }
        
        if loyalty_results and 'metrics_with_index' in loyalty_results:
            results['loyalty_referral_correlation'] = self._analyze_loyalty_correlation(
                referrals_df, loyalty_results['metrics_with_index']
            )
        
        return results
    
    def _empty_results(self):
        return {
            'referral_overview': {'total_referrals': 0},
            'referrer_analysis': {},
            'conversion_analysis': {},
            'channel_effectiveness': {},
            'referred_customer_value': {},
            'referral_prediction': {},
            'viral_coefficient': {},
            'optimization_strategies': []
        }
    
    def _analyze_overview(self, referrals_df):
        total_referrals = len(referrals_df)
        unique_referrers = referrals_df['referrer_id'].nunique()
        conversion_rate = referrals_df['is_converted'].mean()
        active_referred = referrals_df[referrals_df['is_converted'] == True]['referred_still_active'].mean() if referrals_df['is_converted'].sum() > 0 else 0
        
        converted = referrals_df[referrals_df['is_converted'] == True]
        
        return {
            'total_referrals': total_referrals,
            'unique_referrers': unique_referrers,
            'avg_referrals_per_referrer': total_referrals / max(unique_referrers, 1),
            'conversion_rate': conversion_rate,
            'active_referred_rate': active_referred,
            'avg_referred_spend': converted['referred_first_spend'].mean() if len(converted) > 0 else 0,
            'avg_referred_frequency': converted['referred_frequency'].mean() if len(converted) > 0 else 0,
            'total_referred_revenue': converted['referred_first_spend'].sum() if len(converted) > 0 else 0
        }
    
    def _analyze_referrers(self, referrals_df):
        referrer_stats = referrals_df.groupby('referrer_id').agg(
            total_referrals=('referred_customer_id', 'count'),
            conversions=('is_converted', 'sum'),
            avg_referred_spend=('referred_first_spend', 'mean'),
            avg_referred_active=('referred_still_active', 'mean')
        ).reset_index()
        
        referrer_stats['conversion_rate'] = referrer_stats['conversions'] / referrer_stats['total_referrals']
        
        top_referrers = referrer_stats.nlargest(10, 'conversions')
        
        referrer_by_loyalty = referrals_df.groupby(
            pd.cut(referrals_df['referrer_loyalty_tendency'], bins=[0, 0.33, 0.66, 1], labels=['low', 'medium', 'high'])
        ).agg(
            referrer_count=('referrer_id', 'nunique'),
            avg_referrals=('referred_customer_id', 'count'),
            conversion_rate=('is_converted', 'mean'),
            avg_referred_spend=('referred_first_spend', 'mean')
        )
        
        loyalty_tendency_groups = referrals_df.groupby('referrer_loyalty_tendency_bin' if 'referrer_loyalty_tendency_bin' in referrals_df.columns else pd.cut(referrals_df['referrer_loyalty_tendency'], bins=[0, 0.33, 0.66, 1], labels=['low', 'medium', 'high']))
        
        return {
            'top_referrers': top_referrers.to_dict('records'),
            'referrer_by_loyalty': referrer_by_loyalty.to_dict('index') if len(referrer_by_loyalty) > 0 else {},
            'avg_referrals_per_user': float(referrer_stats['total_referrals'].mean()),
            'conversion_rate_by_loyalty': {
                str(tier): float(group['is_converted'].mean())
                for tier, group in loyalty_tendency_groups
            },
            'super_referrer_threshold': float(referrer_stats['total_referrals'].quantile(0.9)),
            'super_referrer_count': int((referrer_stats['total_referrals'] >= referrer_stats['total_referrals'].quantile(0.9)).sum())
        }
    
    def _analyze_conversion(self, referrals_df):
        converted = referrals_df[referrals_df['is_converted'] == True]
        not_converted = referrals_df[referrals_df['is_converted'] == False]
        
        conversion_by_channel = referrals_df.groupby('referral_channel')['is_converted'].mean().to_dict()
        
        conversion_by_segment = referrals_df.groupby('referrer_segment')['is_converted'].mean().to_dict()
        
        still_active_rate = converted['referred_still_active'].mean() if len(converted) > 0 else 0
        
        time_to_convert = None
        if len(converted) > 0 and 'converted_date' in converted.columns and 'referral_date' in converted.columns:
            converted_clean = converted.dropna(subset=['converted_date', 'referral_date'])
            if len(converted_clean) > 0:
                converted_clean = converted_clean.copy()
                converted_clean['days_to_convert'] = (
                    pd.to_datetime(converted_clean['converted_date']) - 
                    pd.to_datetime(converted_clean['referral_date'])
                ).dt.days
                time_to_convert = float(converted_clean['days_to_convert'].mean())
        
        return {
            'overall_conversion_rate': referrals_df['is_converted'].mean(),
            'conversion_by_channel': conversion_by_channel,
            'conversion_by_segment': conversion_by_segment,
            'still_active_rate': still_active_rate,
            'avg_days_to_convert': time_to_convert,
            'converted_avg_spend': float(converted['referred_first_spend'].mean()) if len(converted) > 0 else 0,
            'not_converted_count': len(not_converted)
        }
    
    def _analyze_channels(self, referrals_df):
        channel_stats = referrals_df.groupby('referral_channel').agg(
            total_referrals=('referred_customer_id', 'count'),
            conversion_rate=('is_converted', 'mean'),
            avg_referred_spend=('referred_first_spend', 'mean'),
            avg_referred_frequency=('referred_frequency', 'mean'),
            active_rate=('referred_still_active', 'mean')
        ).reset_index()
        
        channel_stats['revenue_per_referral'] = (
            channel_stats['conversion_rate'] * channel_stats['avg_referred_spend']
        )
        
        channel_stats = channel_stats.sort_values('revenue_per_referral', ascending=False)
        
        best_channel = channel_stats.iloc[0]['referral_channel'] if len(channel_stats) > 0 else 'N/A'
        best_conversion_channel = channel_stats.sort_values('conversion_rate', ascending=False).iloc[0]['referral_channel'] if len(channel_stats) > 0 else 'N/A'
        
        return {
            'channel_stats': channel_stats.to_dict('records'),
            'best_channel_by_revenue': best_channel,
            'best_channel_by_conversion': best_conversion_channel,
            'channel_recommendation': {
                'primary': best_channel,
                'secondary': channel_stats.iloc[1]['referral_channel'] if len(channel_stats) > 1 else 'N/A'
            }
        }
    
    def _analyze_referred_value(self, referrals_df):
        converted = referrals_df[referrals_df['is_converted'] == True]
        
        if len(converted) == 0:
            return {'avg_customer_value': 0, 'total_value': 0}
        
        active_referred = converted[converted['referred_still_active'] == True]
        churned_referred = converted[converted['referred_still_active'] == False]
        
        return {
            'avg_first_spend': float(converted['referred_first_spend'].mean()),
            'avg_frequency': float(converted['referred_frequency'].mean()),
            'avg_customer_value': float(converted['referred_first_spend'].mean() * converted['referred_frequency'].mean()),
            'total_referred_revenue': float(converted['referred_first_spend'].sum()),
            'active_referred_value': float(active_referred['referred_first_spend'].mean()) if len(active_referred) > 0 else 0,
            'churned_referred_value': float(churned_referred['referred_first_spend'].mean()) if len(churned_referred) > 0 else 0,
            'active_vs_churned_ratio': float(len(active_referred) / max(len(churned_referred), 1)),
            'retention_rate': float(converted['referred_still_active'].mean())
        }
    
    def _predict_referral_potential(self, data_dict, referrals_df):
        profiles = data_dict.get('profiles')
        if profiles is None:
            return {}
        
        referrer_ids = set(referrals_df['referrer_id'].unique())
        profiles = profiles.copy()
        profiles['is_referrer'] = profiles['customer_id'].isin(referrer_ids).astype(int)
        
        referrer_referrals = referrals_df.groupby('referrer_id').size().reset_index(name='n_referrals')
        referrer_referrals.columns = ['customer_id', 'n_referrals']
        profiles = profiles.merge(referrer_referrals, on='customer_id', how='left')
        profiles['n_referrals'] = profiles['n_referrals'].fillna(0)
        
        feature_cols = ['age', 'loyalty_tendency', 'price_sensitivity', 'promotion_responsiveness']
        X = profiles[feature_cols].values
        y = profiles['n_referrals'].values
        
        X_scaled = self.scaler.fit_transform(X)
        
        try:
            self.model = GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=3)
            self.model.fit(X_scaled, y)
            
            potential_scores = self.model.predict(X_scaled)
            profiles['referral_potential'] = np.clip(potential_scores, 0, None)
            
            top_potential = profiles[profiles['is_referrer'] == 0].nlargest(20, 'referral_potential')
            
            feature_importance = pd.DataFrame({
                'feature': feature_cols,
                'importance': self.model.feature_importances_
            }).sort_values('importance', ascending=False)
            
            return {
                'top_potential_referrers': top_potential[['customer_id', 'referral_potential']].to_dict('records'),
                'potential_distribution': {
                    'high_potential': int((profiles['referral_potential'] >= 1.5).sum()),
                    'medium_potential': int(((profiles['referral_potential'] >= 0.5) & (profiles['referral_potential'] < 1.5)).sum()),
                    'low_potential': int((profiles['referral_potential'] < 0.5).sum())
                },
                'feature_importance': feature_importance.to_dict('records'),
                'current_referrer_pct': float(profiles['is_referrer'].mean() * 100),
                'potential_referrer_pct': float((profiles['referral_potential'] >= 1).mean() * 100)
            }
        except Exception:
            return {
                'top_potential_referrers': [],
                'potential_distribution': {},
                'current_referrer_pct': float(profiles['is_referrer'].mean() * 100)
            }
    
    def _calculate_viral_coefficient(self, referrals_df, data_dict):
        total_customers = data_dict.get('profiles', pd.DataFrame()).shape[0]
        if total_customers == 0:
            return {'viral_coefficient': 0}
        
        unique_referrers = referrals_df['referrer_id'].nunique()
        total_referrals = len(referrals_df)
        conversions = referrals_df['is_converted'].sum()
        
        invites_per_user = total_referrals / max(unique_referrers, 1)
        conversion_rate = conversions / max(total_referrals, 1)
        
        viral_coefficient = invites_per_user * conversion_rate
        
        active_converted = referrals_df[
            (referrals_df['is_converted'] == True) & (referrals_df['referred_still_active'] == True)
        ]
        
        effective_conversion = len(active_converted) / max(total_referrals, 1)
        effective_viral = invites_per_user * effective_conversion
        
        return {
            'viral_coefficient': float(viral_coefficient),
            'effective_viral_coefficient': float(effective_viral),
            'invites_per_user': float(invites_per_user),
            'conversion_rate': float(conversion_rate),
            'effective_conversion_rate': float(effective_conversion),
            'interpretation': '增长型' if viral_coefficient > 1 else ('稳定型' if viral_coefficient > 0.5 else '需改善'),
            'growth_potential': '高' if effective_viral > 0.3 else ('中' if effective_viral > 0.1 else '低')
        }
    
    def _analyze_loyalty_correlation(self, referrals_df, loyalty_metrics):
        if 'customer_id' not in loyalty_metrics.columns:
            return {}
        
        referrer_loyalty = referrals_df.merge(
            loyalty_metrics[['customer_id', 'loyalty_index']].rename(columns={'customer_id': 'referrer_id', 'loyalty_index': 'referrer_loyalty_index'}),
            on='referrer_id', how='left'
        )
        
        if len(referrer_loyalty) == 0 or referrer_loyalty['referrer_loyalty_index'].isna().all():
            return {}
        
        corr = referrer_loyalty[['referrer_loyalty_index', 'is_converted']].corr().iloc[0, 1]
        
        high_loyalty_referrers = referrer_loyalty[referrer_loyalty['referrer_loyalty_index'] >= 70]
        low_loyalty_referrers = referrer_loyalty[referrer_loyalty['referrer_loyalty_index'] < 40]
        
        return {
            'loyalty_conversion_correlation': float(corr),
            'high_loyalty_conversion_rate': float(high_loyalty_referrers['is_converted'].mean()) if len(high_loyalty_referrers) > 0 else 0,
            'low_loyalty_conversion_rate': float(low_loyalty_referrers['is_converted'].mean()) if len(low_loyalty_referrers) > 0 else 0,
            'avg_referrer_loyalty_index': float(referrer_loyalty['referrer_loyalty_index'].mean())
        }
    
    def _generate_optimization_strategies(self, referrals_df):
        strategies = []
        
        conversion_rate = referrals_df['is_converted'].mean()
        if conversion_rate < 0.5:
            strategies.append({
                'priority': 'high',
                'category': 'conversion',
                'strategy': '优化推荐转化路径，缩短新客首次购买决策时间',
                'rationale': f'当前推荐转化率为{conversion_rate:.1%}，低于50%的行业基准',
                'expected_impact': '预计可将转化率提升10-15个百分点',
                'target_segment': '所有推荐人'
            })
        
        channel_stats = referrals_df.groupby('referral_channel')['is_converted'].mean()
        if len(channel_stats) > 0:
            best_channel = channel_stats.idxmax()
            worst_channel = channel_stats.idxmin()
            strategies.append({
                'priority': 'medium',
                'category': 'channel',
                'strategy': f'重点发展{best_channel}渠道，优化{worst_channel}渠道体验',
                'rationale': f'{best_channel}转化率最高({channel_stats[best_channel]:.1%})，{worst_channel}最低({channel_stats[worst_channel]:.1%})',
                'expected_impact': '预计提升整体转化率5-10个百分点',
                'target_segment': f'{best_channel}和{worst_channel}用户'
            })
        
        active_rate = referrals_df[referrals_df['is_converted'] == True]['referred_still_active'].mean()
        if active_rate < 0.7:
            strategies.append({
                'priority': 'high',
                'category': 'retention',
                'strategy': '建立被推荐新客专属留存计划，提供首月特殊权益',
                'rationale': f'被推荐新客留存率仅{active_rate:.1%}，需要加强新客培育',
                'expected_impact': '预计提升新客留存率15-25%',
                'target_segment': '被推荐新客户'
            })
        
        unique_referrers = referrals_df['referrer_id'].nunique()
        total_customers = referrals_df['referrer_segment'].nunique()
        strategies.append({
            'priority': 'medium',
            'category': 'expansion',
            'strategy': '设计分层推荐激励体系，激发更多用户参与推荐',
            'rationale': f'当前仅{unique_referrers}位用户参与推荐，扩大推荐人基数是关键',
            'expected_impact': '预计推荐参与率提升50-100%',
            'target_segment': '高忠诚度但未参与推荐的用户'
        })
        
        strategies.append({
            'priority': 'low',
            'category': 'reward',
            'strategy': '实施双向奖励机制（推荐人和被推荐人都有奖励）',
            'rationale': '双向奖励比单向奖励转化率通常高30-50%',
            'expected_impact': '预计提升推荐转化率和参与率',
            'target_segment': '所有活跃用户'
        })
        
        return strategies
