import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
from config import Config

class RootCauseAnalyzer:
    def __init__(self, history_window_days: int = None):
        self.history_window = history_window_days or Config.ROOT_CAUSE_HISTORY_WINDOW
        self.cause_prior_probabilities = self._initialize_prior_probabilities()
        
    def _initialize_prior_probabilities(self) -> Dict[str, float]:
        return {
            'traffic_overload': 0.15,
            'service_failure': 0.20,
            'performance_degradation': 0.12,
            'systemic_issue': 0.10,
            'database_issue': 0.12,
            'cache_issue': 0.08,
            'network_issue': 0.10,
            'release_bug': 0.08,
            'resource_exhaustion': 0.05
        }
        
    def analyze_root_causes(self, df: pd.DataFrame, anomalies: List[Dict], 
                            metrics: List[str]) -> List[Dict]:
        results = []
        
        for anomaly in anomalies:
            root_causes = self._analyze_single_anomaly(df, anomaly, metrics)
            anomaly_with_root = anomaly.copy()
            anomaly_with_root['root_cause_candidates'] = root_causes
            
            if root_causes:
                anomaly_with_root['most_probable_root_cause'] = root_causes[0]
            else:
                anomaly_with_root['most_probable_root_cause'] = None
                
            results.append(anomaly_with_root)
        
        return results
    
    def _analyze_single_anomaly(self, df: pd.DataFrame, anomaly: Dict, 
                                 metrics: List[str]) -> List[Dict]:
        timestamp = anomaly['timestamp']
        root_causes = []
        
        pattern_hint = None
        if 'best_matched_pattern' in anomaly:
            pattern_hint = anomaly['best_matched_pattern']['root_cause_hint']
        
        correlation_causes = self._analyze_correlation(df, timestamp, metrics)
        root_causes.extend(correlation_causes)
        
        trend_causes = self._analyze_trend_change(df, timestamp, metrics)
        root_causes.extend(trend_causes)
        
        historical_causes = self._analyze_historical_patterns(df, timestamp, metrics)
        root_causes.extend(historical_causes)
        
        domain_causes = self._analyze_domain_knowledge(anomaly, pattern_hint)
        root_causes.extend(domain_causes)
        
        root_causes_with_prob = self._calculate_posterior_probabilities(root_causes, anomaly)
        
        root_causes_with_prob.sort(key=lambda x: x['posterior_probability'], reverse=True)
        
        return root_causes_with_prob[:5]
    
    def _calculate_posterior_probabilities(self, causes: List[Dict], 
                                            anomaly: Dict) -> List[Dict]:
        if not causes:
            return []
        
        evidence_strength = self._calculate_evidence_strength(anomaly)
        
        causes_with_prob = []
        for cause in causes:
            cause_type = cause.get('cause', cause.get('cause_type', 'unknown'))
            
            prior = self.cause_prior_probabilities.get(cause_type, 0.05)
            likelihood = cause.get('confidence', 0.5)
            
            posterior = self._bayesian_update(prior, likelihood, evidence_strength)
            
            cause_with_prob = cause.copy()
            cause_with_prob['prior_probability'] = prior
            cause_with_prob['likelihood'] = likelihood
            cause_with_prob['posterior_probability'] = posterior
            cause_with_prob['probability_rank'] = 0
            
            causes_with_prob.append(cause_with_prob)
        
        causes_with_prob.sort(key=lambda x: x['posterior_probability'], reverse=True)
        
        for i, cause in enumerate(causes_with_prob):
            cause['probability_rank'] = i + 1
        
        total_prob = sum(c['posterior_probability'] for c in causes_with_prob)
        if total_prob > 0:
            for cause in causes_with_prob:
                cause['normalized_probability'] = cause['posterior_probability'] / total_prob
        
        return causes_with_prob
    
    def _bayesian_update(self, prior: float, likelihood: float, 
                         evidence_strength: float) -> float:
        posterior = prior * likelihood * evidence_strength
        return min(1.0, posterior * 2)
    
    def _calculate_evidence_strength(self, anomaly: Dict) -> float:
        strength = 1.0
        
        if anomaly.get('is_joint_anomaly', False):
            strength *= 1.3
        
        anomaly_score = anomaly.get('total_score', 0.5)
        strength *= (0.7 + anomaly_score * 0.6)
        
        if 'best_matched_pattern' in anomaly:
            match_score = anomaly['best_matched_pattern'].get('match_score', 0)
            strength *= (0.8 + match_score * 0.4)
        
        return min(2.0, strength)
    
    def _analyze_correlation(self, df: pd.DataFrame, timestamp: datetime, 
                              metrics: List[str]) -> List[Dict]:
        causes = []
        
        window_before = 24
        idx = df[df['timestamp'] == timestamp].index
        if len(idx) == 0:
            return causes
        
        idx = idx[0]
        start_idx = max(0, idx - window_before)
        end_idx = min(len(df), idx + 1)
        
        window_df = df.iloc[start_idx:end_idx]
        
        if len(window_df) < 2:
            return causes
        
        correlation_matrix = window_df[metrics].corr()
        
        for metric1 in metrics:
            for metric2 in metrics:
                if metric1 >= metric2:
                    continue
                
                corr = correlation_matrix.loc[metric1, metric2]
                
                if abs(corr) > 0.8:
                    direction = 'positive' if corr > 0 else 'negative'
                    causes.append({
                        'cause_type': 'correlation',
                        'metric1': metric1,
                        'metric2': metric2,
                        'correlation': corr,
                        'direction': direction,
                        'confidence': min(1.0, abs(corr)),
                        'description': f'{metric1}和{metric2}呈{direction}强相关 (r={corr:.2f})'
                    })
        
        return causes
    
    def _analyze_trend_change(self, df: pd.DataFrame, timestamp: datetime,
                               metrics: List[str]) -> List[Dict]:
        causes = []
        
        window_size = 12
        idx = df[df['timestamp'] == timestamp].index
        if len(idx) == 0:
            return causes
        
        idx = idx[0]
        
        for metric in metrics:
            if idx < window_size * 2 or idx + window_size >= len(df):
                continue
            
            before_window = df[metric].iloc[idx - window_size:idx]
            after_window = df[metric].iloc[idx:idx + window_size]
            
            before_mean = before_window.mean()
            after_mean = after_window.mean()
            before_std = before_window.std()
            after_std = after_window.std()
            
            mean_change_pct = abs(after_mean - before_mean) / (before_mean + 1e-10) * 100
            std_change_pct = abs(after_std - before_std) / (before_std + 1e-10) * 100
            
            if mean_change_pct > 20 or std_change_pct > 30:
                change_direction = '上升' if after_mean > before_mean else '下降'
                causes.append({
                    'cause_type': 'trend_change',
                    'metric': metric,
                    'mean_change_pct': mean_change_pct,
                    'std_change_pct': std_change_pct,
                    'change_direction': change_direction,
                    'confidence': min(1.0, (mean_change_pct + std_change_pct) / 100),
                    'description': f'{metric}在异常点前后发生{change_direction}趋势变化 (均值变化: {mean_change_pct:.1f}%, 方差变化: {std_change_pct:.1f}%)'
                })
        
        return causes
    
    def _analyze_historical_patterns(self, df: pd.DataFrame, timestamp: datetime,
                                      metrics: List[str]) -> List[Dict]:
        causes = []
        
        hour = timestamp.hour
        day_of_week = timestamp.dayofweek
        
        historical_data = df[
            (df['timestamp'].dt.hour == hour) &
            (df['timestamp'].dt.dayofweek == day_of_week) &
            (df['timestamp'] < timestamp)
        ]
        
        if len(historical_data) == 0:
            return causes
        
        idx = df[df['timestamp'] == timestamp].index[0]
        current_row = df.iloc[idx]
        
        for metric in metrics:
            historical_mean = historical_data[metric].mean()
            historical_std = historical_data[metric].std()
            current_value = current_row[metric]
            
            z_score = abs(current_value - historical_mean) / (historical_std + 1e-10)
            
            if z_score > 2:
                deviation_direction = '偏高' if current_value > historical_mean else '偏低'
                causes.append({
                    'cause_type': 'historical_deviation',
                    'metric': metric,
                    'historical_mean': historical_mean,
                    'current_value': current_value,
                    'z_score': z_score,
                    'deviation_direction': deviation_direction,
                    'confidence': min(1.0, z_score / 5),
                    'description': f'{metric}偏离历史同期水平{deviation_direction} (Z-score: {z_score:.2f})'
                })
        
        return causes
    
    def _analyze_domain_knowledge(self, anomaly: Dict) -> List[Dict]:
        causes = []
        
        affected_metrics = list(anomaly['metrics'].keys())
        anomaly_types = set()
        for metric_data in anomaly['metrics'].values():
            anomaly_types.update(metric_data['anomaly_types'])
        
        if 'qps' in affected_metrics and 'latency' in affected_metrics:
            qps_types = anomaly['metrics']['qps']['anomaly_types']
            latency_types = anomaly['metrics']['latency']['anomaly_types']
            
            if 'spike' in qps_types and 'spike' in latency_types:
                causes.append({
                    'cause_type': 'domain_knowledge',
                    'cause': 'traffic_overload',
                    'confidence': 0.85,
                    'description': 'QPS和延迟同时突增，可能是流量过载导致系统处理能力饱和'
                })
            elif 'drop' in qps_types and 'spike' in latency_types:
                causes.append({
                    'cause_type': 'domain_knowledge',
                    'cause': 'performance_degradation',
                    'confidence': 0.75,
                    'description': 'QPS下降但延迟上升，可能是系统性能退化或依赖服务故障'
                })
        
        if 'error_rate' in affected_metrics and 'latency' in affected_metrics:
            error_types = anomaly['metrics']['error_rate']['anomaly_types']
            latency_types = anomaly['metrics']['latency']['anomaly_types']
            
            if 'spike' in error_types and 'spike' in latency_types:
                causes.append({
                    'cause_type': 'domain_knowledge',
                    'cause': 'service_failure',
                    'confidence': 0.9,
                    'description': '错误率和延迟同时突增，极有可能是下游服务故障或超时'
                })
        
        if len(affected_metrics) >= 2:
            causes.append({
                'cause_type': 'domain_knowledge',
                'cause': 'systemic_issue',
                'confidence': 0.7,
                'description': '多个指标同时异常，可能是系统性问题而非单一组件故障'
            })
        
        return causes
    
    def generate_incident_report(self, anomaly: Dict) -> Dict:
        report = {
            'timestamp': anomaly['timestamp'],
            'severity': self._get_severity(anomaly['total_score']),
            'affected_metrics': list(anomaly['metrics'].keys()),
            'summary': self._generate_summary(anomaly),
            'recommendations': self._generate_recommendations(anomaly)
        }
        return report
    
    def _get_severity(self, score: float) -> str:
        if score >= 0.7:
            return 'CRITICAL'
        elif score >= 0.3:
            return 'WARNING'
        else:
            return 'INFO'
    
    def _generate_summary(self, anomaly: Dict) -> str:
        metrics = ', '.join(anomaly['metrics'].keys())
        severity = self._get_severity(anomaly['total_score'])
        return f"{severity}级别异常: {metrics} 在 {anomaly['timestamp']} 发生异常波动"
    
    def _generate_recommendations(self, anomaly: Dict) -> List[str]:
        recommendations = []
        affected_metrics = list(anomaly['metrics'].keys())
        
        recommendations.append('查看相关监控仪表盘确认异常影响范围')
        recommendations.append('检查系统日志寻找错误信息和异常堆栈')
        
        if 'qps' in affected_metrics:
            recommendations.append('检查流量来源，确认是否为恶意请求或正常业务增长')
        
        if 'latency' in affected_metrics:
            recommendations.append('分析依赖服务的响应时间，排查性能瓶颈')
        
        if 'error_rate' in affected_metrics:
            recommendations.append('检查错误日志，识别具体错误类型和发生频率')
        
        if len(affected_metrics) >= 2:
            recommendations.append('考虑近期发布变更，可能需要回滚验证')
        
        return recommendations
