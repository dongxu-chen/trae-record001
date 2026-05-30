import pandas as pd
import numpy as np
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
import warnings
warnings.filterwarnings('ignore')


class LoyaltyPredictor:
    def __init__(self):
        self.trend_model = None
        self.scaler = StandardScaler()
    
    def run_full_analysis(self, data_dict, loyalty_results=None):
        trends_df = data_dict.get('loyalty_trends')
        if trends_df is None or len(trends_df) == 0:
            return self._empty_results()
        
        results = {
            'trend_overview': self._analyze_trend_overview(trends_df),
            'individual_trends': self._analyze_individual_trends(trends_df),
            'loyalty_prediction': self._predict_future_loyalty(trends_df),
            'transition_matrix': self._build_transition_matrix(trends_df),
            'risk_forecast': self._forecast_risk_users(trends_df, loyalty_results),
            'intervention_timing': self._determine_intervention_timing(trends_df)
        }
        
        return results
    
    def _empty_results(self):
        return {
            'trend_overview': {},
            'individual_trends': {},
            'loyalty_prediction': {},
            'transition_matrix': {},
            'risk_forecast': {},
            'intervention_timing': {}
        }
    
    def _analyze_trend_overview(self, trends_df):
        period_avg = trends_df.groupby('period')['loyalty_score'].agg(['mean', 'median', 'std']).reset_index()
        period_avg = period_avg.sort_values('period')
        
        trend_direction_dist = trends_df.groupby('trend_direction')['customer_id'].nunique().to_dict()
        
        total_users = trends_df['customer_id'].nunique()
        
        first_period = trends_df['period'].min()
        last_period = trends_df['period'].max()
        first_scores = trends_df[trends_df['period'] == first_period].groupby('customer_id')['loyalty_score'].first()
        last_scores = trends_df[trends_df['period'] == last_period].groupby('customer_id')['loyalty_score'].first()
        
        score_changes = last_scores - first_scores
        
        improving = (score_changes > 5).sum()
        declining = (score_changes < -5).sum()
        stable = ((score_changes >= -5) & (score_changes <= 5)).sum()
        
        period_trend = {}
        for period in sorted(trends_df['period'].unique()):
            period_data = trends_df[trends_df['period'] == period]
            period_trend[period] = {
                'avg_score': float(period_data['loyalty_score'].mean()),
                'median_score': float(period_data['loyalty_score'].median()),
                'user_count': int(period_data['customer_id'].nunique()),
                'up_trend_pct': float((period_data['trend_direction'] == 'up').mean() * 100),
                'down_trend_pct': float((period_data['trend_direction'] == 'down').mean() * 100)
            }
        
        return {
            'period_trends': period_trend,
            'trend_direction_distribution': {
                'improving': int(improving),
                'declining': int(declining),
                'stable': int(stable),
                'improving_pct': float(improving / total_users * 100),
                'declining_pct': float(declining / total_users * 100),
                'stable_pct': float(stable / total_users * 100)
            },
            'overall_change': {
                'avg_first_period': float(first_scores.mean()),
                'avg_last_period': float(last_scores.mean()),
                'avg_change': float(score_changes.mean()),
                'max_improvement': float(score_changes.max()),
                'max_decline': float(score_changes.min())
            }
        }
    
    def _analyze_individual_trends(self, trends_df):
        def calc_slope(group):
            if len(group) < 2:
                return 0
            x = np.arange(len(group))
            y = group['loyalty_score'].values
            try:
                slope = np.polyfit(x, y, 1)[0]
                return slope
            except Exception:
                return 0
        
        user_slopes = trends_df.groupby('customer_id').apply(calc_slope).reset_index()
        user_slopes.columns = ['customer_id', 'loyalty_slope']
        
        user_latest = trends_df.groupby('customer_id').last().reset_index()
        user_latest = user_latest.merge(user_slopes, on='customer_id')
        
        def classify_trend(row):
            slope = row['loyalty_slope']
            score = row['loyalty_score']
            if slope > 1.5 and score < 60:
                return '快速上升型'
            elif slope > 0.5:
                return '稳步上升型'
            elif slope < -1.5 and score < 50:
                return '快速下降型'
            elif slope < -0.5:
                return '逐步下降型'
            elif score > 70:
                return '高位稳定型'
            else:
                return '低位稳定型'
        
        user_latest['trend_type'] = user_latest.apply(classify_trend, axis=1)
        trend_distribution = user_latest['trend_type'].value_counts().to_dict()
        
        rapidly_declining = user_latest[user_latest['trend_type'] == '快速下降型'].nlargest(10, 'loyalty_slope', keep='last')
        
        rapidly_improving = user_latest[user_latest['trend_type'] == '快速上升型'].nsmallest(10, 'loyalty_slope', keep='last')
        
        return {
            'trend_type_distribution': trend_distribution,
            'rapidly_declining_users': rapidly_declining[['customer_id', 'loyalty_score', 'loyalty_slope']].to_dict('records'),
            'rapidly_improving_users': rapidly_improving[['customer_id', 'loyalty_score', 'loyalty_slope']].to_dict('records'),
            'avg_slope': float(user_slopes['loyalty_slope'].mean()),
            'user_trends_detail': user_latest[['customer_id', 'loyalty_score', 'loyalty_slope', 'trend_type']].copy()
        }
    
    def _predict_future_loyalty(self, trends_df):
        periods = sorted(trends_df['period'].unique())
        
        if len(periods) < 3:
            return {'predictions': {}, 'model_performance': {}}
        
        predictions = []
        
        for customer_id, customer_data in trends_df.groupby('customer_id'):
            customer_data = customer_data.sort_values('period')
            scores = customer_data['loyalty_score'].values
            
            if len(scores) < 3:
                continue
            
            x = np.arange(len(scores))
            try:
                coeffs = np.polyfit(x, scores, 2)
                next_x = np.array([len(scores), len(scores) + 1, len(scores) + 2])
                predicted = np.polyval(coeffs, next_x)
                predicted = np.clip(predicted, 0, 100)
            except Exception:
                last_score = scores[-1]
                predicted = np.array([last_score, last_score, last_score])
            
            predictions.append({
                'customer_id': customer_id,
                'current_score': float(scores[-1]),
                'predicted_1q': float(predicted[0]),
                'predicted_2q': float(predicted[1]),
                'predicted_3q': float(predicted[2]),
                'predicted_change': float(predicted[0] - scores[-1]),
                'trend': 'up' if predicted[0] > scores[-1] + 2 else ('down' if predicted[0] < scores[-1] - 2 else 'stable')
            })
        
        pred_df = pd.DataFrame(predictions)
        
        if len(pred_df) == 0:
            return {'predictions': {}, 'model_performance': {}}
        
        improving = (pred_df['trend'] == 'up').sum()
        declining = (pred_df['trend'] == 'down').sum()
        stable = (pred_df['trend'] == 'stable').sum()
        
        period_avg_predictions = {}
        for i, q_name in enumerate(['next_Q1', 'next_Q2', 'next_Q3']):
            col = f'predicted_{i+1}q'
            period_avg_predictions[q_name] = {
                'avg_predicted_score': float(pred_df[col].mean()),
                'improving_pct': float(improving / len(pred_df) * 100),
                'declining_pct': float(declining / len(pred_df) * 100),
                'stable_pct': float(stable / len(pred_df) * 100)
            }
        
        return {
            'period_predictions': period_avg_predictions,
            'overall_forecast': {
                'avg_current_score': float(pred_df['current_score'].mean()),
                'avg_predicted_next_q': float(pred_df['predicted_1q'].mean()),
                'avg_predicted_change': float(pred_df['predicted_change'].mean()),
                'improving_count': int(improving),
                'declining_count': int(declining),
                'stable_count': int(stable),
                'improving_pct': float(improving / len(pred_df) * 100),
                'declining_pct': float(declining / len(pred_df) * 100)
            },
            'user_predictions': pred_df
        }
    
    def _build_transition_matrix(self, trends_df):
        def score_to_tier(score):
            if score >= 70:
                return '高'
            elif score >= 40:
                return '中'
            else:
                return '低'
        
        transitions = {'高': {'高': 0, '中': 0, '低': 0}, 
                       '中': {'高': 0, '中': 0, '低': 0}, 
                       '低': {'高': 0, '中': 0, '低': 0}}
        
        for customer_id, customer_data in trends_df.groupby('customer_id'):
            customer_data = customer_data.sort_values('period')
            scores = customer_data['loyalty_score'].values
            
            for i in range(len(scores) - 1):
                from_tier = score_to_tier(scores[i])
                to_tier = score_to_tier(scores[i + 1])
                transitions[from_tier][to_tier] += 1
        
        transition_probs = {}
        for from_tier in transitions:
            total = sum(transitions[from_tier].values())
            if total > 0:
                transition_probs[from_tier] = {
                    to_tier: transitions[from_tier][to_tier] / total
                    for to_tier in transitions[from_tier]
                }
            else:
                transition_probs[from_tier] = {to_tier: 0 for to_tier in transitions[from_tier]}
        
        return {
            'transition_counts': transitions,
            'transition_probabilities': transition_probs,
            'key_insights': {
                'high_retention_rate': transition_probs.get('高', {}).get('高', 0),
                'medium_upgrade_rate': transition_probs.get('中', {}).get('高', 0),
                'low_churn_escalation': transition_probs.get('低', {}).get('低', 0),
                'high_to_low_rate': transition_probs.get('高', {}).get('低', 0)
            }
        }
    
    def _forecast_risk_users(self, trends_df, loyalty_results=None):
        user_latest = trends_df.groupby('customer_id').last().reset_index()
        
        def calc_slope(group):
            if len(group) < 2:
                return 0
            x = np.arange(len(group))
            y = group['loyalty_score'].values
            try:
                return np.polyfit(x, y, 1)[0]
            except Exception:
                return 0
        
        user_slopes = trends_df.groupby('customer_id').apply(calc_slope).reset_index()
        user_slopes.columns = ['customer_id', 'slope']
        user_latest = user_latest.merge(user_slopes, on='customer_id')
        
        def risk_level(row):
            score = row['loyalty_score']
            slope = row['slope']
            if score < 40 and slope < -1:
                return 'critical'
            elif score < 50 and slope < -0.5:
                return 'high'
            elif score < 60 and slope < 0:
                return 'medium'
            elif slope < -0.5:
                return 'low'
            else:
                return 'minimal'
        
        user_latest['risk_level'] = user_latest.apply(risk_level, axis=1)
        
        risk_distribution = user_latest['risk_level'].value_counts().to_dict()
        
        critical_users = user_latest[user_latest['risk_level'] == 'critical'].nlargest(20, 'slope', keep='last')
        high_risk_users = user_latest[user_latest['risk_level'] == 'high'].nlargest(20, 'slope', keep='last')
        
        return {
            'risk_distribution': risk_distribution,
            'critical_users': critical_users[['customer_id', 'loyalty_score', 'slope', 'risk_level']].to_dict('records'),
            'high_risk_users': high_risk_users[['customer_id', 'loyalty_score', 'slope', 'risk_level']].to_dict('records'),
            'total_at_risk': int((user_latest['risk_level'].isin(['critical', 'high'])).sum()),
            'at_risk_pct': float(user_latest['risk_level'].isin(['critical', 'high']).mean() * 100)
        }
    
    def _determine_intervention_timing(self, trends_df):
        user_latest = trends_df.groupby('customer_id').last().reset_index()
        
        def calc_slope(group):
            if len(group) < 2:
                return 0
            x = np.arange(len(group))
            y = group['loyalty_score'].values
            try:
                return np.polyfit(x, y, 1)[0]
            except Exception:
                return 0
        
        user_slopes = trends_df.groupby('customer_id').apply(calc_slope).reset_index()
        user_slopes.columns = ['customer_id', 'slope']
        user_latest = user_latest.merge(user_slopes, on='customer_id')
        
        def timing_urgency(row):
            score = row['loyalty_score']
            slope = row['slope']
            if score < 40 and slope < -1:
                return 'immediate'
            elif score < 50 and slope < -0.5:
                return 'within_1_month'
            elif score < 60 and slope < 0:
                return 'within_3_months'
            elif score < 70 and slope < -0.3:
                return 'within_6_months'
            else:
                return 'routine'
        
        user_latest['intervention_timing'] = user_latest.apply(timing_urgency, axis=1)
        
        timing_dist = user_latest['intervention_timing'].value_counts().to_dict()
        
        immediate_users = user_latest[user_latest['intervention_timing'] == 'immediate']
        
        return {
            'timing_distribution': timing_dist,
            'immediate_action_count': len(immediate_users),
            'immediate_users_sample': immediate_users[['customer_id', 'loyalty_score', 'slope']].head(20).to_dict('records'),
            'recommended_actions': {
                'immediate': '立即启动一对一客户关怀，专属优惠挽回',
                'within_1_month': '月内安排客户回访，了解不满意原因',
                'within_3_months': '季度内优化产品体验，推送个性化推荐',
                'within_6_months': '半年度客户满意度提升计划',
                'routine': '常规忠诚度维护和会员权益优化'
            }
        }
