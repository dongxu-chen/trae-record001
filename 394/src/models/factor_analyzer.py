import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
import shap


class FactorAnalyzer:
    def __init__(self):
        self.factor_weights = {
            'exercise': 0.18,
            'exercise_history': 0.12,
            'caffeine': 0.15,
            'alcohol': 0.15,
            'stress': 0.25,
            'bedtime_consistency': 0.15
        }
        self.lag_decay = [0.5, 0.3, 0.2]

    def analyze_lifestyle_impact(self, lifestyle_factors, sleep_score, history_factors=None):
        exercise_impact = self._analyze_exercise_impact(
            lifestyle_factors.get('exercise_minutes', 0),
            lifestyle_factors.get('exercise_intensity', 'moderate')
        )
        caffeine_impact = self._analyze_caffeine_impact(
            lifestyle_factors.get('caffeine_intake', 0)
        )
        alcohol_impact = self._analyze_alcohol_impact(
            lifestyle_factors.get('alcohol_intake', 0)
        )
        stress_impact = self._analyze_stress_impact(
            lifestyle_factors.get('stress_level', 5)
        )
        bedtime_impact = self._analyze_bedtime_consistency(
            lifestyle_factors.get('bedtime_consistency', 5)
        )

        exercise_history_impact = None
        if history_factors:
            exercise_history_impact = self._analyze_exercise_history_impact(
                history_factors.get('exercise_minutes_1d', 0),
                history_factors.get('exercise_minutes_2d', 0),
                history_factors.get('exercise_minutes_3d', 0),
                lifestyle_factors.get('exercise_intensity', 'moderate')
            )

        total_impact = {
            'exercise': exercise_impact,
            'caffeine': caffeine_impact,
            'alcohol': alcohol_impact,
            'stress': stress_impact,
            'bedtime_consistency': bedtime_impact
        }
        if exercise_history_impact:
            total_impact['exercise_history'] = exercise_history_impact

        attribution = self._calculate_attribution(total_impact, sleep_score)
        return {
            'factor_impacts': total_impact,
            'attribution': attribution,
            'key_drivers': self._identify_key_drivers(total_impact),
            'cumulative_exercise': self._calculate_cumulative_exercise(
                lifestyle_factors, history_factors
            )
        }

    def _analyze_exercise_impact(self, minutes, intensity):
        intensity_scores = {'low': 0.5, 'moderate': 1.0, 'high': 1.5}
        intensity_factor = intensity_scores.get(intensity, 1.0)
        if minutes == 0:
            score = 70
            direction = 'neutral'
            description = '今天没有进行运动，适量运动可以改善睡眠质量。'
        elif minutes < 20:
            score = 78
            direction = 'neutral'
            description = '轻度运动对睡眠有一定帮助，建议增加至30分钟以上。'
        elif minutes < 45:
            score = 90
            direction = 'positive'
            description = '运动量适中，对睡眠有积极影响。'
        elif minutes < 75:
            score = 95
            direction = 'positive'
            description = '充足的运动对睡眠非常有益。'
        elif minutes < 120:
            score = 88
            direction = 'neutral'
            description = '运动时间较长，注意避免睡前3小时内剧烈运动。'
        else:
            score = 75
            direction = 'negative'
            description = '运动时间过长可能导致疲劳累积，影响睡眠恢复质量。'
        score = min(100, score * intensity_factor)
        return {
            'score': score,
            'direction': direction,
            'description': description,
            'minutes': minutes,
            'intensity': intensity
        }

    def _analyze_exercise_history_impact(self, day1_min, day2_min, day3_min, intensity):
        history_minutes = [day3_min, day2_min, day1_min]
        weighted_avg = sum(m * w for m, w in zip(history_minutes, self.lag_decay))
        total_3day = sum(history_minutes)
        consistency = 1 - np.std(history_minutes) / (np.mean(history_minutes) + 1)
        consistency = max(0, min(1, consistency))
        if weighted_avg == 0:
            score = 65
            direction = 'neutral'
            description = '近3天均未运动，身体活动不足会影响睡眠质量。'
        elif weighted_avg < 20:
            score = 75
            direction = 'neutral'
            description = '近3天运动较少，建议保持每日至少30分钟的运动量。'
        elif weighted_avg < 50:
            score = 88
            direction = 'positive'
            description = '近3天运动量适中，持续保持有助于改善睡眠质量。'
        elif weighted_avg < 90:
            score = 92
            direction = 'positive'
            description = '近3天运动充足，对睡眠有持续的积极影响。'
        else:
            score = 85
            direction = 'neutral'
            description = '近3天运动量较大，注意避免过度疲劳。'
        if consistency > 0.7:
            score = min(100, score + 5)
            consistency_desc = ' 运动习惯规律，效果更佳。'
        else:
            consistency_desc = ' 建议保持每日规律运动。'
        return {
            'score': score,
            'direction': direction,
            'description': description + consistency_desc,
            'avg_minutes': weighted_avg,
            'total_3day': total_3day,
            'consistency': consistency,
            'daily_minutes': history_minutes
        }

    def _analyze_caffeine_impact(self, intake_level):
        if intake_level == 0:
            score = 100
            direction = 'positive'
            description = '未摄入咖啡因，这对睡眠非常有利。'
        elif intake_level == 1:
            score = 85
            direction = 'neutral'
            description = '少量咖啡因，建议下午2点后避免摄入。'
        elif intake_level == 2:
            score = 70
            direction = 'negative'
            description = '中等量咖啡因，可能会影响入睡时间和深睡质量。'
        elif intake_level == 3:
            score = 55
            direction = 'negative'
            description = '咖啡因摄入较多，严重影响睡眠质量，建议减少摄入量。'
        else:
            score = 40
            direction = 'negative'
            description = '咖啡因摄入过多，睡眠质量将受到严重影响。'
        return {
            'score': score,
            'direction': direction,
            'description': description,
            'intake_level': intake_level
        }

    def _analyze_alcohol_impact(self, intake_level):
        if intake_level == 0:
            score = 100
            direction = 'positive'
            description = '未饮酒，这对睡眠质量非常好。'
        elif intake_level == 1:
            score = 72
            direction = 'negative'
            description = '少量饮酒可能帮助入睡，但会显著影响REM睡眠和睡眠连续性。'
        elif intake_level == 2:
            score = 55
            direction = 'negative'
            description = '饮酒量较大，严重破坏睡眠结构和质量，建议戒酒。'
        else:
            score = 35
            direction = 'negative'
            description = '饮酒过量，将严重损害睡眠质量和恢复功能。'
        return {
            'score': score,
            'direction': direction,
            'description': description,
            'intake_level': intake_level
        }

    def _analyze_stress_impact(self, stress_level):
        if stress_level <= 2:
            score = 98
            direction = 'positive'
            description = '压力水平很低，身心放松非常有利于睡眠。'
        elif stress_level <= 4:
            score = 88
            direction = 'neutral'
            description = '压力较低，保持良好状态即可。'
        elif stress_level <= 6:
            score = 75
            direction = 'neutral'
            description = '压力适中，建议睡前进行简单的放松练习。'
        elif stress_level <= 8:
            score = 60
            direction = 'negative'
            description = '压力较高，可能导致入睡困难和睡眠浅，建议学习压力管理技巧。'
        else:
            score = 40
            direction = 'negative'
            description = '压力非常高，严重影响睡眠质量，建议寻求专业帮助或进行深度放松训练。'
        return {
            'score': score,
            'direction': direction,
            'description': description,
            'stress_level': stress_level
        }

    def _analyze_bedtime_consistency(self, consistency_score):
        if consistency_score >= 9:
            score = 98
            direction = 'positive'
            description = '作息非常规律，这是高质量睡眠的基础。'
        elif consistency_score >= 7:
            score = 90
            direction = 'positive'
            description = '作息比较规律，继续保持。'
        elif consistency_score >= 5:
            score = 78
            direction = 'neutral'
            description = '作息规律性一般，建议固定入睡和起床时间。'
        elif consistency_score >= 3:
            score = 65
            direction = 'negative'
            description = '作息不规律，会影响生物钟和睡眠质量。'
        else:
            score = 45
            direction = 'negative'
            description = '作息严重不规律，将导致睡眠周期紊乱。'
        return {
            'score': score,
            'direction': direction,
            'description': description,
            'consistency_score': consistency_score
        }

    def _calculate_cumulative_exercise(self, lifestyle_factors, history_factors):
        today = lifestyle_factors.get('exercise_minutes', 0)
        if history_factors:
            d1 = history_factors.get('exercise_minutes_1d', 0)
            d2 = history_factors.get('exercise_minutes_2d', 0)
            d3 = history_factors.get('exercise_minutes_3d', 0)
            weighted = today * self.lag_decay[0] + d1 * self.lag_decay[1] + d2 * self.lag_decay[2]
            total = today + d1 + d2 + d3
            daily_values = [today, d1, d2, d3]
            consistency = 1 - np.std(daily_values) / (np.mean(daily_values) + 1)
            consistency = max(0, min(1, consistency))
            return {
                'weighted_score': weighted,
                'total_4day': total,
                'daily_values': daily_values,
                'consistency': consistency,
                'trend': 'upward' if today > np.mean([d1, d2, d3]) else 'downward' if today < np.mean([d1, d2, d3]) else 'stable'
            }
        return {
            'weighted_score': today,
            'total_4day': today,
            'daily_values': [today],
            'consistency': 1.0,
            'trend': 'stable'
        }

    def _calculate_attribution(self, impacts, sleep_score):
        scores = {factor: data['score'] for factor, data in impacts.items()}
        weights = {}
        for factor in impacts:
            if factor in self.factor_weights:
                weights[factor] = self.factor_weights[factor]
            else:
                weights[factor] = 0.15
        total_weight = sum(weights.values())
        weights = {k: v / total_weight for k, v in weights.items()}
        attribution = {}
        total_deviation = sum((100 - scores[f]) * weights[f] for f in impacts)
        for factor in impacts:
            if total_deviation > 0:
                contribution_pct = (100 - scores[factor]) * weights[factor] / total_deviation * 100
            else:
                contribution_pct = 0
            attribution[factor] = {
                'contribution_percent': contribution_pct,
                'impact_magnitude': 100 - scores[factor],
                'factor_score': scores[factor],
                'weight': weights[factor]
            }
        return attribution

    def _identify_key_drivers(self, impacts):
        negative_factors = []
        positive_factors = []
        for factor, data in impacts.items():
            if data['direction'] == 'negative':
                negative_factors.append((factor, data['score'], data['description']))
            elif data['direction'] == 'positive':
                positive_factors.append((factor, data['score'], data['description']))
        negative_factors.sort(key=lambda x: x[1])
        positive_factors.sort(key=lambda x: -x[1])
        return {
            'negative_drivers': negative_factors[:3],
            'positive_drivers': positive_factors[:3]
        }

    def generate_factor_recommendations(self, factor_analysis):
        recommendations = []
        drivers = factor_analysis['key_drivers']
        for factor, score, desc in drivers['negative_drivers']:
            factor_name = {
                'stress': '压力管理',
                'caffeine': '咖啡因摄入',
                'alcohol': '饮酒',
                'bedtime_consistency': '作息规律',
                'exercise': '运动',
                'exercise_history': '运动习惯'
            }.get(factor, factor)
            recommendations.append({
                'category': factor,
                'priority': 'high',
                'type': 'improvement',
                'factor': factor_name,
                'suggestion': desc,
                'expected_improvement': f'{int((100 - score) * 0.3)}分'
            })
        for factor, score, desc in drivers['positive_drivers']:
            factor_name = {
                'stress': '压力管理',
                'caffeine': '咖啡因摄入',
                'alcohol': '饮酒',
                'bedtime_consistency': '作息规律',
                'exercise': '运动',
                'exercise_history': '运动习惯'
            }.get(factor, factor)
            recommendations.append({
                'category': factor,
                'priority': 'low',
                'type': 'maintenance',
                'factor': factor_name,
                'suggestion': desc,
                'expected_impact': '保持良好状态'
            })
        if 'cumulative_exercise' in factor_analysis:
            cum = factor_analysis['cumulative_exercise']
            if cum['consistency'] < 0.5:
                recommendations.append({
                    'category': 'exercise_consistency',
                    'priority': 'medium',
                    'type': 'improvement',
                    'factor': '运动规律性',
                    'suggestion': f'近4天运动时间波动较大，建议保持每日至少30分钟的规律运动。当前运动一致性仅为{cum["consistency"]:.0%}。',
                    'expected_improvement': f'{int((1 - cum["consistency"]) * 10)}分'
                })
        return recommendations


class SHAPFactorExplainer:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.explainer = None
        self.feature_names_ = None

    def train_factor_model(self, factor_data, sleep_scores, use_history=False):
        if use_history and isinstance(factor_data, list):
            expanded = []
            for fd in factor_data:
                row = dict(fd)
                if 'history_factors' in fd:
                    for k, v in fd['history_factors'].items():
                        row[k] = v
                expanded.append(row)
            factor_data = expanded
        X = pd.DataFrame(factor_data)
        if 'history_factors' in X.columns:
            X = X.drop('history_factors', axis=1)
        X = X.fillna(X.mean())
        categorical_cols = X.select_dtypes(include=['object']).columns
        for col in categorical_cols:
            X[col] = pd.Categorical(X[col]).codes
        self.feature_names_ = X.columns.tolist()
        y = np.array(sleep_scores)
        X_scaled = self.scaler.fit_transform(X)
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42
        )
        self.model.fit(X_scaled, y)
        self.explainer = shap.TreeExplainer(self.model)
        return {
            'r2': self.model.score(X_scaled, y),
            'feature_count': len(self.feature_names_),
            'feature_names': self.feature_names_
        }

    def explain_factors(self, factor_values, history_factors=None):
        if self.model is None:
            raise ValueError("Model not trained!")
        row = dict(factor_values)
        if history_factors:
            for k, v in history_factors.items():
                row[k] = v
        X = pd.DataFrame([row])
        if 'history_factors' in X.columns:
            X = X.drop('history_factors', axis=1)
        for col in X.select_dtypes(include=['object']).columns:
            X[col] = 0
        for col in self.feature_names_:
            if col not in X.columns:
                X[col] = 0
        X = X[self.feature_names_]
        X = X.fillna(0)
        X_scaled = self.scaler.transform(X)
        shap_values = self.explainer.shap_values(X_scaled)
        explanation = pd.DataFrame({
            'factor': self.feature_names_,
            'value': X.iloc[0].values,
            'shap_value': shap_values[0],
            'abs_shap': np.abs(shap_values[0])
        }).sort_values('abs_shap', ascending=False)
        return explanation
