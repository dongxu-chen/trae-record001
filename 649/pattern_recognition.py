import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional


class PatternRecognizer:
    def __init__(self, df: pd.DataFrame, vol_lookback: int = 20):
        self.df = df.copy()
        self.vol_lookback = vol_lookback
        self._validate_data()
        self._calculate_volatility_factors()
    
    def _validate_data(self):
        required_cols = ['Open', 'High', 'Low', 'Close']
        for col in required_cols:
            if col not in self.df.columns:
                raise ValueError(f"DataFrame must contain '{col}' column")
        self.df = self.df.sort_index()
    
    def _calculate_volatility_factors(self):
        high = self.df['High'].values
        low = self.df['Low'].values
        close = self.df['Close'].values
        
        n = len(self.df)
        tr = np.zeros(n)
        
        for i in range(n):
            if i == 0:
                tr[i] = high[i] - low[i]
            else:
                tr[i] = max(
                    high[i] - low[i],
                    abs(high[i] - close[i-1]),
                    abs(low[i] - close[i-1])
                )
        
        atr = np.zeros(n)
        for i in range(n):
            start = max(0, i - self.vol_lookback + 1)
            atr[i] = np.mean(tr[start:i+1])
        
        self.df['TR'] = tr
        self.df['ATR'] = atr
        
        self.df['vol_factor'] = self.df['ATR'] / self.df['ATR'].median()
        self.df['vol_factor'] = self.df['vol_factor'].clip(0.3, 3.0)
    
    def _get_dynamic_threshold(self, base_threshold: float, idx: int) -> float:
        vol_factor = self.df['vol_factor'].iloc[idx]
        return base_threshold * vol_factor
    
    def _calculate_body_size(self, idx: int) -> float:
        return abs(self.df['Close'].iloc[idx] - self.df['Open'].iloc[idx])
    
    def _calculate_upper_shadow(self, idx: int) -> float:
        return self.df['High'].iloc[idx] - max(self.df['Open'].iloc[idx], self.df['Close'].iloc[idx])
    
    def _calculate_lower_shadow(self, idx: int) -> float:
        return min(self.df['Open'].iloc[idx], self.df['Close'].iloc[idx]) - self.df['Low'].iloc[idx]
    
    def _calculate_tr(self, idx: int) -> float:
        return self.df['High'].iloc[idx] - self.df['Low'].iloc[idx]
    
    def _is_bullish(self, idx: int) -> bool:
        return self.df['Close'].iloc[idx] > self.df['Open'].iloc[idx]
    
    def _is_bearish(self, idx: int) -> bool:
        return self.df['Close'].iloc[idx] < self.df['Open'].iloc[idx]
    
    def detect_hammer(self, 
                     body_ratio: float = 0.3,
                     lower_shadow_ratio: float = 2.0,
                     upper_shadow_ratio: float = 0.5) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        for i in range(1, n):
            body = self._calculate_body_size(i)
            lower_shadow = self._calculate_lower_shadow(i)
            upper_shadow = self._calculate_upper_shadow(i)
            tr = self._calculate_tr(i)
            
            if tr == 0:
                continue
            
            body_rel = body / tr
            lower_shadow_rel = lower_shadow / body if body > 0 else float('inf')
            upper_shadow_rel = upper_shadow / body if body > 0 else float('inf')
            
            dynamic_body_ratio = self._get_dynamic_threshold(body_ratio, i)
            dynamic_lower_shadow = self._get_dynamic_threshold(lower_shadow_ratio, i)
            dynamic_upper_shadow = self._get_dynamic_threshold(upper_shadow_ratio, i)
            
            if (body_rel <= dynamic_body_ratio and 
                lower_shadow_rel >= dynamic_lower_shadow and 
                upper_shadow_rel <= dynamic_upper_shadow):
                
                prev_trend = self._get_trend(i - 1, 5)
                
                if prev_trend < 0:
                    patterns.append({
                        'pattern': 'Hammer',
                        'type': 'bullish',
                        'index': i,
                        'date': self.df.index[i],
                        'price': self.df['Close'].iloc[i],
                        'prediction': 'up',
                        'confidence': min(0.9, (lower_shadow_rel / 3) * 0.7 + 0.3),
                        'details': {
                            'body_ratio': body_rel,
                            'lower_shadow_ratio': lower_shadow_rel,
                            'upper_shadow_ratio': upper_shadow_rel,
                            'prev_trend': prev_trend,
                            'vol_factor': self.df['vol_factor'].iloc[i],
                            'dynamic_body_ratio': dynamic_body_ratio,
                            'dynamic_lower_shadow': dynamic_lower_shadow
                        }
                    })
        
        return patterns
    
    def detect_hanging_man(self,
                          body_ratio: float = 0.3,
                          lower_shadow_ratio: float = 2.0,
                          upper_shadow_ratio: float = 0.5) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        for i in range(1, n):
            body = self._calculate_body_size(i)
            lower_shadow = self._calculate_lower_shadow(i)
            upper_shadow = self._calculate_upper_shadow(i)
            tr = self._calculate_tr(i)
            
            if tr == 0:
                continue
            
            body_rel = body / tr
            lower_shadow_rel = lower_shadow / body if body > 0 else float('inf')
            upper_shadow_rel = upper_shadow / body if body > 0 else float('inf')
            
            dynamic_body_ratio = self._get_dynamic_threshold(body_ratio, i)
            dynamic_lower_shadow = self._get_dynamic_threshold(lower_shadow_ratio, i)
            dynamic_upper_shadow = self._get_dynamic_threshold(upper_shadow_ratio, i)
            
            if (body_rel <= dynamic_body_ratio and 
                lower_shadow_rel >= dynamic_lower_shadow and 
                upper_shadow_rel <= dynamic_upper_shadow):
                
                prev_trend = self._get_trend(i - 1, 5)
                
                if prev_trend > 0:
                    patterns.append({
                        'pattern': 'Hanging Man',
                        'type': 'bearish',
                        'index': i,
                        'date': self.df.index[i],
                        'price': self.df['Close'].iloc[i],
                        'prediction': 'down',
                        'confidence': min(0.85, (lower_shadow_rel / 3) * 0.6 + 0.3),
                        'details': {
                            'body_ratio': body_rel,
                            'lower_shadow_ratio': lower_shadow_rel,
                            'upper_shadow_ratio': upper_shadow_rel,
                            'prev_trend': prev_trend,
                            'vol_factor': self.df['vol_factor'].iloc[i],
                            'dynamic_body_ratio': dynamic_body_ratio,
                            'dynamic_lower_shadow': dynamic_lower_shadow
                        }
                    })
        
        return patterns
    
    def detect_bullish_engulfing(self, min_body_ratio: float = 1.5) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        for i in range(1, n):
            if not self._is_bullish(i):
                continue
            
            if not self._is_bearish(i - 1):
                continue
            
            curr_body = self._calculate_body_size(i)
            prev_body = self._calculate_body_size(i - 1)
            
            if prev_body == 0:
                continue
            
            body_ratio = curr_body / prev_body
            
            dynamic_body_ratio = self._get_dynamic_threshold(min_body_ratio, i)
            
            if (body_ratio >= dynamic_body_ratio and
                self.df['Open'].iloc[i] < self.df['Close'].iloc[i - 1] and
                self.df['Close'].iloc[i] > self.df['Open'].iloc[i - 1]):
                
                prev_trend = self._get_trend(i - 1, 5)
                
                if prev_trend < 0:
                    patterns.append({
                        'pattern': 'Bullish Engulfing',
                        'type': 'bullish',
                        'index': i,
                        'date': self.df.index[i],
                        'price': self.df['Close'].iloc[i],
                        'prediction': 'up',
                        'confidence': min(0.95, body_ratio * 0.3 + 0.5),
                        'details': {
                            'body_ratio': body_ratio,
                            'prev_trend': prev_trend,
                            'vol_factor': self.df['vol_factor'].iloc[i],
                            'dynamic_body_ratio': dynamic_body_ratio
                        }
                    })
        
        return patterns
    
    def detect_bearish_engulfing(self, min_body_ratio: float = 1.5) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        for i in range(1, n):
            if not self._is_bearish(i):
                continue
            
            if not self._is_bullish(i - 1):
                continue
            
            curr_body = self._calculate_body_size(i)
            prev_body = self._calculate_body_size(i - 1)
            
            if prev_body == 0:
                continue
            
            body_ratio = curr_body / prev_body
            
            dynamic_body_ratio = self._get_dynamic_threshold(min_body_ratio, i)
            
            if (body_ratio >= dynamic_body_ratio and
                self.df['Open'].iloc[i] > self.df['Close'].iloc[i - 1] and
                self.df['Close'].iloc[i] < self.df['Open'].iloc[i - 1]):
                
                prev_trend = self._get_trend(i - 1, 5)
                
                if prev_trend > 0:
                    patterns.append({
                        'pattern': 'Bearish Engulfing',
                        'type': 'bearish',
                        'index': i,
                        'date': self.df.index[i],
                        'price': self.df['Close'].iloc[i],
                        'prediction': 'down',
                        'confidence': min(0.95, body_ratio * 0.3 + 0.5),
                        'details': {
                            'body_ratio': body_ratio,
                            'prev_trend': prev_trend,
                            'vol_factor': self.df['vol_factor'].iloc[i],
                            'dynamic_body_ratio': dynamic_body_ratio
                        }
                    })
        
        return patterns
    
    def detect_head_and_shoulders(self, 
                                  lookback: int = 30,
                                  shoulder_similarity: float = 0.85,
                                  neckline_threshold: float = 0.03) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        if n < lookback:
            return patterns
        
        for i in range(lookback, n):
            window = self.df.iloc[i - lookback:i].copy()
            highs = window['High'].values
            lows = window['Low'].values
            
            peaks = self._find_peaks(highs)
            
            if len(peaks) < 3:
                continue
            
            dynamic_similarity = self._get_dynamic_threshold(shoulder_similarity, i)
            dynamic_neckline_threshold = self._get_dynamic_threshold(neckline_threshold, i)
            
            for j in range(len(peaks) - 2):
                left_peak_idx = peaks[j]
                head_peak_idx = peaks[j + 1]
                right_peak_idx = peaks[j + 2]
                
                if not (highs[head_peak_idx] > highs[left_peak_idx] and 
                        highs[head_peak_idx] > highs[right_peak_idx]):
                    continue
                
                shoulder_diff = abs(highs[left_peak_idx] - highs[right_peak_idx]) / highs[left_peak_idx]
                if shoulder_diff > (1 - dynamic_similarity):
                    continue
                
                left_base_idx = left_peak_idx - 1 if left_peak_idx > 0 else 0
                right_base_idx = right_peak_idx + 1 if right_peak_idx < len(highs) - 1 else len(highs) - 1
                
                neckline_left = lows[left_base_idx]
                neckline_right = lows[right_base_idx]
                
                neckline_avg = (neckline_left + neckline_right) / 2
                
                pattern_end_idx = i - lookback + right_peak_idx
                if pattern_end_idx >= n:
                    continue
                
                current_price = self.df['Close'].iloc[pattern_end_idx]
                
                if current_price <= neckline_avg * (1 + dynamic_neckline_threshold):
                    patterns.append({
                        'pattern': 'Head & Shoulders',
                        'type': 'bearish',
                        'index': pattern_end_idx,
                        'date': self.df.index[pattern_end_idx],
                        'price': current_price,
                        'prediction': 'down',
                        'confidence': min(0.9, dynamic_similarity * 0.6 + 0.3),
                        'details': {
                            'shoulder_similarity': 1 - shoulder_diff,
                            'neckline_level': neckline_avg,
                            'head_height': highs[head_peak_idx] - neckline_avg,
                            'vol_factor': self.df['vol_factor'].iloc[i],
                            'dynamic_similarity': dynamic_similarity,
                            'dynamic_neckline_threshold': dynamic_neckline_threshold
                        }
                    })
                    break
        
        return patterns
    
    def detect_inverse_head_and_shoulders(self,
                                          lookback: int = 30,
                                          shoulder_similarity: float = 0.85,
                                          neckline_threshold: float = 0.03) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        if n < lookback:
            return patterns
        
        for i in range(lookback, n):
            window = self.df.iloc[i - lookback:i].copy()
            highs = window['High'].values
            lows = window['Low'].values
            
            troughs = self._find_troughs(lows)
            
            if len(troughs) < 3:
                continue
            
            dynamic_similarity = self._get_dynamic_threshold(shoulder_similarity, i)
            dynamic_neckline_threshold = self._get_dynamic_threshold(neckline_threshold, i)
            
            for j in range(len(troughs) - 2):
                left_trough_idx = troughs[j]
                head_trough_idx = troughs[j + 1]
                right_trough_idx = troughs[j + 2]
                
                if not (lows[head_trough_idx] < lows[left_trough_idx] and 
                        lows[head_trough_idx] < lows[right_trough_idx]):
                    continue
                
                shoulder_diff = abs(lows[left_trough_idx] - lows[right_trough_idx]) / lows[left_trough_idx]
                if shoulder_diff > (1 - dynamic_similarity):
                    continue
                
                left_peak_idx = left_trough_idx - 1 if left_trough_idx > 0 else 0
                right_peak_idx = right_trough_idx + 1 if right_trough_idx < len(lows) - 1 else len(lows) - 1
                
                neckline_left = highs[left_peak_idx]
                neckline_right = highs[right_peak_idx]
                
                neckline_avg = (neckline_left + neckline_right) / 2
                
                pattern_end_idx = i - lookback + right_trough_idx
                if pattern_end_idx >= n:
                    continue
                
                current_price = self.df['Close'].iloc[pattern_end_idx]
                
                if current_price >= neckline_avg * (1 - dynamic_neckline_threshold):
                    patterns.append({
                        'pattern': 'Inverse H&S',
                        'type': 'bullish',
                        'index': pattern_end_idx,
                        'date': self.df.index[pattern_end_idx],
                        'price': current_price,
                        'prediction': 'up',
                        'confidence': min(0.9, dynamic_similarity * 0.6 + 0.3),
                        'details': {
                            'shoulder_similarity': 1 - shoulder_diff,
                            'neckline_level': neckline_avg,
                            'head_depth': neckline_avg - lows[head_trough_idx],
                            'vol_factor': self.df['vol_factor'].iloc[i],
                            'dynamic_similarity': dynamic_similarity,
                            'dynamic_neckline_threshold': dynamic_neckline_threshold
                        }
                    })
                    break
        
        return patterns
    
    def detect_double_top(self,
                         lookback: int = 20,
                         peak_similarity: float = 0.95,
                         min_distance: int = 3) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        for i in range(lookback, n):
            window = self.df.iloc[i - lookback:i].copy()
            highs = window['High'].values
            
            peaks = self._find_peaks(highs)
            
            if len(peaks) < 2:
                continue
            
            dynamic_similarity = self._get_dynamic_threshold(peak_similarity, i)
            
            for j in range(len(peaks) - 1):
                peak1_idx = peaks[j]
                peak2_idx = peaks[j + 1]
                
                if peak2_idx - peak1_idx < min_distance:
                    continue
                
                peak1_high = highs[peak1_idx]
                peak2_high = highs[peak2_idx]
                
                similarity = min(peak1_high, peak2_high) / max(peak1_high, peak2_high)
                
                if similarity >= dynamic_similarity:
                    trough_idx = (peak1_idx + peak2_idx) // 2
                    neckline = window['Low'].iloc[trough_idx]
                    
                    pattern_end_idx = i - lookback + peak2_idx
                    if pattern_end_idx >= n:
                        continue
                    
                    current_price = self.df['Close'].iloc[pattern_end_idx]
                    
                    if current_price <= neckline * 1.02:
                        patterns.append({
                            'pattern': 'Double Top',
                            'type': 'bearish',
                            'index': pattern_end_idx,
                            'date': self.df.index[pattern_end_idx],
                            'price': current_price,
                            'prediction': 'down',
                            'confidence': dynamic_similarity * 0.8,
                            'details': {
                                'peak_similarity': similarity,
                                'neckline_level': neckline,
                                'pattern_height': peak1_high - neckline,
                                'vol_factor': self.df['vol_factor'].iloc[i],
                                'dynamic_similarity': dynamic_similarity
                            }
                        })
                        break
        
        return patterns
    
    def detect_double_bottom(self,
                            lookback: int = 20,
                            trough_similarity: float = 0.95,
                            min_distance: int = 3) -> List[Dict]:
        patterns = []
        n = len(self.df)
        
        for i in range(lookback, n):
            window = self.df.iloc[i - lookback:i].copy()
            lows = window['Low'].values
            
            troughs = self._find_troughs(lows)
            
            if len(troughs) < 2:
                continue
            
            dynamic_similarity = self._get_dynamic_threshold(trough_similarity, i)
            
            for j in range(len(troughs) - 1):
                trough1_idx = troughs[j]
                trough2_idx = troughs[j + 1]
                
                if trough2_idx - trough1_idx < min_distance:
                    continue
                
                trough1_low = lows[trough1_idx]
                trough2_low = lows[trough2_idx]
                
                similarity = min(trough1_low, trough2_low) / max(trough1_low, trough2_low)
                
                if similarity >= dynamic_similarity:
                    peak_idx = (trough1_idx + trough2_idx) // 2
                    neckline = window['High'].iloc[peak_idx]
                    
                    pattern_end_idx = i - lookback + trough2_idx
                    if pattern_end_idx >= n:
                        continue
                    
                    current_price = self.df['Close'].iloc[pattern_end_idx]
                    
                    if current_price >= neckline * 0.98:
                        patterns.append({
                            'pattern': 'Double Bottom',
                            'type': 'bullish',
                            'index': pattern_end_idx,
                            'date': self.df.index[pattern_end_idx],
                            'price': current_price,
                            'prediction': 'up',
                            'confidence': dynamic_similarity * 0.8,
                            'details': {
                                'trough_similarity': similarity,
                                'neckline_level': neckline,
                                'pattern_depth': neckline - trough1_low,
                                'vol_factor': self.df['vol_factor'].iloc[i],
                                'dynamic_similarity': dynamic_similarity
                            }
                        })
                        break
        
        return patterns
    
    def _get_trend(self, end_idx: int, period: int) -> float:
        start_idx = max(0, end_idx - period)
        if end_idx <= start_idx:
            return 0
        
        prices = self.df['Close'].iloc[start_idx:end_idx + 1].values
        if len(prices) < 2:
            return 0
        
        x = np.arange(len(prices))
        slope, _ = np.polyfit(x, prices, 1)
        return slope / prices[0] if prices[0] != 0 else 0
    
    def _find_peaks(self, data: np.ndarray, order: int = 2) -> List[int]:
        peaks = []
        n = len(data)
        
        for i in range(order, n - order):
            left_condition = np.all(data[i] > data[i - order:i])
            right_condition = np.all(data[i] > data[i + 1:i + order + 1])
            if left_condition and right_condition:
                peaks.append(i)
        
        return peaks
    
    def _find_troughs(self, data: np.ndarray, order: int = 2) -> List[int]:
        troughs = []
        n = len(data)
        
        for i in range(order, n - order):
            left_condition = np.all(data[i] < data[i - order:i])
            right_condition = np.all(data[i] < data[i + 1:i + order + 1])
            if left_condition and right_condition:
                troughs.append(i)
        
        return troughs
    
    def detect_all_patterns(self, params: Optional[Dict] = None) -> List[Dict]:
        if params is None:
            params = {}
        
        all_patterns = []
        
        hammer_params = params.get('hammer', {})
        all_patterns.extend(self.detect_hammer(**hammer_params))
        
        hanging_man_params = params.get('hanging_man', {})
        all_patterns.extend(self.detect_hanging_man(**hanging_man_params))
        
        bullish_engulfing_params = params.get('bullish_engulfing', {})
        all_patterns.extend(self.detect_bullish_engulfing(**bullish_engulfing_params))
        
        bearish_engulfing_params = params.get('bearish_engulfing', {})
        all_patterns.extend(self.detect_bearish_engulfing(**bearish_engulfing_params))
        
        hs_params = params.get('head_and_shoulders', {})
        all_patterns.extend(self.detect_head_and_shoulders(**hs_params))
        
        ihs_params = params.get('inverse_head_and_shoulders', {})
        all_patterns.extend(self.detect_inverse_head_and_shoulders(**ihs_params))
        
        dt_params = params.get('double_top', {})
        all_patterns.extend(self.detect_double_top(**dt_params))
        
        db_params = params.get('double_bottom', {})
        all_patterns.extend(self.detect_double_bottom(**db_params))
        
        all_patterns.sort(key=lambda x: x['index'])
        
        return all_patterns
    
    def get_volatility_stats(self) -> Dict:
        return {
            'median_atr': self.df['ATR'].median(),
            'mean_atr': self.df['ATR'].mean(),
            'max_atr': self.df['ATR'].max(),
            'min_atr': self.df['ATR'].min(),
            'vol_factor_range': (self.df['vol_factor'].min(), self.df['vol_factor'].max())
        }
