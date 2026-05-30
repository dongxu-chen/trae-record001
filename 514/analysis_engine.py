import pandas as pd
import numpy as np
import shap
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, List, Tuple, Optional
from io import BytesIO
import base64


class SHAPAnalyzer:
    def __init__(self, model, feature_cols: List[str]):
        self.model = model
        self.feature_cols = feature_cols
        self.explainer = None
        self.shap_values = None
        self.expected_value = None

    def _process_shap_values(self, shap_vals, expected_vals):
        if isinstance(shap_vals, list):
            self.shap_values = shap_vals[1]
            self.expected_value = expected_vals[1] if isinstance(expected_vals, list) else expected_vals
        elif len(shap_vals.shape) == 3:
            self.shap_values = shap_vals[:, :, 1]
            if isinstance(expected_vals, np.ndarray) and len(expected_vals.shape) > 0:
                self.expected_value = expected_vals[1]
            else:
                self.expected_value = expected_vals
        else:
            self.shap_values = shap_vals
            self.expected_value = expected_vals

    def initialize_explainer(self, X: np.ndarray):
        self.explainer = shap.TreeExplainer(self.model)
        shap_vals = self.explainer.shap_values(X)
        self._process_shap_values(shap_vals, self.explainer.expected_value)
        return self

    def get_feature_importance(self, X: pd.DataFrame, top_k: int = 20) -> pd.DataFrame:
        if self.shap_values is None:
            self.initialize_explainer(X[self.feature_cols].fillna(0).values)

        shap_values_mean = np.mean(np.abs(self.shap_values), axis=0)

        importance_df = pd.DataFrame({
            'feature': self.feature_cols,
            'shap_importance': shap_values_mean
        }).sort_values('shap_importance', ascending=False)

        return importance_df.head(top_k)

    def get_summary_plot(self, X: pd.DataFrame, max_display: int = 15) -> BytesIO:
        if self.shap_values is None:
            self.initialize_explainer(X[self.feature_cols].fillna(0).values)

        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            self.shap_values,
            X[self.feature_cols].fillna(0),
            feature_names=self.feature_cols,
            max_display=max_display,
            show=False
        )
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def get_force_plot(self, X: pd.DataFrame, user_idx: int = 0) -> BytesIO:
        if self.shap_values is None:
            self.initialize_explainer(X[self.feature_cols].fillna(0).values)

        X_scaled = X[self.feature_cols].fillna(0).values
        shap_value = self.shap_values[user_idx]
        expected_value = self.expected_value

        plt.figure(figsize=(12, 4))
        shap.force_plot(
            expected_value,
            shap_value,
            X_scaled[user_idx],
            feature_names=self.feature_cols,
            matplotlib=True,
            show=False
        )
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close()

        return buf

    def get_user_shap_values(self, X: pd.DataFrame, user_idx: int = 0) -> pd.DataFrame:
        if self.shap_values is None:
            self.initialize_explainer(X[self.feature_cols].fillna(0).values)

        shap_value = self.shap_values[user_idx]

        shap_df = pd.DataFrame({
            'feature': self.feature_cols,
            'shap_value': shap_value,
            'feature_value': X[self.feature_cols].fillna(0).iloc[user_idx].values
        }).sort_values('shap_value', key=lambda x: x.abs(), ascending=False)

        return shap_df


class ChurnRiskScorer:
    SEGMENT_THRESHOLDS = {
        'high_active': {'high': 50, 'medium': 25},
        'medium_active': {'high': 60, 'medium': 30},
        'low_active': {'high': 70, 'medium': 40},
        'churn_risk': {'high': 70, 'medium': 40},
    }

    SEGMENT_RISK_WEIGHTS = {
        'high_active': {'login_freq': 0.35, 'recency': 0.25, 'trend': 0.20, 'diversity': 0.10, 'active_7d': 0.10},
        'medium_active': {'login_freq': 0.30, 'recency': 0.25, 'trend': 0.20, 'diversity': 0.15, 'active_7d': 0.10},
        'low_active': {'login_freq': 0.25, 'recency': 0.25, 'trend': 0.15, 'diversity': 0.20, 'active_7d': 0.15},
        'churn_risk': {'login_freq': 0.20, 'recency': 0.30, 'trend': 0.15, 'diversity': 0.20, 'active_7d': 0.15},
    }

    def __init__(self, feature_matrix: pd.DataFrame):
        self.feature_matrix = feature_matrix

    def calculate_churn_risk(self, predictions: pd.DataFrame) -> pd.DataFrame:
        risk_df = self.feature_matrix[['user_id']].copy()
        features = self.feature_matrix

        segments = features['user_segment'] if 'user_segment' in features.columns else None

        login_freq = features['login_frequency'].values
        raw_login = (1 - login_freq)

        days_since_login = features['days_since_last_login'].values
        raw_recency = np.minimum(days_since_login / 14, 1)

        login_trend = features['login_count_trend_slope'].values
        raw_trend = np.where(login_trend < 0, np.minimum(-login_trend * 15, 1), 0)

        feature_diversity = features['feature_diversity_score'].values
        raw_diversity = (1 - feature_diversity)

        active_days_7d = features['active_days_last_7d'].values
        raw_active_7d = np.where(active_days_7d < 2, (2 - active_days_7d) / 7, 0)

        risk_scores = np.zeros(len(features))
        for i in range(len(features)):
            seg = segments.iloc[i] if segments is not None else 'medium_active'
            weights = self.SEGMENT_RISK_WEIGHTS.get(seg, self.SEGMENT_RISK_WEIGHTS['medium_active'])

            risk_scores[i] = (
                raw_login[i] * 100 * weights['login_freq'] +
                raw_recency[i] * 100 * weights['recency'] +
                raw_trend[i] * 100 * weights['trend'] +
                raw_diversity[i] * 100 * weights['diversity'] +
                raw_active_7d[i] * 100 * weights['active_7d']
            )

        prob_low = predictions['prob_low'].values
        total_risk = risk_scores * 0.7 + prob_low * 100 * 0.3
        total_risk = np.minimum(total_risk, 100)

        risk_df['churn_risk_score'] = np.round(total_risk, 1)

        risk_levels = []
        for i in range(len(risk_df)):
            seg = segments.iloc[i] if segments is not None else 'medium_active'
            thresholds = self.SEGMENT_THRESHOLDS.get(seg, self.SEGMENT_THRESHOLDS['medium_active'])
            score = total_risk[i]
            if score >= thresholds['high']:
                risk_levels.append('high')
            elif score >= thresholds['medium']:
                risk_levels.append('medium')
            else:
                risk_levels.append('low')

        risk_df['risk_level'] = risk_levels
        risk_df['risk_factors'] = self._get_risk_factors(features, predictions, segments)

        return risk_df

    def _classify_risk(self, score: float, segment: str = 'medium_active') -> str:
        thresholds = self.SEGMENT_THRESHOLDS.get(segment, self.SEGMENT_THRESHOLDS['medium_active'])
        if score >= thresholds['high']:
            return 'high'
        elif score >= thresholds['medium']:
            return 'medium'
        else:
            return 'low'

    def _get_risk_factors(
        self,
        features: pd.DataFrame,
        predictions: pd.DataFrame,
        segments: Optional[pd.Series] = None
    ) -> List[List[str]]:
        factors_list = []

        for idx, row in features.iterrows():
            factors = []
            seg = segments.iloc[idx] if segments is not None else 'medium_active'
            thresholds = self.SEGMENT_THRESHOLDS.get(seg, self.SEGMENT_THRESHOLDS['medium_active'])

            if row['login_frequency'] < 0.3:
                factors.append('登录频率过低')
            if row['days_since_last_login'] > 7:
                factors.append(f"已{int(row['days_since_last_login'])}天未登录")
            if row['login_count_trend_slope'] < -0.02:
                factors.append('活跃度呈下降趋势')
            if row['feature_diversity_score'] < 0.2:
                factors.append('功能使用单一')
            if row['active_days_last_7d'] < 2:
                factors.append('近7天活跃天数不足')
            if predictions.iloc[idx]['prob_low'] > 0.7:
                factors.append('预测低活跃概率高')

            if not factors:
                factors.append('无明显风险因素')

            factors_list.append(factors)

        return factors_list


class RecommendationEngine:
    CHANNEL_NAMES = {
        'email': '邮件', 'push': '推送通知', 'sms': '短信',
        'in_app': '产品内消息', 'wechat': '微信', 'community': '社区'
    }

    def __init__(self, feature_matrix: pd.DataFrame = None):
        self.feature_matrix = feature_matrix
        self.recommendation_templates = {
            'high_risk': [
                {
                    'trigger': '登录频率过低',
                    'title': '召回流失用户',
                    'suggestion': '立即发送个性化召回邮件，展示用户错过的重要更新和新功能，提供专属回归优惠。',
                    'channel': '邮件+推送',
                    'priority': '高',
                    'action': 'send_recall_campaign'
                },
                {
                    'trigger': '已超过7天未登录',
                    'title': '激活沉睡用户',
                    'suggestion': '发送"我们想你了"系列推送，附送上次使用的功能更新，设置登录专属奖励。',
                    'channel': '推送+短信',
                    'priority': '高',
                    'action': 'send_activation_campaign'
                },
            ],
            'medium_risk': [
                {
                    'trigger': '活跃度呈下降趋势',
                    'title': '预防用户流失',
                    'suggestion': '推荐用户可能感兴趣的新功能，发送使用技巧指南，邀请参与用户调研。',
                    'channel': '产品内消息+邮件',
                    'priority': '中',
                    'action': 'send_engagement_campaign'
                },
                {
                    'trigger': '功能使用单一',
                    'title': '深度功能引导',
                    'suggestion': '根据用户已使用的功能，智能推荐相关高级功能，提供功能使用教程。',
                    'channel': '产品内引导+教程邮件',
                    'priority': '中',
                    'action': 'send_feature_guide'
                },
            ],
            'low_risk_high_active': [
                {
                    'trigger': '高活跃用户',
                    'title': '培育忠诚用户',
                    'suggestion': '邀请加入高级用户社区，提供专属客服通道，邀请参与Beta测试。',
                    'channel': '专属邮件+社区邀请',
                    'priority': '中',
                    'action': 'send_loyalty_program'
                },
            ],
            'low_risk_medium_active': [
                {
                    'trigger': '中活跃用户',
                    'title': '提升用户参与度',
                    'suggestion': '展示更多高级功能价值，设置成就系统和等级激励，引导每日登录习惯。',
                    'channel': '产品内推荐+成就通知',
                    'priority': '低',
                    'action': 'send_engagement_tips'
                },
            ]
        }

    def _learn_channel_preference(self, user_id: str) -> Dict:
        if self.feature_matrix is None:
            return {'preferred': 'push', 'secondary': 'email', 'all_scores': {}}

        all_channels = ['email', 'push', 'sms', 'in_app', 'wechat', 'community']
        user_row = self.feature_matrix[self.feature_matrix['user_id'] == user_id]

        if len(user_row) == 0:
            return {'preferred': 'push', 'secondary': 'email', 'all_scores': {}}

        user_row = user_row.iloc[0]
        scores = {}
        for ch in all_channels:
            score_col = f'channel_{ch}_score'
            ratio_col = f'channel_{ch}_ratio'
            if score_col in user_row.index and ratio_col in user_row.index:
                scores[ch] = user_row[score_col] * 0.6 + user_row[ratio_col] * 100 * 0.4
            elif score_col in user_row.index:
                scores[ch] = user_row[score_col]
            else:
                scores[ch] = 0

        sorted_channels = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        preferred = sorted_channels[0][0] if sorted_channels else 'push'
        secondary = sorted_channels[1][0] if len(sorted_channels) > 1 else 'email'

        return {
            'preferred': preferred,
            'secondary': secondary,
            'all_scores': scores,
            'preferred_name': self.CHANNEL_NAMES.get(preferred, preferred),
            'secondary_name': self.CHANNEL_NAMES.get(secondary, secondary),
        }

    def _apply_channel_preference(self, rec: Dict, channel_pref: Dict) -> Dict:
        rec = rec.copy()
        preferred = channel_pref.get('preferred', 'push')
        secondary = channel_pref.get('secondary', 'email')
        pref_name = channel_pref.get('preferred_name', self.CHANNEL_NAMES.get(preferred, preferred))
        sec_name = channel_pref.get('secondary_name', self.CHANNEL_NAMES.get(secondary, secondary))

        rec['original_channel'] = rec['channel']
        rec['preferred_channel'] = f"{pref_name}+{sec_name}"
        rec['channel'] = rec['preferred_channel']

        if 'suggestion' in rec:
            rec['suggestion'] = rec['suggestion'].replace('邮件', pref_name).replace('推送', pref_name)

        rec['channel_preference_detail'] = {
            'primary_channel': preferred,
            'secondary_channel': secondary,
            'confidence': 'high' if channel_pref.get('all_scores', {}).get(preferred, 0) > 5 else 'medium',
        }

        return rec

    def generate_recommendations(
        self,
        user_data: pd.DataFrame,
        churn_risk: pd.DataFrame,
        predictions: pd.DataFrame
    ) -> pd.DataFrame:
        merged_df = user_data[['user_id']].merge(
            churn_risk, on='user_id', how='left'
        ).merge(
            predictions[['user_id', 'predicted_level', 'prob_low', 'prob_medium', 'prob_high']],
            on='user_id', how='left'
        )

        recommendations = []
        for _, row in merged_df.iterrows():
            user_recs = self._get_user_recommendations(row)
            recommendations.append({
                'user_id': row['user_id'],
                'recommendations': user_recs
            })

        return pd.DataFrame(recommendations)

    def _get_user_recommendations(self, user_row: pd.Series) -> List[Dict]:
        recs = []
        risk_level = user_row['risk_level']
        predicted_level = user_row['predicted_level']
        risk_factors = user_row['risk_factors']

        channel_pref = self._learn_channel_preference(user_row['user_id'])

        for factor in risk_factors:
            if risk_level == 'high':
                template = self._find_template(factor, 'high_risk')
                if template:
                    recs.append(self._apply_channel_preference(template, channel_pref))
            elif risk_level == 'medium':
                template = self._find_template(factor, 'medium_risk')
                if template:
                    recs.append(self._apply_channel_preference(template, channel_pref))

        if not recs or risk_level == 'low':
            if predicted_level == 'high':
                rec = self.recommendation_templates['low_risk_high_active'][0]
            else:
                rec = self.recommendation_templates['low_risk_medium_active'][0]
            recs.append(self._apply_channel_preference(rec, channel_pref))

        return recs

    def _find_template(self, factor: str, risk_category: str) -> Optional[Dict]:
        templates = self.recommendation_templates.get(risk_category, [])
        for template in templates:
            if template['trigger'] in factor or factor in template['trigger']:
                return template.copy()
        return None


class ActivityAttributor:
    FEATURE_BEHAVIOR_MAP = {
        'login_frequency': {'behavior': '登录习惯', 'category': '登录频率'},
        'days_since_last_login': {'behavior': '最近登录', 'category': '登录新近度'},
        'login_count_trend_slope': {'behavior': '登录趋势', 'category': '登录趋势'},
        'avg_session_duration': {'behavior': '会话深度', 'category': '使用深度'},
        'session_duration_minutes_trend_slope': {'behavior': '时长变化', 'category': '使用深度'},
        'avg_feature_usage': {'behavior': '功能使用频率', 'category': '功能参与'},
        'feature_diversity_score': {'behavior': '功能探索广度', 'category': '功能参与'},
        'unique_features_used_total': {'behavior': '功能种类数', 'category': '功能参与'},
        'active_days_last_7d': {'behavior': '近期活跃天数', 'category': '近期活跃'},
        'active_days_last_14d': {'behavior': '中期活跃天数', 'category': '近期活跃'},
        'current_login_streak': {'behavior': '连续登录', 'category': '登录频率'},
        'max_login_streak': {'behavior': '最长连续登录', 'category': '登录频率'},
        'feature_usage_count_trend_slope': {'behavior': '功能使用趋势', 'category': '功能参与'},
        'detected_cycle_days': {'behavior': '活跃周期', 'category': '活跃规律'},
        'channel_diversity': {'behavior': '渠道参与度', 'category': '渠道互动'},
    }

    CATEGORY_DESCRIPTIONS = {
        '登录频率': '用户登录的规律性和频率',
        '登录新近度': '用户最近一次登录距今的时间',
        '登录趋势': '用户登录行为的变化方向',
        '使用深度': '用户每次使用产品的沉浸程度',
        '功能参与': '用户对产品功能的探索和使用',
        '近期活跃': '用户近期在产品中的活跃表现',
        '活跃规律': '用户活跃的周期性规律',
        '渠道互动': '用户对触达渠道的响应',
    }

    IMPACT_TEMPLATES = {
        'positive': {
            'login_frequency': '稳定的登录习惯是你保持活跃的核心动力',
            'avg_session_duration': '深度使用产品让你保持了高参与度',
            'feature_diversity_score': '广泛探索功能有效提升了你的活跃度',
            'active_days_last_7d': '近期持续活跃为你带来了正向增长',
            'current_login_streak': '连续登录正在帮你养成良好习惯',
        },
        'negative': {
            'login_frequency': '登录频率下降是活跃度降低的主要原因',
            'days_since_last_login': '长时间未登录导致活跃度明显下滑',
            'avg_session_duration': '使用深度不足限制了活跃度提升',
            'feature_diversity_score': '功能使用过于单一，限制了参与度',
            'active_days_last_7d': '近期活跃天数不足，需要加强',
            'login_count_trend_slope': '活跃度呈下降趋势，需要及时扭转',
        },
    }

    def __init__(self, shap_analyzer: SHAPAnalyzer, feature_matrix: pd.DataFrame):
        self.shap_analyzer = shap_analyzer
        self.feature_matrix = feature_matrix

    def attribute_user(self, user_id: str, top_k: int = 5) -> Dict:
        user_idx_arr = self.feature_matrix[self.feature_matrix['user_id'] == user_id].index
        if len(user_idx_arr) == 0:
            return {'user_id': user_id, 'attributions': [], 'summary': ''}
        user_idx = user_idx_arr[0]

        user_shap = self.shap_analyzer.get_user_shap_values(
            self.feature_matrix, user_idx=user_idx
        )

        attributions = []
        for _, row in user_shap.head(top_k * 2).iterrows():
            feature = row['feature']
            shap_val = row['shap_value']
            feat_val = row['feature_value']

            behavior_info = self._map_feature_to_behavior(feature, shap_val, feat_val)
            if behavior_info:
                attributions.append(behavior_info)

            if len(attributions) >= top_k:
                break

        summary = self._generate_attribution_summary(attributions)

        category_impact = self._aggregate_by_category(attributions)

        return {
            'user_id': user_id,
            'attributions': attributions,
            'summary': summary,
            'category_impact': category_impact,
        }

    def _map_feature_to_behavior(self, feature: str, shap_val: float, feat_val: float) -> Optional[Dict]:
        behavior_info = None
        for key, info in self.FEATURE_BEHAVIOR_MAP.items():
            if key in feature:
                behavior_info = info.copy()
                break

        if behavior_info is None:
            matched = False
            for key, info in self.FEATURE_BEHAVIOR_MAP.items():
                if any(k in feature for k in key.split('_')):
                    behavior_info = info.copy()
                    matched = True
                    break
            if not matched:
                behavior_info = {'behavior': feature, 'category': '其他'}

        direction = 'positive' if shap_val > 0 else 'negative'
        impact_strength = min(abs(shap_val) / 0.5, 1.0)

        description = self._get_impact_description(feature, direction, feat_val)

        return {
            'feature': feature,
            'behavior': behavior_info['behavior'],
            'category': behavior_info['category'],
            'shap_value': round(shap_val, 4),
            'feature_value': round(feat_val, 4),
            'direction': direction,
            'direction_label': '正向驱动' if direction == 'positive' else '负向拖累',
            'impact_strength': round(impact_strength, 2),
            'impact_label': '强' if impact_strength > 0.7 else '中' if impact_strength > 0.3 else '弱',
            'description': description,
        }

    def _get_impact_description(self, feature: str, direction: str, feat_val: float) -> str:
        for key, template_text in self.IMPACT_TEMPLATES.get(direction, {}).items():
            if key in feature:
                return template_text

        if direction == 'positive':
            return f'该行为正向推动了活跃度提升 (SHAP值: {feat_val:.3f})'
        else:
            return f'该行为负向拖累了活跃度 (SHAP值: {feat_val:.3f})'

    def _generate_attribution_summary(self, attributions: List[Dict]) -> str:
        if not attributions:
            return '暂无归因信息'

        positive = [a for a in attributions if a['direction'] == 'positive']
        negative = [a for a in attributions if a['direction'] == 'negative']

        parts = []
        if positive:
            pos_behaviors = '、'.join([a['behavior'] for a in positive[:3]])
            parts.append(f'活跃度主要由{pos_behaviors}正向驱动')
        if negative:
            neg_behaviors = '、'.join([a['behavior'] for a in negative[:3]])
            parts.append(f'受到{neg_behaviors}的负向拖累')

        return '；'.join(parts) if parts else '活跃度受多种因素均衡影响'

    def _aggregate_by_category(self, attributions: List[Dict]) -> Dict:
        category_impact = {}
        for a in attributions:
            cat = a['category']
            if cat not in category_impact:
                category_impact[cat] = {'positive': 0, 'negative': 0, 'count': 0}
            if a['direction'] == 'positive':
                category_impact[cat]['positive'] += abs(a['shap_value'])
            else:
                category_impact[cat]['negative'] += abs(a['shap_value'])
            category_impact[cat]['count'] += 1

        for cat in category_impact:
            total = category_impact[cat]['positive'] + category_impact[cat]['negative']
            category_impact[cat]['net_impact'] = category_impact[cat]['positive'] - category_impact[cat]['negative']
            category_impact[cat]['dominant'] = 'positive' if category_impact[cat]['net_impact'] > 0 else 'negative'
            category_impact[cat]['description'] = self.CATEGORY_DESCRIPTIONS.get(cat, '')

        return category_impact


class CopyGenerator:
    SEGMENT_TONE = {
        'high_active': {'style': '亲切赞赏', 'emoji': '🎉', 'greeting': '亲爱的核心用户'},
        'medium_active': {'style': '温暖鼓励', 'emoji': '💪', 'greeting': '你好呀'},
        'low_active': {'style': '轻松引导', 'emoji': '✨', 'greeting': '好久不见'},
        'churn_risk': {'style': '关切召唤', 'emoji': '🤗', 'greeting': '我们想你了'},
    }

    BEHAVIOR_COPY_TEMPLATES = {
        'login_frequency': {
            'low': [
                '只需每天花{duration}分钟，就能解锁更多精彩功能',
                '你的{top_feature}功能有新更新，来看看吧',
                '重新登录即享专属回归礼包',
            ],
            'medium': [
                '坚持登录{streak}天了！继续保持好习惯',
                '今天有{count}个新消息等你查看',
            ],
            'high': [
                '太棒了！你已经连续活跃{streak}天',
                '你的活跃度超越了{percent}%的用户',
            ],
        },
        'session_duration': {
            'low': [
                '快速{duration}分钟打卡，轻松完成任务',
                '碎片时间也能用好{top_feature}',
            ],
            'medium': [
                '再停留{extra}分钟，就能解锁深度分析功能',
                '试试{top_feature}的高级模式，体验更佳',
            ],
            'high': [
                '深度用户就是你！{top_feature}的新能力已上线',
                '你的使用深度超过了{percent}%的用户',
            ],
        },
        'feature_diversity': {
            'low': [
                '发现新功能：{related_feature}，与{top_feature}搭配使用更高效',
                '解锁更多功能，让工作事半功倍',
            ],
            'medium': [
                '推荐试试{related_feature}，和{top_feature}搭配效果翻倍',
                '已有{count}个功能等你探索',
            ],
            'high': [
                '功能达人！你已解锁{count}个功能',
                '新上线的{related_feature}一定适合你',
            ],
        },
        'active_days': {
            'low': [
                '本周只需再活跃{needed}天，即可获得活跃勋章',
                '轻松一步：打开{top_feature}即可完成今日打卡',
            ],
            'medium': [
                '距离本周活跃目标只差{needed}天',
                '保持节奏，本周活跃奖励等你领取',
            ],
            'high': [
                '全勤之星！本周满勤达成',
                '连续{streak}天活跃，活跃度持续攀升',
            ],
        },
        'trend': {
            'declining': [
                '别让努力白费，今天回归还有特别奖励',
                '你的{top_feature}数据有新动态，快来看看',
            ],
            'stable': [
                '保持稳定就是胜利，继续加油',
                '你的使用习惯很规律，试试新功能换个体验',
            ],
            'growing': [
                '活跃度持续上升中，势头正好',
                '你在{top_feature}上的投入正在产生效果',
            ],
        },
    }

    def __init__(self, feature_matrix: pd.DataFrame, behavior_df: pd.DataFrame = None):
        self.feature_matrix = feature_matrix
        self.behavior_df = behavior_df

    def generate_copy(self, user_id: str, attribution: Dict = None) -> Dict:
        user_row = self.feature_matrix[self.feature_matrix['user_id'] == user_id]
        if len(user_row) == 0:
            return {'user_id': user_id, 'copies': [], 'primary_copy': ''}
        user_row = user_row.iloc[0]

        segment = user_row.get('user_segment', 'medium_active')
        tone = self.SEGMENT_TONE.get(segment, self.SEGMENT_TONE['medium_active'])

        user_behavior_data = self._get_user_behavior_data(user_id)

        copies = []
        copies.append(self._generate_login_copy(user_row, tone, user_behavior_data))
        copies.append(self._generate_session_copy(user_row, tone, user_behavior_data))
        copies.append(self._generate_feature_copy(user_row, tone, user_behavior_data))
        copies.append(self._generate_active_days_copy(user_row, tone, user_behavior_data))
        copies.append(self._generate_trend_copy(user_row, tone, user_behavior_data))

        copies = [c for c in copies if c is not None]

        primary_copy = self._select_primary_copy(copies, user_row, tone)

        return {
            'user_id': user_id,
            'tone': tone['style'],
            'greeting': tone['greeting'],
            'copies': copies,
            'primary_copy': primary_copy,
        }

    def _get_user_behavior_data(self, user_id: str) -> Dict:
        data = {'top_feature': '数据分析', 'related_feature': '报表导出'}
        if self.behavior_df is None:
            return data

        user_behavior = self.behavior_df[self.behavior_df['user_id'] == user_id]
        if len(user_behavior) == 0:
            return data

        feature_counts = {}
        for features_str in user_behavior['features_used'].dropna():
            if isinstance(features_str, str) and features_str:
                for f in features_str.split(','):
                    f = f.strip()
                    if f:
                        feature_counts[f] = feature_counts.get(f, 0) + 1

        if feature_counts:
            sorted_features = sorted(feature_counts.items(), key=lambda x: x[1], reverse=True)
            feature_names = {
                'dashboard': '仪表盘', 'analytics': '数据分析', 'reports': '报表',
                'settings': '设置', 'search': '搜索', 'export': '导出',
                'share': '分享', 'notifications': '通知', 'profile': '个人中心',
                'help': '帮助', 'upload': '上传', 'download': '下载',
                'edit': '编辑', 'delete': '删除', 'create': '创建',
            }
            top_key = sorted_features[0][0]
            data['top_feature'] = feature_names.get(top_key, top_key)
            if len(sorted_features) > 1:
                related_key = sorted_features[1][0]
                data['related_feature'] = feature_names.get(related_key, related_key)

        return data

    def _determine_level(self, value: float, low_thresh: float, high_thresh: float) -> str:
        if value < low_thresh:
            return 'low'
        elif value > high_thresh:
            return 'high'
        return 'medium'

    def _generate_login_copy(self, user_row, tone: Dict, behavior_data: Dict) -> Optional[Dict]:
        login_freq = user_row.get('login_frequency', 0)
        level = self._determine_level(login_freq, 0.3, 0.7)
        templates = self.BEHAVIOR_COPY_TEMPLATES['login_frequency'].get(level, [])

        if not templates:
            return None

        template = templates[0]
        copy_text = template.format(
            duration=max(5, int(user_row.get('avg_session_duration', 15) * 0.5)),
            top_feature=behavior_data['top_feature'],
            streak=int(user_row.get('current_login_streak', 0)),
            count=np.random.randint(1, 8),
            percent=np.random.randint(60, 95),
        )

        return {
            'behavior_type': '登录频率',
            'level': level,
            'level_label': {'low': '偏低', 'medium': '适中', 'high': '优秀'}[level],
            'copy': f"{tone['emoji']} {copy_text}",
            'metric_value': f"{login_freq:.1%}",
        }

    def _generate_session_copy(self, user_row, tone: Dict, behavior_data: Dict) -> Optional[Dict]:
        avg_duration = user_row.get('avg_session_duration', 0)
        level = self._determine_level(avg_duration, 10, 30)
        templates = self.BEHAVIOR_COPY_TEMPLATES['session_duration'].get(level, [])

        if not templates:
            return None

        template = templates[0]
        copy_text = template.format(
            duration=max(3, int(avg_duration * 0.5)),
            extra=max(2, int(avg_duration * 0.3)),
            top_feature=behavior_data['top_feature'],
            percent=np.random.randint(50, 90),
        )

        return {
            'behavior_type': '使用深度',
            'level': level,
            'level_label': {'low': '偏浅', 'medium': '适中', 'high': '深入'}[level],
            'copy': f"{tone['emoji']} {copy_text}",
            'metric_value': f"{avg_duration:.1f}分钟",
        }

    def _generate_feature_copy(self, user_row, tone: Dict, behavior_data: Dict) -> Optional[Dict]:
        diversity = user_row.get('feature_diversity_score', 0)
        level = self._determine_level(diversity, 0.2, 0.5)
        templates = self.BEHAVIOR_COPY_TEMPLATES['feature_diversity'].get(level, [])

        if not templates:
            return None

        template = templates[0]
        unique_features = int(user_row.get('unique_features_used_total', 0))
        copy_text = template.format(
            related_feature=behavior_data['related_feature'],
            top_feature=behavior_data['top_feature'],
            count=max(1, 15 - unique_features),
        )

        return {
            'behavior_type': '功能探索',
            'level': level,
            'level_label': {'low': '单一', 'medium': '适中', 'high': '广泛'}[level],
            'copy': f"{tone['emoji']} {copy_text}",
            'metric_value': f"{diversity:.1%}",
        }

    def _generate_active_days_copy(self, user_row, tone: Dict, behavior_data: Dict) -> Optional[Dict]:
        active_7d = user_row.get('active_days_last_7d', 0)
        level = self._determine_level(active_7d, 2, 5)
        templates = self.BEHAVIOR_COPY_TEMPLATES['active_days'].get(level, [])

        if not templates:
            return None

        template = templates[0]
        copy_text = template.format(
            needed=max(1, 5 - int(active_7d)),
            top_feature=behavior_data['top_feature'],
            streak=int(user_row.get('current_login_streak', 0)),
        )

        return {
            'behavior_type': '近期活跃',
            'level': level,
            'level_label': {'low': '不足', 'medium': '适中', 'high': '充足'}[level],
            'copy': f"{tone['emoji']} {copy_text}",
            'metric_value': f"{int(active_7d)}天/7天",
        }

    def _generate_trend_copy(self, user_row, tone: Dict, behavior_data: Dict) -> Optional[Dict]:
        trend_slope = user_row.get('login_count_trend_slope', 0)
        if trend_slope < -0.01:
            trend_key = 'declining'
        elif trend_slope > 0.01:
            trend_key = 'growing'
        else:
            trend_key = 'stable'

        templates = self.BEHAVIOR_COPY_TEMPLATES['trend'].get(trend_key, [])
        if not templates:
            return None

        template = templates[0]
        copy_text = template.format(
            top_feature=behavior_data['top_feature'],
        )

        return {
            'behavior_type': '活跃趋势',
            'level': trend_key,
            'level_label': {'declining': '下降', 'stable': '平稳', 'growing': '上升'}[trend_key],
            'copy': f"{tone['emoji']} {copy_text}",
            'metric_value': f"{'↑' if trend_key == 'growing' else '→' if trend_key == 'stable' else '↓'}",
        }

    def _select_primary_copy(self, copies: List[Dict], user_row, tone: Dict) -> str:
        if not copies:
            return f"{tone['greeting']}，欢迎回来！今天有什么可以帮你的？"

        level_priority = {
            'low': 0, 'declining': 0,
            'medium': 1, 'stable': 1,
            'high': 2, 'growing': 2,
        }
        sorted_copies = sorted(copies, key=lambda c: level_priority.get(c['level'], 1))

        best = sorted_copies[0]
        return f"{tone['greeting']}，{best['copy']}"


class GroupComparator:
    SEGMENT_NAMES = {
        'high_active': '高活跃用户',
        'medium_active': '中活跃用户',
        'low_active': '低活跃用户',
        'churn_risk': '流失风险用户',
    }

    SEGMENT_COLORS = {
        'high_active': '#2ca02c',
        'medium_active': '#ff7f0e',
        'low_active': '#d62728',
        'churn_risk': '#9467bd',
    }

    METRIC_CONFIG = {
        'login_frequency': {'name': '登录频率', 'format': '.1%', 'higher_better': True},
        'avg_session_duration': {'name': '平均会话时长(分钟)', 'format': '.1f', 'higher_better': True},
        'feature_diversity_score': {'name': '功能多样性', 'format': '.1%', 'higher_better': True},
        'active_days_last_7d': {'name': '近7天活跃天数', 'format': '.0f', 'higher_better': True},
        'active_days_last_14d': {'name': '近14天活跃天数', 'format': '.0f', 'higher_better': True},
        'days_since_last_login': {'name': '距上次登录(天)', 'format': '.0f', 'higher_better': False},
        'current_login_streak': {'name': '当前连续登录', 'format': '.0f', 'higher_better': True},
        'max_login_streak': {'name': '最长连续登录', 'format': '.0f', 'higher_better': True},
        'unique_features_used_total': {'name': '使用功能数', 'format': '.0f', 'higher_better': True},
    }

    def __init__(self, feature_matrix: pd.DataFrame):
        self.feature_matrix = feature_matrix

    def compare_groups(self) -> Dict:
        if 'user_segment' not in self.feature_matrix.columns:
            return {'error': '缺少 user_segment 列'}

        segments = ['high_active', 'medium_active', 'low_active', 'churn_risk']
        comparison = {}

        for metric, config in self.METRIC_CONFIG.items():
            if metric not in self.feature_matrix.columns:
                continue

            metric_data = {}
            for seg in segments:
                seg_data = self.feature_matrix[self.feature_matrix['user_segment'] == seg][metric]
                metric_data[seg] = {
                    'mean': seg_data.mean(),
                    'median': seg_data.median(),
                    'std': seg_data.std(),
                    'count': len(seg_data),
                }

            best_seg = max(metric_data, key=lambda s: metric_data[s]['mean']) if config['higher_better'] else min(metric_data, key=lambda s: metric_data[s]['mean'])
            worst_seg = min(metric_data, key=lambda s: metric_data[s]['mean']) if config['higher_better'] else max(metric_data, key=lambda s: metric_data[s]['mean'])

            comparison[metric] = {
                'config': config,
                'data': metric_data,
                'best_segment': best_seg,
                'worst_segment': worst_seg,
                'gap': abs(metric_data[best_seg]['mean'] - metric_data[worst_seg]['mean']),
            }

        return comparison

    def get_comparison_dataframe(self) -> pd.DataFrame:
        comparison = self.compare_groups()
        if 'error' in comparison:
            return pd.DataFrame()

        rows = []
        for metric, info in comparison.items():
            row = {'指标': info['config']['name']}
            for seg in ['high_active', 'medium_active', 'low_active', 'churn_risk']:
                if seg in info['data']:
                    val = info['data'][seg]['mean']
                    row[self.SEGMENT_NAMES[seg]] = format(val, info['config']['format'])
            row['最大差异'] = format(info['gap'], info['config']['format'])
            rows.append(row)

        return pd.DataFrame(rows)

    def get_pattern_insights(self) -> List[Dict]:
        comparison = self.compare_groups()
        if 'error' in comparison:
            return []

        insights = []
        for metric, info in comparison.items():
            best = info['best_segment']
            worst = info['worst_segment']
            gap_pct = info['gap'] / max(abs(info['data'][best]['mean']), 0.001) * 100

            if gap_pct > 50:
                insights.append({
                    'metric': info['config']['name'],
                    'insight': f"{self.SEGMENT_NAMES[best]}的{info['config']['name']}是{self.SEGMENT_NAMES[worst]}的{gap_pct:.0f}%",
                    'severity': 'high',
                    'recommendation': f'建议重点关注{self.SEGMENT_NAMES[worst]}的{info["config"]["name"]}提升',
                })
            elif gap_pct > 20:
                insights.append({
                    'metric': info['config']['name'],
                    'insight': f"{self.SEGMENT_NAMES[best]}与{self.SEGMENT_NAMES[worst]}的{info['config']['name']}差距为{gap_pct:.0f}%",
                    'severity': 'medium',
                    'recommendation': f'可通过引导提升{self.SEGMENT_NAMES[worst]}的{info["config"]["name"]}',
                })

        return insights


def create_activity_curve(
    behavior_df: pd.DataFrame,
    future_predictions: pd.DataFrame,
    user_id: str
) -> BytesIO:
    user_behavior = behavior_df[behavior_df['user_id'] == user_id].copy()
    user_behavior['date'] = pd.to_datetime(user_behavior['date'])

    user_future = future_predictions[future_predictions['user_id'] == user_id].copy()

    user_behavior['activity_score'] = (
        user_behavior['login_count'] * 20 +
        user_behavior['session_duration_minutes'] / 60 * 30 +
        user_behavior['feature_usage_count'] * 2
    )
    user_behavior['activity_score'] = np.minimum(user_behavior['activity_score'], 100)
    user_behavior['type'] = '历史'

    user_future['type'] = '预测'

    plt.figure(figsize=(12, 6))

    sns.lineplot(
        data=user_behavior,
        x='date',
        y='activity_score',
        label='历史活跃度',
        marker='o',
        linewidth=2,
        color='#1f77b4'
    )

    last_historical_date = user_behavior['date'].max()
    bridge_df = pd.DataFrame({
        'date': [last_historical_date, user_future['date'].min()],
        'activity_score': [
            user_behavior[user_behavior['date'] == last_historical_date]['activity_score'].values[0],
            user_future.iloc[0]['activity_score']
        ],
        'type': ['连接', '连接']
    })

    sns.lineplot(
        data=bridge_df,
        x='date',
        y='activity_score',
        linestyle='--',
        color='#ff7f0e',
        linewidth=1.5,
        label='_nolegend_'
    )

    sns.lineplot(
        data=user_future,
        x='date',
        y='activity_score',
        label='预测活跃度',
        marker='s',
        linewidth=2,
        color='#ff7f0e',
        linestyle='--'
    )

    plt.axhline(y=60, color='green', linestyle=':', alpha=0.7, label='高活跃阈值 (60)')
    plt.axhline(y=25, color='red', linestyle=':', alpha=0.7, label='低活跃阈值 (25)')

    plt.title(f'用户 {user_id} 活跃度曲线 - 历史与未来7天预测', fontsize=14)
    plt.xlabel('日期', fontsize=12)
    plt.ylabel('活跃度评分', fontsize=12)
    plt.xticks(rotation=45)
    plt.legend(loc='best')
    plt.grid(alpha=0.3)
    plt.ylim(0, 105)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def create_user_segmentation_plot(
    predictions: pd.DataFrame,
    churn_risk: pd.DataFrame
) -> BytesIO:
    merged = predictions.merge(churn_risk, on='user_id')

    color_map = {'high': '#2ca02c', 'medium': '#ff7f0e', 'low': '#d62728'}

    plt.figure(figsize=(10, 8))
    for level in ['high', 'medium', 'low']:
        subset = merged[merged['predicted_level'] == level]
        plt.scatter(
            subset['activity_score'],
            subset['churn_risk_score'],
            c=color_map[level],
            label=f'预测{level}活跃',
            alpha=0.7,
            s=100,
            edgecolors='white',
            linewidth=0.5
        )

    plt.axvline(x=60, color='gray', linestyle='--', alpha=0.5)
    plt.axvline(x=25, color='gray', linestyle='--', alpha=0.5)
    plt.axhline(y=70, color='red', linestyle='--', alpha=0.5)
    plt.axhline(y=40, color='orange', linestyle='--', alpha=0.5)

    plt.text(80, 85, '高活跃高风险', ha='center', fontsize=10, color='red')
    plt.text(80, 15, '高活跃低风险\n(核心用户)', ha='center', fontsize=10, color='green')
    plt.text(10, 85, '低活跃高风险\n(流失预警)', ha='center', fontsize=10, color='red')
    plt.text(10, 15, '低活跃低风险', ha='center', fontsize=10, color='gray')

    plt.title('用户分群矩阵 - 活跃度 vs 流失风险', fontsize=14)
    plt.xlabel('预测活跃度评分', fontsize=12)
    plt.ylabel('流失风险评分', fontsize=12)
    plt.legend()
    plt.grid(alpha=0.3)
    plt.tight_layout()

    buf = BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close()

    return buf


def fig_to_base64(fig_buf: BytesIO) -> str:
    return base64.b64encode(fig_buf.read()).decode('utf-8')


if __name__ == '__main__':
    from data_generator import generate_all_data
    from feature_engineering import build_feature_matrix, select_features_by_importance
    from model_training import train_full_pipeline

    print("生成模拟数据...")
    behavior_df, labels_df, channel_df, user_cycles = generate_all_data(n_users=100, history_days=30)

    print("构建特征矩阵...")
    feature_matrix, all_feature_cols = build_feature_matrix(behavior_df, labels_df, user_cycles=user_cycles, channel_df=channel_df)
    top_features = select_features_by_importance(feature_matrix, all_feature_cols, top_k=30)

    print("训练模型...")
    model, eval_results = train_full_pipeline(feature_matrix, top_features)

    print("预测...")
    predictions = model.predict(feature_matrix, top_features)

    print("\n=== 1. 活跃度归因测试 ===")
    X = feature_matrix[top_features].fillna(0)
    shap_analyzer = SHAPAnalyzer(model.model, top_features)
    shap_analyzer.initialize_explainer(X.values)

    attributor = ActivityAttributor(shap_analyzer, feature_matrix)
    sample_user = feature_matrix['user_id'].iloc[0]
    attr_result = attributor.attribute_user(sample_user, top_k=5)
    print(f"\n用户 {sample_user} 归因总结: {attr_result['summary']}")
    print("Top 3 关键行为:")
    for a in attr_result['attributions'][:3]:
        print(f"  - {a['behavior']}: {a['direction_label']} (强度: {a['impact_label']}, SHAP: {a['shap_value']})")

    print("\n=== 2. 个性化文案生成测试 ===")
    copy_gen = CopyGenerator(feature_matrix, behavior_df)
    copy_result = copy_gen.generate_copy(sample_user, attr_result)
    print(f"\n语气: {copy_result['tone']}")
    print(f"问候语: {copy_result['greeting']}")
    print(f"主推文案: {copy_result['primary_copy']}")
    print("备选文案:")
    for c in copy_result['copies']:
        print(f"  [{c['behavior_type']}-{c['level_label']}] {c['copy']} (指标: {c['metric_value']})")

    print("\n=== 3. 群组对比测试 ===")
    comparator = GroupComparator(feature_matrix)
    compare_df = comparator.get_comparison_dataframe()
    print("\n群组对比指标:")
    print(compare_df.to_string(index=False))

    print("\n差异洞察:")
    insights = comparator.get_pattern_insights()
    for ins in insights:
        print(f"  [{ins['severity']}] {ins['insight']} → {ins['recommendation']}")

    print("\n=== 全部测试通过! ===")
