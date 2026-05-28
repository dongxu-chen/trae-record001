import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime
from config import Config
from prophet_detector import ProphetAnomalyDetector
from three_sigma_detector import ThreeSigmaDetector
from isolation_forest_detector import IsolationForestDetector
from holiday_manager import HolidayManager
from anomaly_pattern_library import AnomalyPatternLibrary

class AnomalyFusion:
    def __init__(self, weights: Dict[str, float] = None, enable_holiday_filter: bool = True,
                 enable_pattern_matching: bool = True):
        self.weights = weights or Config.ANOMALY_SCORE_WEIGHTS
        self.prophet_detector = ProphetAnomalyDetector()
        self.three_sigma_detector = ThreeSigmaDetector()
        self.isolation_forest_detector = IsolationForestDetector()
        self.holiday_manager = HolidayManager() if enable_holiday_filter else None
        self.pattern_library = AnomalyPatternLibrary() if enable_pattern_matching else None
        
    def detect_all_methods(self, df: pd.DataFrame, metrics: List[str]) -> Dict[str, Dict]:
        all_results = {}
        
        for metric in metrics:
            prophet_anomalies = self.prophet_detector.get_anomaly_points(df, metric)
            three_sigma_anomalies = self.three_sigma_detector.get_anomaly_points(df, metric)
            if_anomalies = self.isolation_forest_detector.get_anomaly_points(df, metric)
            
            all_results[metric] = {
                'prophet': prophet_anomalies,
                'three_sigma': three_sigma_anomalies,
                'isolation_forest': if_anomalies
            }
        
        return all_results
    
    def fuse_anomalies(self, df: pd.DataFrame, metrics: List[str]) -> List[Dict]:
        df_normalized = self._normalize_for_holidays(df, metrics)
        
        all_results = self.detect_all_methods(df_normalized, metrics)
        fused_anomalies = defaultdict(lambda: {
            'timestamp': None,
            'metrics': defaultdict(lambda: {
                'prophet': 0,
                'three_sigma': 0,
                'isolation_forest': 0,
                'total_score': 0,
                'anomaly_types': []
            }),
            'total_score': 0,
            'detected_by': [],
            'anomaly_count': 0
        })
        
        for metric in metrics:
            for method in ['prophet', 'three_sigma', 'isolation_forest']:
                for anomaly in all_results[metric][method]:
                    ts_key = anomaly['timestamp'].strftime('%Y-%m-%d %H:%M:%S')
                    
                    if fused_anomalies[ts_key]['timestamp'] is None:
                        fused_anomalies[ts_key]['timestamp'] = anomaly['timestamp']
                    
                    score = anomaly['anomaly_score'] * self.weights[method]
                    fused_anomalies[ts_key]['metrics'][metric][method] = anomaly['anomaly_score']
                    fused_anomalies[ts_key]['metrics'][metric]['total_score'] += score
                    
                    if method not in fused_anomalies[ts_key]['detected_by']:
                        fused_anomalies[ts_key]['detected_by'].append(method)
                    
                    if anomaly['anomaly_type'] not in fused_anomalies[ts_key]['metrics'][metric]['anomaly_types']:
                        fused_anomalies[ts_key]['metrics'][metric]['anomaly_types'].append(anomaly['anomaly_type'])
        
        for ts_key in fused_anomalies:
            total_score = 0
            metric_count = 0
            for metric in metrics:
                if fused_anomalies[ts_key]['metrics'][metric]['total_score'] > 0:
                    total_score += fused_anomalies[ts_key]['metrics'][metric]['total_score']
                    metric_count += 1
            
            if metric_count > 0:
                fused_anomalies[ts_key]['total_score'] = total_score / metric_count
                fused_anomalies[ts_key]['anomaly_count'] = metric_count
                fused_anomalies[ts_key]['is_joint'] = metric_count > 1
        
        result_list = []
        for ts_key, data in fused_anomalies.items():
            if data['total_score'] > 0:
                metrics_detail = {}
                for metric in metrics:
                    if data['metrics'][metric]['total_score'] > 0:
                        metrics_detail[metric] = {
                            'scores': {
                                'prophet': data['metrics'][metric]['prophet'],
                                'three_sigma': data['metrics'][metric]['three_sigma'],
                                'isolation_forest': data['metrics'][metric]['isolation_forest']
                            },
                            'total_score': data['metrics'][metric]['total_score'],
                            'anomaly_types': data['metrics'][metric]['anomaly_types']
                        }
                
                result_list.append({
                    'timestamp': data['timestamp'],
                    'total_score': data['total_score'],
                    'anomaly_count': data['anomaly_count'],
                    'is_joint_anomaly': data['is_joint'],
                    'detected_by': data['detected_by'],
                    'metrics': metrics_detail
                })
        
        result_list.sort(key=lambda x: x['total_score'], reverse=True)
        
        result_list = self._filter_holiday_anomalies(result_list, df)
        
        result_list, matched_patterns = self._match_anomaly_patterns(result_list, df)
        
        if matched_patterns:
            result_list = [{**a, 'matched_patterns': matched_patterns} for a in result_list]
        
        return result_list
    
    def _normalize_for_holidays(self, df: pd.DataFrame, metrics: List[str]) -> pd.DataFrame:
        if self.holiday_manager:
            return self.holiday_manager.remove_holiday_effect(df, metrics)
        return df
    
    def _filter_holiday_anomalies(self, anomalies: List[Dict], df: pd.DataFrame) -> List[Dict]:
        if self.holiday_manager:
            filtered, holiday_effect = self.holiday_manager.filter_holiday_anomalies(anomalies, df)
            return filtered
        return anomalies
    
    def _match_anomaly_patterns(self, anomalies: List[Dict], df: pd.DataFrame) -> Tuple[List[Dict], List[Dict]]:
        if self.pattern_library and anomalies:
            matched_patterns = self.pattern_library.match_patterns(anomalies, df)
            if matched_patterns:
                best_pattern = matched_patterns[0]
                enriched_anomalies = []
                for anomaly in anomalies:
                    enriched_anomalies.append({
                        **anomaly,
                        'best_matched_pattern': {
                            'pattern_id': best_pattern['pattern_id'],
                            'pattern_name': best_pattern['pattern_name'],
                            'match_score': best_pattern['match_score'],
                            'severity': best_pattern['severity'],
                            'root_cause_hint': best_pattern['root_cause_hint'],
                            'remediation_hint': best_pattern['remediation_hint']
                        }
                    })
                return enriched_anomalies, matched_patterns
        return anomalies, []
    
    def get_top_anomalies(self, df: pd.DataFrame, metrics: List[str], 
                           top_n: int = 20, score_threshold: float = 0.1) -> List[Dict]:
        all_anomalies = self.fuse_anomalies(df, metrics)
        filtered = [a for a in all_anomalies if a['total_score'] >= score_threshold]
        return filtered[:top_n]
    
    def detect_joint_anomalies(self, df: pd.DataFrame, metrics: List[str]) -> List[Dict]:
        all_anomalies = self.fuse_anomalies(df, metrics)
        joint_anomalies = [a for a in all_anomalies if a['is_joint_anomaly']]
        return joint_anomalies
    
    def get_anomaly_summary(self, df: pd.DataFrame, metrics: List[str]) -> Dict:
        all_anomalies = self.fuse_anomalies(df, metrics)
        
        summary = {
            'total_anomalies': len(all_anomalies),
            'joint_anomalies': len([a for a in all_anomalies if a['is_joint_anomaly']]),
            'single_metric_anomalies': len([a for a in all_anomalies if not a['is_joint_anomaly']]),
            'by_metric': defaultdict(int),
            'by_method': defaultdict(int),
            'high_severity': len([a for a in all_anomalies if a['total_score'] >= 0.7]),
            'medium_severity': len([a for a in all_anomalies if 0.3 <= a['total_score'] < 0.7]),
            'low_severity': len([a for a in all_anomalies if a['total_score'] < 0.3])
        }
        
        for anomaly in all_anomalies:
            for metric in anomaly['metrics']:
                summary['by_metric'][metric] += 1
            for method in anomaly['detected_by']:
                summary['by_method'][method] += 1
        
        return dict(summary)
    
    def get_time_series_with_anomalies(self, df: pd.DataFrame, metrics: List[str]) -> Dict[str, pd.DataFrame]:
        result = {}
        
        for metric in metrics:
            prophet_df = self.prophet_detector.detect_anomalies(df, metric)
            three_sigma_df = self.three_sigma_detector.detect_anomalies(df, metric)
            if_df = self.isolation_forest_detector.detect_anomalies(df, metric)
            
            combined_df = pd.DataFrame({
                'timestamp': df['timestamp'],
                'value': df[metric],
                'prophet_anomaly': prophet_df['is_anomaly'],
                'prophet_score': prophet_df['anomaly_score'],
                'three_sigma_anomaly': three_sigma_df['is_anomaly'],
                'three_sigma_score': three_sigma_df['anomaly_score'],
                'isolation_forest_anomaly': if_df['is_anomaly'],
                'isolation_forest_score': if_df['anomaly_score'],
                'fused_score': 0.0,
                'is_fused_anomaly': False
            })
            
            for i, row in combined_df.iterrows():
                score = (
                    row['prophet_score'] * self.weights['prophet'] +
                    row['three_sigma_score'] * self.weights['three_sigma'] +
                    row['isolation_forest_score'] * self.weights['isolation_forest']
                )
                combined_df.at[i, 'fused_score'] = score
                combined_df.at[i, 'is_fused_anomaly'] = score > 0.1
            
            result[metric] = combined_df
        
        return result
