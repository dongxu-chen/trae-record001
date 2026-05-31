import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from datetime import datetime


class SignalDirection(Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"
    NEUTRAL = "neutral"


@dataclass
class PatternCombo:
    combo_id: str
    patterns: List[Dict]
    direction: SignalDirection
    strength: float
    start_index: int
    end_index: int
    start_date: pd.Timestamp
    end_date: pd.Timestamp
    price: float
    individual_confidences: List[float]
    boost_factor: float


COMBO_RULES = {
    'hammer_bullish_engulfing': {
        'patterns': ['Hammer', 'Bullish Engulfing'],
        'direction': SignalDirection.BULLISH,
        'boost': 1.8,
        'max_gap': 3,
        'description': '锤子线+看涨吞没：强底部反转信号'
    },
    'hanging_man_bearish_engulfing': {
        'patterns': ['Hanging Man', 'Bearish Engulfing'],
        'direction': SignalDirection.BEARISH,
        'boost': 1.8,
        'max_gap': 3,
        'description': '上吊线+看跌吞没：强顶部反转信号'
    },
    'double_bottom_hammer': {
        'patterns': ['Double Bottom', 'Hammer'],
        'direction': SignalDirection.BULLISH,
        'boost': 1.6,
        'max_gap': 5,
        'description': '双底+锤子线：底部确认信号'
    },
    'double_top_hanging_man': {
        'patterns': ['Double Top', 'Hanging Man'],
        'direction': SignalDirection.BEARISH,
        'boost': 1.6,
        'max_gap': 5,
        'description': '双顶+上吊线：顶部确认信号'
    },
    'inverse_hs_hammer': {
        'patterns': ['Inverse H&S', 'Hammer'],
        'direction': SignalDirection.BULLISH,
        'boost': 1.7,
        'max_gap': 5,
        'description': '头肩底+锤子线：强底部反转'
    },
    'hs_hanging_man': {
        'patterns': ['Head & Shoulders', 'Hanging Man'],
        'direction': SignalDirection.BEARISH,
        'boost': 1.7,
        'max_gap': 5,
        'description': '头肩顶+上吊线：强顶部反转'
    },
    'bullish_engulfing_double_bottom': {
        'patterns': ['Bullish Engulfing', 'Double Bottom'],
        'direction': SignalDirection.BULLISH,
        'boost': 1.5,
        'max_gap': 4,
        'description': '看涨吞没+双底：双重底部信号'
    },
    'bearish_engulfing_double_top': {
        'patterns': ['Bearish Engulfing', 'Double Top'],
        'direction': SignalDirection.BEARISH,
        'boost': 1.5,
        'max_gap': 4,
        'description': '看跌吞没+双顶：双重顶部信号'
    },
    'triple_bullish': {
        'patterns': ['Hammer', 'Bullish Engulfing', 'Double Bottom'],
        'direction': SignalDirection.BULLISH,
        'boost': 2.2,
        'max_gap': 5,
        'description': '锤子线+看涨吞没+双底：极强底部信号'
    },
    'triple_bearish': {
        'patterns': ['Hanging Man', 'Bearish Engulfing', 'Double Top'],
        'direction': SignalDirection.BEARISH,
        'boost': 2.2,
        'max_gap': 5,
        'description': '上吊线+看跌吞没+双顶：极强顶部信号'
    },
    'hammer_hammer': {
        'patterns': ['Hammer', 'Hammer'],
        'direction': SignalDirection.BULLISH,
        'boost': 1.4,
        'max_gap': 2,
        'description': '双锤子线：底部强化信号'
    },
    'engulfing_engulfing': {
        'patterns': ['Bullish Engulfing', 'Bullish Engulfing'],
        'direction': SignalDirection.BULLISH,
        'boost': 1.5,
        'max_gap': 3,
        'description': '连续看涨吞没：强势看涨'
    },
    'bearish_engulfing_engulfing': {
        'patterns': ['Bearish Engulfing', 'Bearish Engulfing'],
        'direction': SignalDirection.BEARISH,
        'boost': 1.5,
        'max_gap': 3,
        'description': '连续看跌吞没：强势看跌'
    }
}


class PatternComboDetector:
    def __init__(self, patterns: List[Dict], df: pd.DataFrame):
        self.patterns = sorted(patterns, key=lambda x: x['index'])
        self.df = df
    
    def detect_combos(self) -> List[PatternCombo]:
        combos = []
        
        for rule_name, rule in COMBO_RULES.items():
            matched_combos = self._match_rule(rule_name, rule)
            combos.extend(matched_combos)
        
        combos.sort(key=lambda x: x.strength, reverse=True)
        
        combos = self._deduplicate_combos(combos)
        
        return combos
    
    def _match_rule(self, rule_name: str, rule: Dict) -> List[PatternCombo]:
        combos = []
        required_patterns = rule['patterns']
        max_gap = rule['max_gap']
        
        if len(self.patterns) < len(required_patterns):
            return combos
        
        for i in range(len(self.patterns)):
            matched = self._try_match_from(i, required_patterns, max_gap)
            if matched is not None:
                combo_patterns = matched
                boost = rule['boost']
                
                avg_confidence = np.mean([p['confidence'] for p in combo_patterns])
                
                n_patterns = len(combo_patterns)
                additional_boost = 1.0 + (n_patterns - 2) * 0.15
                
                final_boost = boost * additional_boost
                
                strength = min(1.0, avg_confidence * final_boost)
                
                combo = PatternCombo(
                    combo_id=rule_name,
                    patterns=combo_patterns,
                    direction=rule['direction'],
                    strength=strength,
                    start_index=combo_patterns[0]['index'],
                    end_index=combo_patterns[-1]['index'],
                    start_date=combo_patterns[0]['date'],
                    end_date=combo_patterns[-1]['date'],
                    price=combo_patterns[-1]['price'],
                    individual_confidences=[p['confidence'] for p in combo_patterns],
                    boost_factor=final_boost
                )
                combos.append(combo)
        
        return combos
    
    def _try_match_from(self, start_idx: int, required_patterns: List[str], max_gap: int) -> Optional[List[Dict]]:
        matched = []
        pattern_idx = start_idx
        
        for req_pattern in required_patterns:
            found = False
            
            for j in range(pattern_idx, len(self.patterns)):
                candidate = self.patterns[j]
                
                if matched and (candidate['index'] - matched[-1]['index']) > max_gap:
                    break
                
                if candidate['pattern'] == req_pattern:
                    matched.append(candidate)
                    pattern_idx = j + 1
                    found = True
                    break
            
            if not found:
                return None
        
        if len(matched) == len(required_patterns):
            return matched
        return None
    
    def _deduplicate_combos(self, combos: List[PatternCombo]) -> List[PatternCombo]:
        used_indices = set()
        result = []
        
        for combo in combos:
            combo_indices = set(range(combo.start_index, combo.end_index + 1))
            
            if not combo_indices.intersection(used_indices):
                result.append(combo)
                used_indices.update(combo_indices)
        
        return result
    
    def get_enhanced_patterns(self) -> List[Dict]:
        combos = self.detect_combos()
        enhanced = []
        
        combo_indices = set()
        for combo in combos:
            for p in combo.patterns:
                combo_indices.add(p['index'])
        
        for p in self.patterns:
            if p['index'] not in combo_indices:
                enhanced.append(p)
        
        for combo in combos:
            direction_text = '上涨' if combo.direction == SignalDirection.BULLISH else '下跌'
            rule_info = COMBO_RULES.get(combo.combo_id, {})
            description = rule_info.get('description', combo.combo_id)
            
            pattern_names = ' + '.join([p['pattern'] for p in combo.patterns])
            
            enhanced.append({
                'pattern': f'⚡ {pattern_names}',
                'type': combo.direction.value,
                'index': combo.end_index,
                'date': combo.end_date,
                'price': combo.price,
                'prediction': 'up' if combo.direction == SignalDirection.BULLISH else 'down',
                'confidence': combo.strength,
                'is_combo': True,
                'details': {
                    'combo_id': combo.combo_id,
                    'description': description,
                    'boost_factor': combo.boost_factor,
                    'individual_confidences': combo.individual_confidences,
                    'pattern_count': len(combo.patterns),
                    'start_date': combo.start_date,
                    'end_date': combo.end_date
                }
            })
        
        enhanced.sort(key=lambda x: x['index'])
        return enhanced


@dataclass
class Alert:
    alert_id: str
    pattern_name: str
    direction: SignalDirection
    strength: float
    date: pd.Timestamp
    price: float
    is_combo: bool
    description: str
    prediction: str
    confidence: float


class PatternAlertSystem:
    def __init__(self, 
                 min_confidence: float = 0.5,
                 combo_only: bool = False,
                 alert_cooldown: int = 3):
        self.min_confidence = min_confidence
        self.combo_only = combo_only
        self.alert_cooldown = alert_cooldown
        self.alert_history: List[Alert] = []
        self._last_alert_idx = -999
    
    def generate_alerts(self, patterns: List[Dict], df: pd.DataFrame) -> List[Alert]:
        alerts = []
        
        for p in patterns:
            if p['confidence'] < self.min_confidence:
                continue
            
            if self.combo_only and not p.get('is_combo', False):
                continue
            
            if p['index'] - self._last_alert_idx < self.alert_cooldown:
                continue
            
            direction = SignalDirection.BULLISH if p['prediction'] == 'up' else SignalDirection.BEARISH
            
            description = self._generate_description(p)
            
            alert = Alert(
                alert_id=f"alert_{p['pattern']}_{p['index']}",
                pattern_name=p['pattern'],
                direction=direction,
                strength=p['confidence'],
                date=p['date'],
                price=p['price'],
                is_combo=p.get('is_combo', False),
                description=description,
                prediction=p['prediction'],
                confidence=p['confidence']
            )
            
            alerts.append(alert)
            self.alert_history.append(alert)
            self._last_alert_idx = p['index']
        
        return alerts
    
    def _generate_description(self, pattern: Dict) -> str:
        direction = '看涨' if pattern['prediction'] == 'up' else '看跌'
        name = pattern['pattern']
        confidence = pattern['confidence']
        
        if pattern.get('is_combo', False):
            details = pattern.get('details', {})
            desc = details.get('description', '组合形态')
            boost = details.get('boost_factor', 1.0)
            return (
                f"🔥 组合形态预警: {desc}\n"
                f"方向: {direction} | 置信度: {confidence:.0%} | "
                f"信号增强: {boost:.1f}x"
            )
        else:
            return (
                f"📌 单一形态预警: {name}\n"
                f"方向: {direction} | 置信度: {confidence:.0%}"
            )
    
    def get_alert_summary(self, alerts: List[Alert]) -> Dict:
        if not alerts:
            return {
                'total_alerts': 0,
                'bullish_alerts': 0,
                'bearish_alerts': 0,
                'combo_alerts': 0,
                'single_alerts': 0,
                'avg_confidence': 0,
                'latest_alert': None
            }
        
        bullish = [a for a in alerts if a.direction == SignalDirection.BULLISH]
        bearish = [a for a in alerts if a.direction == SignalDirection.BEARISH]
        combo = [a for a in alerts if a.is_combo]
        single = [a for a in alerts if not a.is_combo]
        
        return {
            'total_alerts': len(alerts),
            'bullish_alerts': len(bullish),
            'bearish_alerts': len(bearish),
            'combo_alerts': len(combo),
            'single_alerts': len(single),
            'avg_confidence': np.mean([a.confidence for a in alerts]),
            'latest_alert': alerts[-1] if alerts else None
        }


class PatternSuccessRateTracker:
    def __init__(self, df: pd.DataFrame, 
                 forward_period: int = 10,
                 min_samples: int = 3):
        self.df = df.copy().sort_index()
        self.forward_period = forward_period
        self.min_samples = min_samples
    
    def calculate_success_rates(self, patterns: List[Dict]) -> pd.DataFrame:
        if not patterns:
            return pd.DataFrame(columns=[
                'pattern', 'total', 'success', 'fail', 
                'success_rate', 'avg_return', 'avg_success_return',
                'avg_fail_return', 'best_return', 'worst_return'
            ])
        
        results = []
        
        grouped = {}
        for p in patterns:
            name = p['pattern']
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(p)
        
        for pattern_name, pattern_list in grouped.items():
            stats = self._calculate_pattern_stats(pattern_name, pattern_list)
            results.append(stats)
        
        df = pd.DataFrame(results)
        df = df.sort_values('success_rate', ascending=False)
        
        return df
    
    def _calculate_pattern_stats(self, pattern_name: str, patterns: List[Dict]) -> Dict:
        successes = []
        failures = []
        returns = []
        
        for p in patterns:
            idx = p['index']
            prediction = p['prediction']
            
            forward_return = self._calculate_forward_return(idx, prediction)
            
            if forward_return is not None:
                returns.append(forward_return)
                if forward_return > 0:
                    successes.append(forward_return)
                else:
                    failures.append(forward_return)
        
        total = len(returns)
        
        if total < self.min_samples:
            return {
                'pattern': pattern_name,
                'total': total,
                'success': len(successes),
                'fail': len(failures),
                'success_rate': np.nan if total == 0 else len(successes) / total,
                'avg_return': np.nan if total == 0 else np.mean(returns),
                'avg_success_return': np.nan if not successes else np.mean(successes),
                'avg_fail_return': np.nan if not failures else np.mean(failures),
                'best_return': np.nan if not returns else max(returns),
                'worst_return': np.nan if not returns else min(returns)
            }
        
        return {
            'pattern': pattern_name,
            'total': total,
            'success': len(successes),
            'fail': len(failures),
            'success_rate': len(successes) / total,
            'avg_return': np.mean(returns),
            'avg_success_return': np.mean(successes) if successes else 0,
            'avg_fail_return': np.mean(failures) if failures else 0,
            'best_return': max(returns),
            'worst_return': min(returns)
        }
    
    def _calculate_forward_return(self, idx: int, prediction: str) -> Optional[float]:
        if idx + self.forward_period >= len(self.df):
            return None
        
        entry_price = self.df['Close'].iloc[idx]
        exit_price = self.df['Close'].iloc[idx + self.forward_period]
        
        if entry_price == 0:
            return None
        
        price_return = (exit_price - entry_price) / entry_price
        
        if prediction == 'up':
            return price_return
        else:
            return -price_return
    
    def calculate_rolling_success_rate(self, 
                                        patterns: List[Dict],
                                        window: int = 20) -> pd.DataFrame:
        if not patterns:
            return pd.DataFrame()
        
        records = []
        
        for p in patterns:
            idx = p['index']
            prediction = p['prediction']
            forward_return = self._calculate_forward_return(idx, prediction)
            
            if forward_return is not None:
                records.append({
                    'date': p['date'],
                    'pattern': p['pattern'],
                    'prediction': prediction,
                    'return': forward_return,
                    'success': 1 if forward_return > 0 else 0,
                    'index': idx
                })
        
        if not records:
            return pd.DataFrame()
        
        df = pd.DataFrame(records)
        df = df.sort_values('index')
        
        df['rolling_success_rate'] = df['success'].rolling(
            window=min(window, len(df)), min_periods=1
        ).mean()
        
        df['rolling_avg_return'] = df['return'].rolling(
            window=min(window, len(df)), min_periods=1
        ).mean()
        
        return df
    
    def calculate_combo_success_rate(self, 
                                      patterns: List[Dict],
                                      combos: List[PatternCombo]) -> pd.DataFrame:
        if not combos:
            return pd.DataFrame(columns=[
                'combo', 'total', 'success', 'success_rate', 'avg_return'
            ])
        
        results = []
        
        grouped = {}
        for combo in combos:
            name = combo.combo_id
            if name not in grouped:
                grouped[name] = []
            grouped[name].append(combo)
        
        for combo_name, combo_list in grouped.items():
            successes = 0
            returns = []
            
            for combo in combo_list:
                idx = combo.end_index
                prediction = 'up' if combo.direction == SignalDirection.BULLISH else 'down'
                
                forward_return = self._calculate_forward_return(idx, prediction)
                
                if forward_return is not None:
                    returns.append(forward_return)
                    if forward_return > 0:
                        successes += 1
            
            total = len(returns)
            
            results.append({
                'combo': combo_name,
                'total': total,
                'success': successes,
                'success_rate': successes / total if total > 0 else np.nan,
                'avg_return': np.mean(returns) if returns else np.nan
            })
        
        df = pd.DataFrame(results)
        df = df.sort_values('success_rate', ascending=False)
        return df
