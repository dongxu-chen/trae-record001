import os
import numpy as np
import pandas as pd
from datetime import datetime
from config import RANDOM_SEED, ACTOR_POPULARITY, REVENUE_MODEL_PARAMS, PLATFORMS
from utils import smooth_curve, detect_peaks, calculate_trend, calculate_rmse, calculate_mape
from xgboost_model import XGBoostRatingPredictor
from lstm_model import TimeIntervalLSTM
from data_generator import (
    generate_drama_basic_info, generate_episodic_ratings, generate_social_media_data,
    generate_trailer_heat, predict_premiere_rating
)
from sentiment_analyzer import generate_episode_comments_batch, aggregate_episode_sentiment, get_top_keywords

np.random.seed(RANDOM_SEED)

class RevenueModel:
    """
    收益模型 - 综合收视率、版权费、制作成本进行决策
    
    收入来源：
    1. 广告收入 - 基于收视率
    2. 平台版权费 - 基于平台和剧集质量
    3. 海外发行收入 - 按比例计算
    4. IP衍生收入 - 按比例计算
    
    成本构成：
    1. 制作成本 - 制作预算
    2. 运营成本 - 按比例计算
    3. 税收 - 按税率计算
    
    决策指标：
    1. ROI (投资回报率)
    2. 投资回收期
    3. 净现值(NPV)
    """
    
    def __init__(self, params=None):
        self.params = params or REVENUE_MODEL_PARAMS
    
    def calculate_ad_revenue(self, avg_rating, num_episodes, platform):
        """
        计算广告收入
        
        公式：
        广告收入 = 平均收视率 × 每点收视率收入系数 × 每集广告时长 × 集数
        """
        coef = self.params['rating_revenue_coef']
        ad_duration = self.params['ad_duration_per_episode']
        price_per_second = self.params['avg_ad_price_per_second']
        
        platform_factor = {
            '湖南卫视': 1.5, '浙江卫视': 1.3, '东方卫视': 1.35, '江苏卫视': 1.2,
            '北京卫视': 1.15, '腾讯视频': 1.0, '爱奇艺': 0.95, '优酷': 0.9
        }.get(platform, 1.0)
        
        ad_revenue_per_episode = avg_rating * coef * ad_duration * price_per_second * platform_factor
        total_ad_revenue = ad_revenue_per_episode * num_episodes
        
        return {
            'per_episode': round(ad_revenue_per_episode, 2),
            'total': round(total_ad_revenue, 2),
            'platform_factor': platform_factor
        }
    
    def calculate_copyright_fee(self, drama_info, avg_rating, peak_rating):
        """
        计算平台版权费
        
        公式：
        版权费 = 基础费用 × (1 + 收视率系数 + 演员系数 + 导演系数)
        单位：元
        """
        base_fee = self.params['platform_fee_min'] + \
                   (self.params['platform_fee_max'] - self.params['platform_fee_min']) * \
                   (avg_rating / 5.0)
        
        rating_bonus = (avg_rating - 1.5) * self.params['rating_bonus_per_point'] if avg_rating > 1.5 else 0
        peak_bonus = (peak_rating - 2.5) * self.params['peak_bonus_per_point'] if peak_rating > 2.5 else 0
        actor_bonus = ACTOR_POPULARITY[drama_info['actor_level']] * self.params['actor_bonus_per_level']
        director_bonus = drama_info['director_reputation'] * self.params['director_bonus_factor']
        sequel_bonus = self.params['sequel_bonus'] if drama_info['is_sequel'] else 0
        
        fee_per_episode = base_fee + rating_bonus + peak_bonus + actor_bonus + director_bonus + sequel_bonus
        total_fee = fee_per_episode * drama_info['num_episodes']
        
        return {
            'base_fee_per_episode': round(base_fee, 2),
            'rating_bonus_per_episode': round(rating_bonus, 2),
            'peak_bonus_per_episode': round(peak_bonus, 2),
            'actor_bonus_per_episode': round(actor_bonus, 2),
            'director_bonus_per_episode': round(director_bonus, 2),
            'sequel_bonus_per_episode': round(sequel_bonus, 2),
            'fee_per_episode': round(fee_per_episode, 2),
            'total': round(total_fee, 2)
        }
    
    def calculate_total_revenue(self, drama_info, predictions, social_df):
        """
        计算总收入
        """
        avg_rating = np.mean(predictions)
        max_rating = np.max(predictions)
        num_episodes = len(predictions)
        platform = drama_info['platform']
        
        ad_revenue = self.calculate_ad_revenue(avg_rating, num_episodes, platform)
        copyright_fee = self.calculate_copyright_fee(drama_info, avg_rating, max_rating)
        
        overseas_ratio = self.params['overseas_rights_ratio']
        overseas_revenue = copyright_fee['total'] * overseas_ratio
        
        ip_ratio = self.params['ip_derivative_ratio']
        ip_revenue = copyright_fee['total'] * ip_ratio
        
        total_revenue = ad_revenue['total'] + copyright_fee['total'] + overseas_revenue + ip_revenue
        
        return {
            'ad_revenue': ad_revenue,
            'copyright_fee': copyright_fee,
            'overseas_revenue': round(overseas_revenue, 2),
            'ip_derivative_revenue': round(ip_revenue, 2),
            'total_revenue': round(total_revenue, 2),
            'breakdown': {
                '广告收入': ad_revenue['total'],
                '版权费用': copyright_fee['total'],
                '海外发行': overseas_revenue,
                'IP衍生': ip_revenue
            }
        }
    
    def calculate_total_cost(self, drama_info, total_revenue):
        """
        计算总成本
        """
        production_cost = drama_info['production_budget'] * 10000
        
        operating_cost_ratio = self.params['operating_cost_ratio']
        operating_cost = total_revenue * operating_cost_ratio
        
        tax_rate = self.params['tax_rate']
        pre_tax_profit = total_revenue - production_cost - operating_cost
        tax = max(0, pre_tax_profit * tax_rate)
        
        total_cost = production_cost + operating_cost + tax
        
        return {
            'production_cost': production_cost,
            'operating_cost': round(operating_cost, 2),
            'tax': round(tax, 2),
            'total_cost': round(total_cost, 2)
        }
    
    def calculate_profit_metrics(self, drama_info, predictions, social_df):
        """
        计算所有盈利指标
        """
        revenue = self.calculate_total_revenue(drama_info, predictions, social_df)
        total_rev = revenue['total_revenue']
        
        cost = self.calculate_total_cost(drama_info, total_rev)
        total_cost = cost['total_cost']
        
        net_profit = total_rev - total_cost
        
        roi = net_profit / cost['production_cost'] if cost['production_cost'] > 0 else 0
        
        payback_period = cost['production_cost'] / (net_profit / len(predictions)) if net_profit > 0 else float('inf')
        
        avg_rating = np.mean(predictions)
        profit_per_rating_point = net_profit / (avg_rating * len(predictions)) if avg_rating > 0 else 0
        
        gross_margin = (total_rev - cost['production_cost']) / total_rev if total_rev > 0 else 0
        net_margin = net_profit / total_rev if total_rev > 0 else 0
        
        return {
            'revenue': revenue,
            'cost': cost,
            'net_profit': round(net_profit, 2),
            'roi': round(roi, 4),
            'payback_period_years': round(payback_period / 52, 2) if payback_period != float('inf') else '无法收回',
            'profit_per_rating_point': round(profit_per_rating_point, 2),
            'gross_margin': round(gross_margin, 4),
            'net_margin': round(net_margin, 4),
            'key_ratios': {
                'ROI': f"{roi*100:.2f}%",
                '毛利率': f"{gross_margin*100:.2f}%",
                '净利率': f"{net_margin*100:.2f}%",
                '投资回收期': f"{payback_period/52:.2f}年" if payback_period != float('inf') else "无法收回"
            }
        }
    
    def get_renewal_recommendation_with_revenue(self, drama_info, predictions, social_df, base_score=0):
        """
        基于收益模型的续订建议
        """
        profit_metrics = self.calculate_profit_metrics(drama_info, predictions, social_df)
        
        roi = profit_metrics['roi']
        net_profit = profit_metrics['net_profit']
        payback = profit_metrics['payback_period_years']
        net_margin = profit_metrics['net_margin']
        
        revenue_score = 0
        
        if roi >= self.params['roi_threshold_good']:
            roi_score = 30
        elif roi >= self.params['roi_threshold_normal']:
            roi_score = 20
        elif roi >= 0:
            roi_score = 10
        else:
            roi_score = 0
        
        if net_profit >= 5000 * 10000:
            profit_score = 25
        elif net_profit >= 2000 * 10000:
            profit_score = 18
        elif net_profit >= 500 * 10000:
            profit_score = 10
        elif net_profit >= 0:
            profit_score = 5
        else:
            profit_score = 0
        
        if isinstance(payback, (int, float)) and payback <= self.params['payback_period_max']:
            payback_score = 15
        elif isinstance(payback, (int, float)) and payback <= 5:
            payback_score = 8
        else:
            payback_score = 0
        
        if net_margin >= 0.3:
            margin_score = 20
        elif net_margin >= 0.2:
            margin_score = 15
        elif net_margin >= 0.1:
            margin_score = 8
        elif net_margin >= 0:
            margin_score = 3
        else:
            margin_score = 0
        
        revenue_score = roi_score + profit_score + payback_score + margin_score
        
        avg_rating = np.mean(predictions)
        if avg_rating >= 2.5:
            score_adjust = 1.0
        elif avg_rating >= 1.8:
            score_adjust = 0.9
        else:
            score_adjust = 0.8
        
        final_revenue_score = revenue_score * score_adjust
        
        combined_score = base_score * 0.4 + final_revenue_score * 0.6
        
        if combined_score >= 75:
            recommendation = '强烈建议续订'
            confidence = '高'
        elif combined_score >= 60:
            recommendation = '建议续订'
            confidence = '较高'
        elif combined_score >= 45:
            recommendation = '可考虑续订'
            confidence = '中等'
        elif combined_score >= 30:
            recommendation = '谨慎考虑，建议观察后续表现'
            confidence = '较低'
        else:
            recommendation = '不建议续订'
            confidence = '高'
        
        reasons = []
        if roi >= self.params['roi_threshold_normal']:
            reasons.append(f"投资回报率优异（ROI: {roi*100:.1f}%）")
        if net_profit > 0:
            reasons.append(f"预计盈利 {net_profit/10000:.1f} 万元")
        if isinstance(payback, (int, float)) and payback <= 3:
            reasons.append(f"投资回收期短（{payback:.1f}年）")
        if net_margin >= 0.2:
            reasons.append(f"盈利能力强（净利率: {net_margin*100:.1f}%）")
        if profit_metrics['revenue']['ad_revenue']['total'] > profit_metrics['revenue']['copyright_fee']['total']:
            reasons.append("广告收入贡献突出")
        
        if not reasons:
            reasons.append("收益表现未达预期，需谨慎评估")
        
        return {
            'base_score': round(base_score, 1),
            'revenue_score': round(final_revenue_score, 1),
            'combined_score': round(combined_score, 1),
            'recommendation': recommendation,
            'confidence': confidence,
            'profit_metrics': profit_metrics,
            'revenue_breakdown': profit_metrics['revenue']['breakdown'],
            'cost_breakdown': {
                '制作成本': profit_metrics['cost']['production_cost'],
                '运营成本': profit_metrics['cost']['operating_cost'],
                '税收': profit_metrics['cost']['tax']
            },
            'key_reasons': reasons
        }

class RatingPredictionEngine:
    def __init__(self, xgb_weight=0.55, lstm_weight=0.45):
        self.xgb_predictor = XGBoostRatingPredictor()
        self.lstm_predictor = TimeIntervalLSTM(seq_length=5)
        self.revenue_model = RevenueModel()
        self.xgb_weight = xgb_weight
        self.lstm_weight = lstm_weight
        self.models_trained = False
    
    def train_models(self, num_dramas=50, force_retrain=False):
        if force_retrain or not self.xgb_predictor.is_trained():
            print("Training XGBoost model...")
            self.xgb_predictor.train(num_dramas=num_dramas)
        
        if force_retrain or not self.lstm_predictor.is_trained():
            print("Training LSTM model...")
            self.lstm_predictor.train(num_dramas=num_dramas, epochs=30)
        
        self.models_trained = True
        print("All models trained successfully!")
    
    def load_models(self):
        self.xgb_predictor.load()
        self.lstm_predictor.load()
        self.models_trained = True
    
    def predict(self, drama_info, dates, known_ratings, social_df, episode_idx):
        if not self.models_trained:
            self.load_models()
        
        xgb_pred = self.xgb_predictor.predict(
            drama_info, dates, known_ratings, social_df, episode_idx
        )
        
        lstm_pred = self.lstm_predictor.predict(
            drama_info, dates, known_ratings, social_df, episode_idx
        )
        
        ensemble_pred = self.xgb_weight * xgb_pred + self.lstm_weight * lstm_pred
        
        return {
            'xgb_prediction': round(xgb_pred, 4),
            'lstm_prediction': round(lstm_pred, 4),
            'ensemble_prediction': round(ensemble_pred, 4)
        }
    
    def predict_all_episodes(self, drama_info, dates, initial_ratings, social_df):
        if not self.models_trained:
            self.load_models()
        
        xgb_preds = self.xgb_predictor.predict_all_episodes(
            drama_info, dates, initial_ratings, social_df
        )
        
        lstm_preds = self.lstm_predictor.predict_all_episodes(
            drama_info, dates, initial_ratings, social_df
        )
        
        ensemble_preds = [
            round(self.xgb_weight * x + self.lstm_weight * l, 4)
            for x, l in zip(xgb_preds, lstm_preds)
        ]
        
        return {
            'xgb_predictions': xgb_preds,
            'lstm_predictions': lstm_preds,
            'ensemble_predictions': ensemble_preds
        }
    
    def detect_peak_episodes(self, predictions, threshold=0.15, min_distance=2):
        smoothed = smooth_curve(predictions, window_size=3)
        peaks = detect_peaks(smoothed, threshold=threshold, min_distance=min_distance)
        
        peak_details = []
        for peak_idx in peaks:
            peak_ep = peak_idx + 1
            peak_rating = predictions[peak_idx]
            avg_rating = np.mean(predictions)
            increase_pct = ((peak_rating - avg_rating) / avg_rating) * 100
            
            peak_details.append({
                'episode': peak_ep,
                'predicted_rating': round(peak_rating, 4),
                'average_rating': round(avg_rating, 4),
                'increase_percent': round(increase_pct, 2),
                'confidence': self._calculate_peak_confidence(predictions, peak_idx)
            })
        
        return peak_details
    
    def _calculate_peak_confidence(self, ratings, peak_idx):
        if peak_idx == 0 or peak_idx >= len(ratings) - 1:
            return 0.5
        
        avg = np.mean(ratings)
        neighbors = [ratings[peak_idx - 1], ratings[peak_idx + 1]]
        neighbor_avg = np.mean(neighbors)
        
        local_magnitude = (ratings[peak_idx] - neighbor_avg) / neighbor_avg if neighbor_avg > 0 else 0
        global_magnitude = (ratings[peak_idx] - avg) / avg if avg > 0 else 0
        
        confidence = 0.3 + min(0.35, abs(local_magnitude) * 2) + min(0.35, abs(global_magnitude) * 2)
        return max(0.0, min(1.0, confidence))
    
    def generate_renewal_recommendation(self, drama_info, predictions, social_df, comments_df=None, use_revenue_model=True):
        avg_rating = np.mean(predictions)
        max_rating = np.max(predictions)
        min_rating = np.min(predictions)
        rating_trend = calculate_trend(predictions)
        
        avg_sentiment = social_df['sentiment_score'].mean() if 'sentiment_score' in social_df.columns else 0.5
        avg_search = social_df['search_index'].mean() if 'search_index' in social_df.columns else 500
        post_volume = social_df['post_volume'].sum() if 'post_volume' in social_df.columns else 0
        
        score = 0
        factors = {}
        
        if avg_rating >= 2.5:
            rating_score = 30
        elif avg_rating >= 2.0:
            rating_score = 20
        elif avg_rating >= 1.5:
            rating_score = 10
        else:
            rating_score = 0
        score += rating_score
        factors['avg_rating'] = {'value': round(avg_rating, 3), 'score': rating_score, 'weight': 30}
        
        if rating_trend > 0.02:
            trend_score = 15
        elif rating_trend > 0:
            trend_score = 10
        elif rating_trend > -0.02:
            trend_score = 5
        else:
            trend_score = 0
        score += trend_score
        factors['trend'] = {'value': round(rating_trend, 4), 'score': trend_score, 'weight': 15}
        
        if max_rating >= 3.5:
            peak_score = 10
        elif max_rating >= 3.0:
            peak_score = 7
        elif max_rating >= 2.5:
            peak_score = 4
        else:
            peak_score = 0
        score += peak_score
        factors['peak_rating'] = {'value': round(max_rating, 3), 'score': peak_score, 'weight': 10}
        
        if avg_sentiment >= 0.7:
            sentiment_score = 15
        elif avg_sentiment >= 0.6:
            sentiment_score = 10
        elif avg_sentiment >= 0.5:
            sentiment_score = 5
        else:
            sentiment_score = 0
        score += sentiment_score
        factors['sentiment'] = {'value': round(avg_sentiment, 3), 'score': sentiment_score, 'weight': 15}
        
        actor_score = ACTOR_POPULARITY[drama_info['actor_level']] * 10
        score += actor_score
        factors['actor_level'] = {'value': drama_info['actor_level'], 'score': actor_score, 'weight': 10}
        
        if drama_info['is_sequel']:
            sequel_score = 5
        else:
            sequel_score = 0
        score += sequel_score
        factors['is_sequel'] = {'value': drama_info['is_sequel'], 'score': sequel_score, 'weight': 5}
        
        if avg_search >= 1500:
            search_score = 10
        elif avg_search >= 1000:
            search_score = 6
        elif avg_search >= 500:
            search_score = 3
        else:
            search_score = 0
        score += search_score
        factors['search_index'] = {'value': int(avg_search), 'score': search_score, 'weight': 10}
        
        stability = 1 - (np.std(predictions) / np.mean(predictions) if np.mean(predictions) > 0 else 0)
        stability = max(0, min(1, stability))
        stability_score = stability * 10
        score += stability_score
        factors['stability'] = {'value': round(stability, 3), 'score': round(stability_score, 1), 'weight': 10}
        
        base_result = {
            'total_score': round(score, 1),
            'recommendation': '',
            'confidence': '',
            'factors': factors,
            'summary_stats': {
                'avg_rating': round(avg_rating, 3),
                'max_rating': round(max_rating, 3),
                'min_rating': round(min_rating, 3),
                'rating_trend': round(rating_trend, 4),
                'avg_sentiment': round(avg_sentiment, 3),
                'avg_search_index': int(avg_search),
                'total_post_volume': int(post_volume),
                'stability_index': round(stability, 3)
            },
            'key_reasons': []
        }
        
        reasons = []
        if factors['avg_rating']['score'] >= 20:
            reasons.append(f"平均收视率表现优异（{round(avg_rating, 2)}%）")
        if factors['trend']['score'] >= 10:
            reasons.append("收视率呈上升趋势")
        if factors['sentiment']['score'] >= 10:
            reasons.append(f"观众口碑良好（平均情感分{round(avg_sentiment, 2)}）")
        if factors['peak_rating']['score'] >= 7:
            reasons.append(f"存在收视爆点（最高{round(max_rating, 2)}%）")
        if factors['actor_level']['score'] >= 8:
            reasons.append(f"{drama_info['actor_level']}演员阵容具有号召力")
        if factors['stability']['score'] >= 7:
            reasons.append("收视表现稳定")
        
        if not reasons:
            reasons.append("收视表现平平，需综合其他因素考量")
        
        base_result['key_reasons'] = reasons
        
        if use_revenue_model:
            revenue_result = self.revenue_model.get_renewal_recommendation_with_revenue(
                drama_info, predictions, social_df, base_score=score
            )
            
            base_result['revenue_analysis'] = revenue_result
            base_result['total_score'] = revenue_result['combined_score']
            base_result['recommendation'] = revenue_result['recommendation']
            base_result['confidence'] = revenue_result['confidence']
            base_result['key_reasons'].extend(revenue_result['key_reasons'])
            
            base_result['summary_stats'].update({
                'net_profit_wan': round(revenue_result['profit_metrics']['net_profit'] / 10000, 1),
                'roi': revenue_result['profit_metrics']['roi'],
                'roi_pct': f"{revenue_result['profit_metrics']['roi']*100:.2f}%",
                'payback_period_years': revenue_result['profit_metrics']['payback_period_years'],
                'net_margin': revenue_result['profit_metrics']['net_margin'],
                'net_margin_pct': f"{revenue_result['profit_metrics']['net_margin']*100:.2f}%",
                'total_revenue_wan': round(revenue_result['profit_metrics']['revenue']['total_revenue'] / 10000, 1),
                'total_cost_wan': round(revenue_result['profit_metrics']['cost']['total_cost'] / 10000, 1)
            })
        else:
            if score >= 80:
                base_result['recommendation'] = '强烈建议续订'
                base_result['confidence'] = '高'
            elif score >= 65:
                base_result['recommendation'] = '建议续订'
                base_result['confidence'] = '较高'
            elif score >= 50:
                base_result['recommendation'] = '可考虑续订'
                base_result['confidence'] = '中等'
            elif score >= 35:
                base_result['recommendation'] = '谨慎考虑，建议观察后续表现'
                base_result['confidence'] = '较低'
            else:
                base_result['recommendation'] = '不建议续订'
                base_result['confidence'] = '高'
        
        return base_result
    
    def generate_full_prediction_report(self, drama_info, dates, initial_ratings, social_df, comments_df=None, 
                                         include_trailer_heat=True, use_revenue_model=True):
        if not self.models_trained:
            self.load_models()
        
        predictions = self.predict_all_episodes(drama_info, dates, initial_ratings, social_df)
        
        ensemble_preds = predictions['ensemble_predictions']
        
        peaks = self.detect_peak_episodes(ensemble_preds)
        
        renewal = self.generate_renewal_recommendation(
            drama_info, ensemble_preds, social_df, comments_df, 
            use_revenue_model=use_revenue_model
        )
        
        peak_episodes = [p['episode'] for p in peaks]
        peak_ratings = [p['predicted_rating'] for p in peaks]
        
        known_count = len(initial_ratings)
        
        results_df = pd.DataFrame({
            'episode': list(range(1, len(dates) + 1)),
            'date': dates,
            'day_of_week': [d.strftime('%A') for d in dates],
            'is_weekend': [1 if d.weekday() >= 5 else 0 for d in dates],
            'known_rating': list(initial_ratings) + [None] * (len(dates) - known_count),
            'xgb_prediction': predictions['xgb_predictions'],
            'lstm_prediction': predictions['lstm_predictions'],
            'ensemble_prediction': ensemble_preds,
            'is_peak': [i + 1 in peak_episodes for i in range(len(dates))]
        })
        
        for col in ['post_volume', 'repost_volume', 'like_volume', 'comment_volume', 'search_index', 'sentiment_score']:
            if col in social_df.columns:
                results_df[col] = social_df[col].values
        
        if comments_df is not None:
            sentiment_stats = aggregate_episode_sentiment(comments_df)
            results_df = results_df.merge(
                sentiment_stats[['episode', 'avg_sentiment', 'positive_ratio', 'negative_ratio']],
                on='episode', how='left'
            )
        
        trailer_heat_df = None
        premiere_prediction = None
        if include_trailer_heat:
            trailer_heat_df = generate_trailer_heat(drama_info, days_before_premiere=30)
            premiere_prediction = predict_premiere_rating(drama_info, trailer_heat_df)
        
        time_gate_analysis = None
        if hasattr(self.lstm_predictor, 'get_time_gate_effect'):
            intervals = [1, 2, 3, 5, 7, 14, 30]
            time_gate_analysis = self.lstm_predictor.get_time_gate_effect(intervals)
        
        report = {
            'drama_info': drama_info,
            'predictions': predictions,
            'episode_details': results_df,
            'peak_episodes': peaks,
            'renewal_recommendation': renewal,
            'top_peaks': sorted(peaks, key=lambda x: x['increase_percent'], reverse=True)[:3],
            'prediction_summary': {
                'avg_predicted': round(np.mean(ensemble_preds), 3),
                'max_predicted': round(np.max(ensemble_preds), 3),
                'min_predicted': round(np.min(ensemble_preds), 3),
                'trend': round(calculate_trend(ensemble_preds), 4),
                'total_episodes': len(dates),
                'known_episodes': known_count,
                'predicted_episodes': len(dates) - known_count
            },
            'trailer_heat': trailer_heat_df,
            'premiere_prediction': premiere_prediction,
            'time_gate_analysis': time_gate_analysis
        }
        
        return report
    
    def get_model_evaluation(self, drama_info, dates, true_ratings, social_df, n_known=10):
        initial_ratings = true_ratings[:n_known]
        predictions = self.predict_all_episodes(drama_info, dates, initial_ratings, social_df)
        
        eval_results = {}
        for name, preds in predictions.items():
            y_true = true_ratings[n_known:]
            y_pred = preds[n_known:]
            eval_results[name] = {
                'rmse': round(calculate_rmse(y_true, y_pred), 4),
                'mape': round(calculate_mape(y_true, y_pred), 2)
            }
        
        return eval_results

if __name__ == '__main__':
    engine = RatingPredictionEngine()
    
    engine.train_models(num_dramas=30)
    
    test_drama = generate_drama_basic_info('TEST003')
    dates, true_ratings = generate_episodic_ratings(test_drama)
    social_df = generate_social_media_data(test_drama, dates, true_ratings)
    
    print(f"\n{'='*60}")
    print(f"Generating prediction report for: {test_drama['drama_name']}")
    print(f"Genre: {test_drama['genre']} | Platform: {test_drama['platform']}")
    print(f"Actor Level: {test_drama['actor_level']} | Episodes: {test_drama['num_episodes']}")
    print(f"{'='*60}")
    
    n_known = 10
    initial_ratings = true_ratings[:n_known]
    
    report = engine.generate_full_prediction_report(
        test_drama, dates, initial_ratings, social_df
    )
    
    print(f"\nPrediction Summary:")
    for k, v in report['prediction_summary'].items():
        print(f"  {k}: {v}")
    
    print(f"\nTop Peak Episodes:")
    for peak in report['top_peaks']:
        print(f"  Episode {peak['episode']}: {peak['predicted_rating']:.3f}% "
              f"(+{peak['increase_percent']:.1f}%, confidence: {peak['confidence']:.2f})")
    
    print(f"\nRenewal Recommendation:")
    print(f"  Score: {report['renewal_recommendation']['total_score']}/100")
    print(f"  Recommendation: {report['renewal_recommendation']['recommendation']}")
    print(f"  Confidence: {report['renewal_recommendation']['confidence']}")
    print(f"  Key Reasons:")
    for reason in report['renewal_recommendation']['key_reasons']:
        print(f"    - {reason}")
    
    eval_results = engine.get_model_evaluation(test_drama, dates, true_ratings, social_df, n_known)
    print(f"\nModel Evaluation (on unknown episodes):")
    for name, metrics in eval_results.items():
        print(f"  {name}: RMSE={metrics['rmse']:.4f}, MAPE={metrics['mape']:.2f}%")
