import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import warnings
warnings.filterwarnings('ignore')


@dataclass
class WOMParams:
    decay_rate: float = 0.15
    word_of_mouth_factor: float = 0.8
    social_media_amplification: float = 1.2
    critic_score_weight: float = 0.3
    audience_score_weight: float = 0.7
    max_legs_weeks: int = 8
    saturation_threshold: float = 0.8


@dataclass
class WOMScoring:
    douban_score: Optional[float] = None
    maoyan_score: Optional[float] = None
    taopiaopiao_score: Optional[float] = None
    imdb_score: Optional[float] = None
    rotten_tomatoes: Optional[float] = None
    metacritic: Optional[float] = None
    
    def weighted_score(self) -> float:
        scores = []
        weights = []
        
        if self.douban_score is not None:
            scores.append(self.douban_score / 10.0)
            weights.append(0.3)
        if self.maoyan_score is not None:
            scores.append(self.maoyan_score / 10.0)
            weights.append(0.25)
        if self.taopiaopiao_score is not None:
            scores.append(self.taopiaopiao_score / 10.0)
            weights.append(0.25)
        if self.imdb_score is not None:
            scores.append(self.imdb_score / 10.0)
            weights.append(0.1)
        if self.rotten_tomatoes is not None:
            scores.append(self.rotten_tomatoes / 100.0)
            weights.append(0.05)
        if self.metacritic is not None:
            scores.append(self.metacritic / 100.0)
            weights.append(0.05)
        
        if not scores:
            return 0.5
        
        total_weight = sum(weights)
        return np.average(scores, weights=[w/total_weight for w in weights])
    
    def composite_score(self) -> float:
        return self.weighted_score() * 10.0


@dataclass
class PointScreenData:
    screen_count: int = 0
    total_viewers: int = 0
    average_occupancy: float = 0.0
    point_screen_days: int = 0
    average_score: float = 0.0
    positive_review_ratio: float = 0.0
    social_media_mentions: int = 0
    want_to_watch_increase: int = 0
    viewer_comments: List[str] = field(default_factory=list)
    
    def correction_factor(self) -> float:
        factor = 1.0
        
        if self.average_score > 0:
            score_factor = (self.average_score / 7.5)
            factor *= score_factor
        
        if self.average_occupancy > 0:
            occupancy_factor = min(1.5, self.average_occupancy / 0.6)
            factor *= occupancy_factor
        
        if self.positive_review_ratio > 0:
            pos_factor = min(1.3, self.positive_review_ratio / 0.7)
            factor *= pos_factor
        
        if self.screen_count > 0:
            screen_factor = min(1.2, 1 + (self.screen_count / 1000) * 0.1)
            factor *= screen_factor
        
        if self.social_media_mentions > 0:
            social_factor = min(1.4, 1 + np.log1p(self.social_media_mentions / 10000))
            factor *= social_factor
        
        return max(0.5, min(2.0, factor))


class WordOfMouthSimulator:
    def __init__(self, params: Optional[WOMParams] = None):
        self.params = params or WOMParams()

    def _bass_diffusion(self, p: float, q: float, M: float, t: np.ndarray) -> np.ndarray:
        exp_term = np.exp(-(p + q) * t)
        denominator = (1 + (q / p) * exp_term) ** 2
        numerator = M * (p + q) ** 2 * exp_term
        return numerator / (p * denominator)

    def simulate_weekly_box_office(
        self,
        first_week: float,
        total_box_office: float,
        scoring: WOMScoring,
        competition_intensity: float = 0.5,
        season_factor: float = 1.0,
        point_screen_data: Optional[PointScreenData] = None
    ) -> Dict:
        w_score = scoring.weighted_score()
        legs_multiplier = 1.0 + (w_score - 0.5) * self.params.word_of_mouth_factor * 2
        
        base_total = total_box_office
        if point_screen_data is not None:
            correction = point_screen_data.correction_factor()
            base_total *= correction
        
        base_ratio = first_week / base_total
        
        p = 0.03 + (w_score - 0.5) * 0.02
        q = 0.3 + (w_score - 0.5) * 0.2
        
        competition_decay = 1 + competition_intensity * self.params.decay_rate
        effective_decay = self.params.decay_rate * competition_decay / season_factor
        
        n_weeks = min(self.params.max_legs_weeks, int(np.ceil(np.log(0.01) / np.log(1 - effective_decay))))
        n_weeks = max(n_weeks, 3)
        
        t = np.arange(n_weeks)
        weekly = self._bass_diffusion(p, q, base_total, t)
        
        first_week_correction = first_week / weekly[0] if weekly[0] > 0 else 1
        weekly = weekly * first_week_correction
        
        wom_effect = np.zeros(n_weeks)
        peak_week = min(int(n_weeks * (0.3 + w_score * 0.3)), n_weeks - 1)
        for i in range(n_weeks):
            if i <= peak_week:
                wom_effect[i] = 1 + (w_score - 0.5) * (i / max(1, peak_week)) * self.params.word_of_mouth_factor
            else:
                decay = (1 - effective_decay) ** (i - peak_week)
                wom_effect[i] = 1 + (w_score - 0.5) * decay * self.params.word_of_mouth_factor
        
        weekly = weekly * wom_effect * season_factor
        weekly = np.maximum(weekly, first_week * 0.01)
        
        cume = np.cumsum(weekly)
        cume_ratio = cume / base_total
        
        if cume_ratio[-1] > self.params.saturation_threshold:
            scale_factor = base_total * 0.95 / cume[-1] if cume[-1] > 0 else 1
            weekly = weekly * scale_factor
            cume = np.cumsum(weekly)
        
        weekly_forecast = []
        for i in range(n_weeks):
            weekly_forecast.append({
                'week': i + 1,
                'week_box_office': float(weekly[i]),
                'cumulative_box_office': float(cume[i]),
                'wom_multiplier': float(wom_effect[i]),
                'share_of_total': float(weekly[i] / cume[-1] if cume[-1] > 0 else 0)
            })
        
        adjusted_total = float(cume[-1])
        adjusted_first_week = float(weekly[0])
        
        legs_ratio = adjusted_total / adjusted_first_week if adjusted_first_week > 0 else 0
        
        return {
            'weekly_forecast': weekly_forecast,
            'adjusted_opening_week': adjusted_first_week,
            'adjusted_first_week': adjusted_first_week,
            'adjusted_total': adjusted_total,
            'legs_ratio': legs_ratio,
            'word_of_mouth_score': w_score * 10.0,
            'word_of_mouth_impact': (adjusted_total - total_box_office) / max(total_box_office, 1),
            'word_of_mouth_impact_pct': (adjusted_total - total_box_office) / max(total_box_office, 1) * 100,
            'point_screen_correction': point_screen_data.correction_factor() if point_screen_data else 1.0,
            'peak_week': peak_week + 1,
            'forecast_weeks': n_weeks
        }
    
    def simulate_weekly_forecast(
        self,
        opening_week_box_office: float,
        total_box_office: float,
        scoring: WOMScoring,
        competition_intensity: float = 0.5,
        season_factor: float = 1.0,
        point_screen_correction: float = 1.0
    ) -> Dict:
        ps_data = None
        if point_screen_correction != 1.0:
            ps_data = PointScreenData()
            ps_data.average_score = 7.5 * point_screen_correction
            ps_data.average_occupancy = 0.6 * point_screen_correction
            ps_data.positive_review_ratio = 0.7 * point_screen_correction
        
        return self.simulate_weekly_box_office(
            first_week=opening_week_box_office,
            total_box_office=total_box_office,
            scoring=scoring,
            competition_intensity=competition_intensity,
            season_factor=season_factor,
            point_screen_data=ps_data
        )
    
    def sensitivity_analysis(
        self,
        opening_week_box_office: float,
        total_box_office: float,
        base_scoring: WOMScoring
    ) -> List[Dict]:
        base_result = self.simulate_weekly_forecast(
            opening_week_box_office, total_box_office, base_scoring
        )
        base_total = base_result['adjusted_total']
        
        scenarios = []
        deviations = [-1.5, -1.0, -0.5, 0, 0.5, 1.0, 1.5]
        scenario_names = ['严重低于预期', '明显低于预期', '略低于预期', '基准预期', '略高于预期', '明显高于预期', '严重高于预期']
        
        base_score = base_scoring.composite_score() / 10.0
        
        for dev, name in zip(deviations, scenario_names):
            new_score_01 = max(0.1, min(1.0, base_score + dev / 10.0))
            new_score_10 = new_score_01 * 10.0
            
            new_scoring = WOMScoring(
                douban_score=new_score_10 if base_scoring.douban_score else None,
                maoyan_score=new_score_10 if base_scoring.maoyan_score else None,
                taopiaopiao_score=new_score_10 if base_scoring.taopiaopiao_score else None
            )
            
            result = self.simulate_weekly_forecast(
                opening_week_box_office, total_box_office, new_scoring
            )
            
            scenarios.append({
                'scenario': name,
                'score_deviation': dev,
                'new_score': new_score_10,
                'adjusted_total': result['adjusted_total'],
                'total_box_change_pct': (result['adjusted_total'] - base_total) / base_total * 100,
                'legs_ratio': result['legs_ratio']
            })
        
        return scenarios

    def analyze_wom_impact(
        self,
        scoring: WOMScoring,
        base_first_week: float,
        base_total: float
    ) -> Dict:
        w_score = scoring.weighted_score()
        
        scenarios = []
        score_offsets = [-0.2, -0.1, 0, 0.1, 0.2]
        for offset in score_offsets:
            scenario_score = max(0.1, min(1.0, w_score + offset))
            simulated_score = WOMScoring(
                douban_score=scenario_score * 10 if scoring.douban_score else None,
                maoyan_score=scenario_score * 10 if scoring.maoyan_score else None
            )
            
            result = self.simulate_weekly_box_office(
                first_week=base_first_week,
                total_box_office=base_total,
                scoring=simulated_score
            )
            
            scenarios.append({
                'score_offset': offset,
                'effective_score': scenario_score * 10,
                'total_box_office': result['adjusted_total'],
                'first_week': result['adjusted_first_week'],
                'legs_ratio': result['legs_ratio'],
                'impact_percent': (result['adjusted_total'] - base_total) / base_total * 100
            })
        
        sensitivity = {
            'score_elasticity': scenarios[3]['impact_percent'] - scenarios[1]['impact_percent'],
            'break_even_score': 0.0,
            'scenarios': scenarios
        }
        
        for i in range(len(scenarios) - 1):
            if scenarios[i]['impact_percent'] < 0 <= scenarios[i + 1]['impact_percent']:
                ratio = (0 - scenarios[i]['impact_percent']) / (scenarios[i + 1]['impact_percent'] - scenarios[i]['impact_percent'] + 1e-6)
                sensitivity['break_even_score'] = scenarios[i]['effective_score'] + ratio * (scenarios[i + 1]['effective_score'] - scenarios[i]['effective_score'])
                break
        
        return {
            'current_score': w_score * 10,
            'sensitivity': sensitivity,
            'recommendation': self._generate_wom_recommendation(w_score, sensitivity)
        }

    def _generate_wom_recommendation(self, w_score: float, sensitivity: Dict) -> str:
        score_10 = w_score * 10
        
        if score_10 >= 9:
            return "口碑极佳，建议加大宣发投入，充分利用口碑发酵延长上映周期"
        elif score_10 >= 8:
            return "口碑优秀，建议针对性安排口碑场和粉丝场，维持排片热度"
        elif score_10 >= 7:
            return "口碑良好，建议稳定宣发节奏，挖掘细分观众群体"
        elif score_10 >= 6:
            return "口碑中等，建议调整宣发策略，突出影片亮点"
        elif score_10 >= 5:
            return "口碑一般，建议收缩宣发投入，重点投放高转化率渠道"
        else:
            return "口碑较差，建议快速调整排片策略，控制风险"


class PricingOptimizer:
    def __init__(self):
        self.base_price_segments = {
            'morning': {'base_price': 35, 'demand_elasticity': 1.5},
            'afternoon': {'base_price': 45, 'demand_elasticity': 1.2},
            'evening': {'base_price': 65, 'demand_elasticity': 0.8},
            'midnight': {'base_price': 55, 'demand_elasticity': 1.8},
            'weekend_premium': {'multiplier': 1.3},
            'holiday_premium': {'multiplier': 1.5}
        }

    def calculate_demand(
        self,
        price: float,
        base_demand: float,
        elasticity: float,
        competition_factor: float = 1.0
    ) -> float:
        price_ratio = price / self.base_price_segments['evening']['base_price']
        demand = base_demand * (price_ratio ** (-elasticity))
        demand *= competition_factor
        return demand

    def calculate_revenue(
        self,
        price: float,
        base_demand: float,
        elasticity: float,
        capacity: float,
        competition_factor: float = 1.0
    ) -> Tuple[float, float, float]:
        demand = self.calculate_demand(price, base_demand, elasticity, competition_factor)
        effective_demand = min(demand, capacity)
        revenue = effective_demand * price
        return revenue, effective_demand, demand

    def optimize_segment_price(
        self,
        segment: str,
        base_demand: float,
        capacity: float,
        predicted_box_office: float,
        competition_factor: float = 1.0,
        is_weekend: bool = False,
        is_holiday: bool = False
    ) -> Dict:
        seg_config = self.base_price_segments.get(segment, self.base_price_segments['evening'])
        base_price = seg_config['base_price']
        elasticity = seg_config['demand_elasticity']
        
        total_gross = predicted_box_office
        demand_scale = min(3.0, np.log1p(total_gross / 10000))
        
        price_range = np.linspace(base_price * 0.6, base_price * 1.5, 100)
        
        best_price = base_price
        best_revenue = 0
        best_demand = 0
        
        revenue_list = []
        for price in price_range:
            scaled_demand = base_demand * demand_scale
            revenue, demand, unmet_demand = self.calculate_revenue(
                price, scaled_demand, elasticity, capacity, competition_factor
            )
            revenue_list.append((price, revenue, demand, unmet_demand))
            
            if revenue > best_revenue:
                best_revenue = revenue
                best_price = price
                best_demand = demand
        
        multiplier = 1.0
        if is_weekend:
            multiplier *= self.base_price_segments['weekend_premium']['multiplier']
        if is_holiday:
            multiplier *= self.base_price_segments['holiday_premium']['multiplier']
        
        final_price = best_price * multiplier
        final_revenue = best_revenue * multiplier
        final_demand = best_demand * multiplier
        
        occupancy_rate = final_demand / max(capacity, 1)
        
        price_point = {
            'optimal_price': round(final_price, 0),
            'expected_revenue': final_revenue,
            'expected_occupancy': occupancy_rate,
            'expected_demand': final_demand,
            'price_range': [float(price_range[0] * multiplier), float(price_range[-1] * multiplier)],
            'demand_elasticity': elasticity,
            'revenue_curve': [(round(p * multiplier, 0), round(r * multiplier, 2)) 
                            for p, r, _, _ in revenue_list[::10]]
        }
        
        return price_point

    def generate_pricing_strategy(
        self,
        predicted_first_week: float,
        predicted_total: float,
        wom_score: float = 0.7,
        competition_count: int = 3,
        is_holiday_release: bool = False,
        total_screens: int = 100000,
        avg_seats_per_screen: int = 150
    ) -> Dict:
        competition_factor = max(0.5, 1 - competition_count * 0.08)
        
        base_demand_scaling = predicted_first_week / 5000
        
        segments = ['morning', 'afternoon', 'evening', 'midnight']
        segment_capacity_ratio = {'morning': 0.15, 'afternoon': 0.25, 'evening': 0.5, 'midnight': 0.1}
        total_capacity = total_screens * avg_seats_per_screen * 7 * 5
        
        segment_results = {}
        for seg in segments:
            seg_capacity = total_capacity * segment_capacity_ratio[seg]
            
            weekday_price = self.optimize_segment_price(
                segment=seg,
                base_demand=base_demand_scaling,
                capacity=seg_capacity,
                predicted_box_office=predicted_total,
                competition_factor=competition_factor,
                is_weekend=False,
                is_holiday=is_holiday_release
            )
            
            weekend_price = self.optimize_segment_price(
                segment=seg,
                base_demand=base_demand_scaling * 1.5,
                capacity=seg_capacity,
                predicted_box_office=predicted_total,
                competition_factor=competition_factor,
                is_weekend=True,
                is_holiday=is_holiday_release
            )
            
            segment_results[seg] = {
                'weekday': weekday_price,
                'weekend': weekend_price
            }
        
        price_points = []
        for seg, res in segment_results.items():
            price_points.append(res['weekday']['optimal_price'])
            price_points.append(res['weekend']['optimal_price'])
        
        wom_adjustment = 1 + (wom_score - 0.7) * 0.3
        
        for seg in segment_results:
            for day_type in ['weekday', 'weekend']:
                segment_results[seg][day_type]['optimal_price'] = round(
                    segment_results[seg][day_type]['optimal_price'] * wom_adjustment, 0
                )
        
        recommendation = self._generate_pricing_recommendation(
            predicted_first_week, predicted_total, wom_score, competition_count
        )
        
        overall = {
            'average_ticket_price': float(np.mean(price_points) * wom_adjustment),
            'min_suggested_price': float(np.min(price_points) * wom_adjustment),
            'max_suggested_price': float(np.max(price_points) * wom_adjustment),
            'price_sensitivity_index': float(1 - np.std(price_points) / np.mean(price_points)),
            'segment_pricing': segment_results
        }
        
        return {
            'overall': overall,
            'competitive_position': {
                'competition_count': competition_count,
                'price_elasticity_adjustment': competition_factor,
                'wom_adjustment': wom_adjustment
            },
            'recommendation': recommendation
        }

    def _generate_pricing_recommendation(
        self,
        first_week: float,
        total: float,
        wom_score: float,
        competition: int
    ) -> str:
        score = wom_score * 10
        legs_ratio = total / max(first_week, 1)
        
        if score >= 8.5 and legs_ratio >= 3.5:
            return "长线口碑爆款，建议采用高位定价配合渐进降价策略，最大化生命周期总收益"
        elif score >= 8 and legs_ratio >= 2.8:
            return "口碑佳作，建议周末及黄金场采用溢价策略，平日保持弹性定价"
        elif score >= 7 and competition <= 5:
            return "中等偏上口碑，建议采用差异化定价，黄金场保持高位，非黄金场灵活促销"
        elif competition <= 3:
            return "竞争环境宽松，建议首周保持偏高定价，根据口碑走势动态调整"
        elif competition >= 8:
            return "竞争激烈，建议采用攻击性定价策略，用性价比抢占市场份额"
        else:
            return "建议采用动态定价策略，根据实时上座率和口碑灵活调整"
    
    def optimize_pricing(
        self,
        predicted_opening: float,
        predicted_total: float,
        wom_score: float = 7.0,
        competition_density: int = 3,
        genre_overlap_ratio: float = 0.3,
        is_holiday_release: bool = False
    ) -> Dict:
        wom_score_01 = wom_score / 10.0
        
        effective_competition = int(competition_density * (1 + genre_overlap_ratio))
        
        result = self.generate_pricing_strategy(
            predicted_first_week=predicted_opening,
            predicted_total=predicted_total,
            wom_score=wom_score_01,
            competition_count=effective_competition,
            is_holiday_release=is_holiday_release
        )
        
        return {
            'average_ticket_price': result['overall']['average_ticket_price'],
            'min_suggested_price': result['overall']['min_suggested_price'],
            'max_suggested_price': result['overall']['max_suggested_price'],
            'price_sensitivity_index': result['overall']['price_sensitivity_index'],
            'segment_pricing': result['overall']['segment_pricing'],
            'wom_adjustment': result['competitive_position']['wom_adjustment'],
            'recommendation': result['recommendation']
        }
