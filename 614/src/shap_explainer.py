import shap
import numpy as np
import pandas as pd
import joblib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class PersonalizedDrivingAnalyzer:
    def __init__(self):
        self.driving_dimensions = {
            '加速习惯': {
                'features': ['纵向加速度均值(m/s²)', '纵向加速度标准差(m/s²)', '急加速事件次数', 
                            '大油门持续占比', '加速度变化率均值(m/s³)', '激进驾驶指数'],
                'weights': {'急加速事件次数': 0.3, '纵向加速度均值(m/s²)': 0.25, 
                           '大油门持续占比': 0.2, '加速度变化率均值(m/s³)': 0.15,
                           '纵向加速度标准差(m/s²)': 0.1},
                'thresholds': {'good': 0.3, 'warning': 0.6},
                'description': '分析您的加速习惯是否平稳，是否存在急加速、地板油等费油行为'
            },
            '刹车习惯': {
                'features': ['急刹车事件次数', '刹车频率', '加减速切换频率(次/小时)', '加减速能耗指数'],
                'weights': {'急刹车事件次数': 0.35, '刹车频率': 0.3, 
                           '加减速切换频率(次/小时)': 0.2, '加减速能耗指数': 0.15},
                'thresholds': {'good': 0.3, 'warning': 0.6},
                'description': '分析您的刹车习惯是否合理，是否存在不必要的频繁刹车'
            },
            '变道习惯': {
                'features': ['横向加速度均值(m/s²)', '横向加速度标准差(m/s²)', '急变道事件次数', '总激烈事件'],
                'weights': {'急变道事件次数': 0.4, '横向加速度均值(m/s²)': 0.3,
                           '横向加速度标准差(m/s²)': 0.2, '总激烈事件': 0.1},
                'thresholds': {'good': 0.3, 'warning': 0.6},
                'description': '分析您的变道习惯是否平稳，是否存在频繁变道和急打方向'
            },
            '怠速习惯': {
                'features': ['怠速时间占比', '怠速损失指数'],
                'weights': {'怠速时间占比': 0.6, '怠速损失指数': 0.4},
                'thresholds': {'good': 0.15, 'warning': 0.25},
                'description': '分析您的怠速时间是否过长，长时间怠速会显著增加油耗'
            },
            '巡航习惯': {
                'features': ['定速巡航占比', '经济驾驶指数', '驾驶平稳性指数'],
                'weights': {'定速巡航占比': 0.4, '经济驾驶指数': 0.35, '驾驶平稳性指数': 0.25},
                'thresholds': {'good': 0.7, 'warning': 0.4},
                'description': '分析您是否充分利用定速巡航，保持匀速行驶是节油的关键'
            },
            '油门效率': {
                'features': ['油门效率', '加速度能量', '三维加速度模'],
                'weights': {'油门效率': 0.5, '加速度能量': 0.3, '三维加速度模': 0.2},
                'thresholds': {'good': 0.7, 'warning': 0.4},
                'description': '分析您的油门控制是否精准，线性控制比猛踩油门更省油'
            }
        }
        
        self.improvement_tips = {
            '加速习惯': {
                'bad': [
                    '您的加速习惯较为激进，急加速次数较多。建议：',
                    '  • 绿灯起步时平稳踩油门，避免地板油',
                    '  • 加速过程保持线性，逐步提升车速',
                    '  • 预判路况，提前加速而非临阵猛踩',
                    '  • 使用ECO模式（如有），限制加速响应',
                    '预期节油效果: 0.5-1.5 L/100km'
                ],
                'medium': [
                    '您的加速习惯基本合理，但仍有改进空间：',
                    '  • 尝试更平缓地踩油门，感受车辆动力输出',
                    '  • 高速行驶时避免不必要的加速超车',
                    '预期节油效果: 0.3-0.8 L/100km'
                ],
                'good': [
                    '您的加速习惯非常好！继续保持：',
                    '  • 平稳线性的加速方式',
                    '  • 合理控制加速时机',
                    '这是一项优秀的节油习惯！'
                ]
            },
            '刹车习惯': {
                'bad': [
                    '您的刹车习惯需要改善，急刹车和频繁刹车较多：',
                    '  • 保持足够的安全车距（至少2秒）',
                    '  • 提前预判路况，松开油门利用发动机制动',
                    '  • 避免跟车过近，减少紧急刹车',
                    '  • 红绿灯前提前松油门滑行',
                    '预期节油效果: 0.4-1.2 L/100km'
                ],
                'medium': [
                    '您的刹车习惯基本正常，可以进一步优化：',
                    '  • 增加跟车距离，给制动留有余地',
                    '  • 下坡路段利用挡位控制车速',
                    '预期节油效果: 0.2-0.6 L/100km'
                ],
                'good': [
                    '您的刹车习惯很优秀！继续保持：',
                    '  • 预判式驾驶，减少紧急制动',
                    '  • 合理利用发动机制动',
                    '这不仅省油，也更安全！'
                ]
            },
            '变道习惯': {
                'bad': [
                    '您的变道较为频繁且激进，建议：',
                    '  • 规划好路线，减少不必要的变道',
                    '  • 变道前提前打转向灯，平稳转向',
                    '  • 避免蛇形行驶，保持车道内居中行驶',
                    '  • 高速上减少超车次数，保持稳定车速',
                    '预期节油效果: 0.3-1.0 L/100km'
                ],
                'medium': [
                    '您的变道习惯基本正常，可优化：',
                    '  • 每次变道前确认安全，平稳操作',
                    '  • 避免紧贴邻车变道',
                    '预期节油效果: 0.2-0.5 L/100km'
                ],
                'good': [
                    '您的变道习惯非常好！继续保持：',
                    '  • 平稳转向，路线规划合理',
                    '  • 变道次数适中，不随意变道',
                    '保持稳定的行驶路线是节油的好习惯！'
                ]
            },
            '怠速习惯': {
                'bad': [
                    '您的怠速时间过长，这会显著增加油耗：',
                    '  • 停车超过1分钟建议熄火（红绿灯、等人）',
                    '  • 避免原地热车过久，30秒即可起步',
                    '  • 使用自动启停功能（如有）',
                    '  • 空调使用时避免长时间怠速',
                    '预期节油效果: 0.5-2.0 L/100km'
                ],
                'medium': [
                    '您的怠速时间偏长，建议：',
                    '  • 长时间等待时主动熄火',
                    '  • 减少热车时间',
                    '预期节油效果: 0.3-1.0 L/100km'
                ],
                'good': [
                    '您的怠速控制很好！继续保持：',
                    '  • 避免不必要的怠速',
                    '  • 合理使用自动启停',
                    '怠速油耗是最浪费的，您做得很好！'
                ]
            },
            '巡航习惯': {
                'bad': [
                    '您很少使用定速巡航，建议：',
                    '  • 高速和快速路上开启定速巡航',
                    '  • 保持稳定的车速，避免频繁加减速',
                    '  • 在车流稳定的路段使用自动跟车功能（如有）',
                    '预期节油效果: 0.4-1.2 L/100km'
                ],
                'medium': [
                    '您对定速巡航的使用尚可，可增加：',
                    '  • 在适用路段更多使用定速巡航',
                    '  • 保持经济车速（通常80-100km/h）',
                    '预期节油效果: 0.2-0.6 L/100km'
                ],
                'good': [
                    '您的巡航习惯非常好！继续保持：',
                    '  • 充分利用定速巡航',
                    '  • 保持稳定的经济车速',
                    '匀速行驶是最省油的方式！'
                ]
            },
            '油门效率': {
                'bad': [
                    '您的油门控制不够精细，建议：',
                    '  • 学习"像踩鸡蛋一样轻"踩油门',
                    '  • 保持油门开度稳定，避免忽大忽小',
                    '  • 上坡时提前给油，保持均匀动力',
                    '  • 避免油门到底的情况（除非必要）',
                    '预期节油效果: 0.4-1.0 L/100km'
                ],
                'medium': [
                    '您的油门控制基本合理，可优化：',
                    '  • 尝试更细腻地控制油门',
                    '  • 保持稳定的动力输出',
                    '预期节油效果: 0.2-0.5 L/100km'
                ],
                'good': [
                    '您的油门控制非常精准！继续保持：',
                    '  • 细腻的油门控制',
                    '  • 稳定的动力输出',
                    '这是驾驶技术高超的体现！'
                ]
            }
        }

    def analyze_driving_behavior(self, raw_input_dict, shap_explanation):
        analysis_result = {
            'overall_score': 0,
            'dimensions': {},
            'weaknesses': [],
            'strengths': [],
            'personalized_advice': []
        }
        
        dimension_scores = []
        
        for dim_name, dim_info in self.driving_dimensions.items():
            features = dim_info['features']
            weights = dim_info['weights']
            thresholds = dim_info['thresholds']
            
            score = 0
            total_weight = 0
            feature_scores = {}
            
            for feature in features:
                if feature in raw_input_dict:
                    raw_value = raw_input_dict[feature]
                    weight = weights.get(feature, 0.1)
                    total_weight += weight
                    
                    normalized_score = self._normalize_feature_score(feature, raw_value, dim_name)
                    feature_scores[feature] = {
                        'raw_value': raw_value,
                        'normalized_score': normalized_score,
                        'weight': weight
                    }
                    score += normalized_score * weight
            
            if total_weight > 0:
                score = score / total_weight
            
            status = self._get_status(score, thresholds, dim_name)
            
            shap_impact = 0
            for feature in features:
                shap_match = shap_explanation[shap_explanation['feature'] == feature]
                if not shap_match.empty:
                    shap_impact += shap_match['shap_value'].values[0]
            
            dimension_scores.append(score * 100)
            
            dimension_analysis = {
                'score': round(score * 100, 1),
                'status': status,
                'description': dim_info['description'],
                'shap_impact': round(shap_impact, 2),
                'feature_scores': feature_scores,
                'advice': self._get_dimension_advice(dim_name, status)
            }
            
            analysis_result['dimensions'][dim_name] = dimension_analysis
            
            if status == 'bad':
                analysis_result['weaknesses'].append({
                    'dimension': dim_name,
                    'score': round(score * 100, 1),
                    'shap_impact': round(shap_impact, 2),
                    'priority': 'high'
                })
            elif status == 'good':
                analysis_result['strengths'].append({
                    'dimension': dim_name,
                    'score': round(score * 100, 1),
                    'shap_impact': round(shap_impact, 2)
                })
        
        analysis_result['overall_score'] = round(np.mean(dimension_scores), 1)
        analysis_result['weaknesses'].sort(key=lambda x: -abs(x['shap_impact']))
        
        analysis_result['personalized_advice'] = self._generate_personalized_advice(
            analysis_result['weaknesses'], 
            analysis_result['strengths'],
            shap_explanation
        )
        
        return analysis_result
    
    def _normalize_feature_score(self, feature, value, dimension):
        if dimension == '巡航习惯' or dimension == '油门效率':
            if '定速巡航' in feature or '经济驾驶' in feature or '驾驶平稳性' in feature or '油门效率' in feature:
                return min(1.0, max(0.0, value / 1.0))
            else:
                return min(1.0, max(0.0, 1.0 - value / 10.0))
        else:
            if '急加速' in feature or '急刹车' in feature or '急变道' in feature:
                return min(1.0, max(0.0, 1.0 - value / 10.0))
            elif '怠速时间' in feature or '怠速损失' in feature:
                return min(1.0, max(0.0, 1.0 - value / 0.5))
            elif '均值' in feature or '标准差' in feature:
                return min(1.0, max(0.0, 1.0 - value / 5.0))
            elif '切换频率' in feature or '能耗指数' in feature:
                return min(1.0, max(0.0, 1.0 - value / 30.0))
            elif '大油门' in feature:
                return min(1.0, max(0.0, 1.0 - value / 0.5))
            elif '激进驾驶' in feature:
                return min(1.0, max(0.0, 1.0 - value / 10.0))
            elif '总激烈事件' in feature:
                return min(1.0, max(0.0, 1.0 - value / 20.0))
            elif '加速度能量' in feature or '三维加速度' in feature:
                return min(1.0, max(0.0, 1.0 - value / 20.0))
            else:
                return min(1.0, max(0.0, 1.0 - value / 1.0))
    
    def _get_status(self, score, thresholds, dimension):
        if dimension in ['巡航习惯', '油门效率']:
            if score >= thresholds['good']:
                return 'good'
            elif score <= thresholds['warning']:
                return 'bad'
            else:
                return 'medium'
        else:
            if score <= thresholds['good']:
                return 'good'
            elif score >= thresholds['warning']:
                return 'bad'
            else:
                return 'medium'
    
    def _get_dimension_advice(self, dimension, status):
        if status == 'bad':
            return self.improvement_tips[dimension]['bad']
        elif status == 'medium':
            return self.improvement_tips[dimension]['medium']
        else:
            return self.improvement_tips[dimension]['good']
    
    def _generate_personalized_advice(self, weaknesses, strengths, shap_explanation):
        advice = []
        
        if weaknesses:
            advice.append("🎯 您的驾驶行为弱点分析：")
            advice.append("")
            
            total_saving = 0
            for i, weak in enumerate(weaknesses[:3], 1):
                dim_name = weak['dimension']
                impact = abs(weak['shap_impact'])
                saving_estimate = impact * 0.8
                total_saving += saving_estimate
                
                advice.append(f"{i}. **{dim_name}** - 得分: {weak['score']}/100")
                advice.append(f"   对油耗影响: +{impact:.2f} L/100km")
                advice.append(f"   潜在节油: ~{saving_estimate:.2f} L/100km")
                advice.append("")
            
            advice.append(f"💡 如能改善以上{len(weaknesses[:3])}项，预计可节油 **{total_saving:.1f}-{total_saving*1.5:.1f} L/100km**")
            advice.append("")
        
        if strengths:
            advice.append("✅ 您做得好的方面：")
            for s in strengths:
                advice.append(f"   • {s['dimension']} (得分: {s['score']}/100)")
            advice.append("")
        
        advice.append("📋 个性化改进建议：")
        advice.append("")
        
        if weaknesses:
            top_weakness = weaknesses[0]['dimension']
            advice.append(f"**首要改进：{top_weakness}**")
            for tip in self.improvement_tips[top_weakness]['bad']:
                advice.append(tip)
            advice.append("")
            
            if len(weaknesses) > 1:
                second_weakness = weaknesses[1]['dimension']
                advice.append(f"**次要改进：{second_weakness}**")
                for tip in self.improvement_tips[second_weakness]['bad'][:3]:
                    advice.append(tip)
                advice.append("")
        
        advice.append("📊 综合驾驶习惯评价：")
        overall_score = np.mean([w['score'] for w in weaknesses] + [s['score'] for s in strengths]) if (weaknesses or strengths) else 50
        if overall_score >= 80:
            advice.append("   🌟 您的驾驶习惯非常优秀，是节油高手！")
        elif overall_score >= 60:
            advice.append("   👍 您的驾驶习惯良好，继续保持并改进薄弱项")
        elif overall_score >= 40:
            advice.append("   ⚡ 您的驾驶习惯有较大提升空间，建议采纳改进建议")
        else:
            advice.append("   🔧 您的驾驶习惯需要重点改善，这将显著降低油耗")
        
        return advice
    
    def plot_radar_chart(self, analysis_result, save_path=None):
        dimensions = list(self.driving_dimensions.keys())
        scores = [analysis_result['dimensions'][d]['score'] for d in dimensions]
        
        angles = np.linspace(0, 2 * np.pi, len(dimensions), endpoint=False).tolist()
        scores += scores[:1]
        angles += angles[:1]
        
        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        
        ax.plot(angles, scores, 'o-', linewidth=2, label='驾驶行为得分', color='#FF6B6B')
        ax.fill(angles, scores, alpha=0.25, color='#FF6B6B')
        
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(dimensions, fontsize=11)
        ax.set_ylim(0, 100)
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'], fontsize=9)
        ax.grid(True, alpha=0.3)
        
        good_area = plt.Circle((0, 0), 70, transform=ax.transData._b, color='green', alpha=0.1)
        medium_area = plt.Circle((0, 0), 40, transform=ax.transData._b, color='yellow', alpha=0.1)
        bad_area = plt.Circle((0, 0), 0, transform=ax.transData._b, color='red', alpha=0.1)
        ax.add_artist(good_area)
        ax.add_artist(medium_area)
        
        plt.title(f'驾驶行为六维分析图\n综合得分: {analysis_result["overall_score"]}/100', 
                 fontsize=14, pad=20)
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
            return save_path
        return fig

class FuelConsumptionExplainer:
    def __init__(self, model, feature_engineer):
        self.model = model
        self.fe = feature_engineer
        self.explainer = None
        self.feature_names = feature_engineer.feature_names
        self.driving_analyzer = PersonalizedDrivingAnalyzer()
        
    def fit_explainer(self, X_sample):
        self.explainer = shap.TreeExplainer(self.model)
        self.shap_values = self.explainer.shap_values(X_sample)
        self.expected_value = self.explainer.expected_value
        return self
    
    def get_feature_importance(self, top_n=10):
        if self.shap_values is None:
            raise ValueError("请先调用 fit_explainer 方法")
        
        feature_importance = pd.DataFrame({
            'feature': self.feature_names,
            'shap_importance': np.abs(self.shap_values).mean(axis=0)
        }).sort_values('shap_importance', ascending=False)
        
        return feature_importance.head(top_n)
    
    def get_single_prediction_explanation(self, X_single):
        if self.explainer is None:
            raise ValueError("请先调用 fit_explainer 方法")
        
        shap_single = self.explainer.shap_values(X_single)
        
        explanation = pd.DataFrame({
            'feature': self.feature_names,
            'feature_value': X_single.values[0],
            'shap_value': shap_single[0]
        }).sort_values('shap_value', key=lambda x: x.abs(), ascending=False)
        
        return explanation
    
    def get_personalized_driving_analysis(self, X_single, raw_input_dict):
        explanation = self.get_single_prediction_explanation(X_single)
        analysis = self.driving_analyzer.analyze_driving_behavior(raw_input_dict, explanation)
        return analysis
    
    def plot_summary_bar(self, save_path=None):
        if self.shap_values is None:
            raise ValueError("请先调用 fit_explainer 方法")
        
        plt.figure(figsize=(10, 8))
        shap.summary_plot(
            self.shap_values,
            features=pd.DataFrame(columns=self.feature_names),
            plot_type='bar',
            show=False
        )
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
            return save_path
        return plt
    
    def plot_waterfall(self, X_single, save_path=None, max_display=10):
        if self.explainer is None:
            raise ValueError("请先调用 fit_explainer 方法")
        
        shap_single = self.explainer.shap_values(X_single)
        
        plt.figure(figsize=(10, 8))
        shap.waterfall_plot(
            shap.Explanation(
                values=shap_single[0],
                base_values=self.expected_value,
                data=X_single.values[0],
                feature_names=self.feature_names
            ),
            max_display=max_display,
            show=False
        )
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            plt.close()
            return save_path
        return plt
    
    def plot_driving_radar(self, analysis_result, save_path=None):
        return self.driving_analyzer.plot_radar_chart(analysis_result, save_path)
