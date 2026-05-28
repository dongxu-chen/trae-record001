import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

@dataclass
class AnomalyPattern:
    id: str
    name: str
    description: str
    severity: str
    metric_patterns: Dict[str, str]
    temporal_relation: str
    confidence: float
    root_cause_hint: str
    remediation_hint: str

class AnomalyPatternLibrary:
    def __init__(self):
        self.patterns = self._load_default_patterns()
        
    def _load_default_patterns(self) -> List[AnomalyPattern]:
        return [
            AnomalyPattern(
                id='PATTERN_001',
                name='流量过载导致性能下降',
                description='QPS突增伴随延迟上升、错误率升高，典型的系统过载现象',
                severity='CRITICAL',
                metric_patterns={
                    'qps': 'spike',
                    'latency': 'spike',
                    'error_rate': 'spike'
                },
                temporal_relation='simultaneous',
                confidence=0.95,
                root_cause_hint='流量超出系统处理能力，可能是业务高峰或攻击',
                remediation_hint='扩容、限流、降级'
            ),
            AnomalyPattern(
                id='PATTERN_002',
                name='下游服务故障',
                description='错误率和延迟同时突增但QPS正常，说明下游依赖服务故障',
                severity='CRITICAL',
                metric_patterns={
                    'qps': 'normal',
                    'latency': 'spike',
                    'error_rate': 'spike'
                },
                temporal_relation='simultaneous',
                confidence=0.90,
                root_cause_hint='下游服务超时或报错，可能是数据库、缓存或第三方API',
                remediation_hint='检查依赖服务状态、熔断降级'
            ),
            AnomalyPattern(
                id='PATTERN_003',
                name='系统性能退化',
                description='QPS下降但延迟上升，说明系统内部处理效率降低',
                severity='HIGH',
                metric_patterns={
                    'qps': 'drop',
                    'latency': 'spike',
                    'error_rate': 'normal'
                },
                temporal_relation='simultaneous',
                confidence=0.85,
                root_cause_hint='可能是内存泄漏、GC频繁、线程池耗尽',
                remediation_hint='重启服务、内存分析、线程dump'
            ),
            AnomalyPattern(
                id='PATTERN_004',
                name='数据库连接池耗尽',
                description='延迟逐渐上升后QPS骤降，典型的连接池耗尽模式',
                severity='CRITICAL',
                metric_patterns={
                    'latency': 'gradual_spike',
                    'qps': 'sudden_drop'
                },
                temporal_relation='sequential',
                confidence=0.88,
                root_cause_hint='数据库连接池耗尽，慢查询堆积',
                remediation_hint='增加连接池、优化SQL、索引优化'
            ),
            AnomalyPattern(
                id='PATTERN_005',
                name='缓存击穿',
                description='热点Key失效导致QPS和延迟同时波动',
                severity='HIGH',
                metric_patterns={
                    'qps': 'spike',
                    'latency': 'spike',
                    'error_rate': 'normal'
                },
                temporal_relation='simultaneous',
                confidence=0.80,
                root_cause_hint='热点缓存失效，请求穿透到数据库',
                remediation_hint='热点预热、互斥锁、永不过期'
            ),
            AnomalyPattern(
                id='PATTERN_006',
                name='发布引入Bug',
                description='发布后错误率持续升高，其他指标正常',
                severity='HIGH',
                metric_patterns={
                    'error_rate': 'step_increase',
                    'qps': 'normal',
                    'latency': 'normal'
                },
                temporal_relation='step_change',
                confidence=0.92,
                root_cause_hint='新版本代码引入Bug，可能是空指针、逻辑错误',
                remediation_hint='回滚版本、查看错误日志'
            ),
            AnomalyPattern(
                id='PATTERN_007',
                name='网络分区故障',
                description='所有指标同时剧烈波动，可能是网络问题',
                severity='CRITICAL',
                metric_patterns={
                    'qps': 'volatile',
                    'latency': 'volatile',
                    'error_rate': 'volatile'
                },
                temporal_relation='simultaneous',
                confidence=0.85,
                root_cause_hint='可能是网络抖动、DNS解析失败、负载均衡问题',
                remediation_hint='检查网络状态、切换可用区'
            ),
            AnomalyPattern(
                id='PATTERN_008',
                name='流量洪峰正常',
                description='业务活动导致QPS上升，但延迟和错误率稳定',
                severity='INFO',
                metric_patterns={
                    'qps': 'spike',
                    'latency': 'normal',
                    'error_rate': 'normal'
                },
                temporal_relation='simultaneous',
                confidence=0.80,
                root_cause_hint='正常业务高峰，系统处理正常',
                remediation_hint='无需处理，持续监控'
            ),
            AnomalyPattern(
                id='PATTERN_009',
                name='超时重试风暴',
                description='错误率升高触发重试，导致QPS放大',
                severity='CRITICAL',
                metric_patterns={
                    'error_rate': 'spike',
                    'qps': 'amplified_spike',
                    'latency': 'spike'
                },
                temporal_relation='sequential',
                confidence=0.85,
                root_cause_hint='初始错误触发重试机制，导致流量放大',
                remediation_hint='熔断、限制重试次数、退避策略'
            ),
            AnomalyPattern(
                id='PATTERN_010',
                name='资源耗尽',
                description='延迟持续升高最终QPS下降，典型资源耗尽',
                severity='CRITICAL',
                metric_patterns={
                    'latency': 'gradual_increase',
                    'qps': 'eventual_drop'
                },
                temporal_relation='sequential',
                confidence=0.90,
                root_cause_hint='CPU、内存、磁盘IO等系统资源耗尽',
                remediation_hint='扩容、优化资源使用、限流'
            )
        ]
    
    def add_custom_pattern(self, pattern: AnomalyPattern):
        self.patterns.append(pattern)
    
    def match_patterns(self, anomalies: List[Dict], df: pd.DataFrame,
                        time_window_minutes: int = 15) -> List[Dict]:
        matched_patterns = []
        
        for pattern in self.patterns:
            match_result = self._match_single_pattern(pattern, anomalies, df, time_window_minutes)
            if match_result:
                matched_patterns.append(match_result)
        
        matched_patterns.sort(key=lambda x: x['match_score'], reverse=True)
        return matched_patterns
    
    def _match_single_pattern(self, pattern: AnomalyPattern, anomalies: List[Dict],
                               df: pd.DataFrame, time_window: int) -> Optional[Dict]:
        if not anomalies:
            return None
        
        metric_anomalies = {}
        for metric, required_type in pattern.metric_patterns.items():
            metric_anomalies[metric] = [
                a for a in anomalies 
                if metric in a.get('metrics', {}) or a.get('metric') == metric
            ]
        
        match_score = 0.0
        matched_metrics = []
        
        for metric, required_type in pattern.metric_patterns.items():
            if required_type == 'normal':
                if len(metric_anomalies[metric]) == 0:
                    match_score += 1.0
                    matched_metrics.append(metric)
            else:
                type_matches = [
                    a for a in metric_anomalies[metric]
                    if self._check_anomaly_type(a, metric, required_type)
                ]
                if type_matches:
                    match_score += 1.0
                    matched_metrics.append(metric)
        
        if len(pattern.metric_patterns) > 0:
            match_score = match_score / len(pattern.metric_patterns)
        
        temporal_score = self._check_temporal_relation(
            pattern.temporal_relation, anomalies, time_window
        )
        final_score = match_score * 0.7 + temporal_score * 0.3
        
        final_score *= pattern.confidence
        
        if final_score >= 0.6:
            return {
                'pattern_id': pattern.id,
                'pattern_name': pattern.name,
                'description': pattern.description,
                'severity': pattern.severity,
                'match_score': final_score,
                'matched_metrics': matched_metrics,
                'root_cause_hint': pattern.root_cause_hint,
                'remediation_hint': pattern.remediation_hint,
                'pattern_confidence': pattern.confidence
            }
        
        return None
    
    def _check_anomaly_type(self, anomaly: Dict, metric: str, required_type: str) -> bool:
        anomaly_types = []
        
        if 'metrics' in anomaly and metric in anomaly['metrics']:
            anomaly_types = anomaly['metrics'][metric].get('anomaly_types', [])
        elif anomaly.get('metric') == metric:
            anomaly_types = [anomaly.get('anomaly_type', '')]
        
        type_mapping = {
            'spike': ['spike'],
            'drop': ['drop'],
            'gradual_spike': ['spike'],
            'sudden_drop': ['drop'],
            'gradual_increase': ['spike'],
            'eventual_drop': ['drop'],
            'step_increase': ['spike'],
            'volatile': ['spike', 'drop'],
            'amplified_spike': ['spike']
        }
        
        allowed_types = type_mapping.get(required_type, [required_type])
        return any(t in allowed_types for t in anomaly_types)
    
    def _check_temporal_relation(self, relation: str, anomalies: List[Dict],
                                  window_minutes: int) -> float:
        if len(anomalies) < 2:
            return 1.0 if relation == 'simultaneous' else 0.5
        
        timestamps = [a['timestamp'] for a in anomalies]
        min_time = min(timestamps)
        max_time = max(timestamps)
        time_span = (max_time - min_time).total_seconds() / 60
        
        if relation == 'simultaneous':
            if time_span <= window_minutes:
                return 1.0
            elif time_span <= window_minutes * 2:
                return 0.7
            else:
                return 0.3
        elif relation == 'sequential':
            if window_minutes < time_span <= window_minutes * 3:
                return 1.0
            else:
                return 0.5
        elif relation == 'step_change':
            return 0.8
        else:
            return 0.5
    
    def get_pattern_by_id(self, pattern_id: str) -> Optional[AnomalyPattern]:
        for pattern in self.patterns:
            if pattern.id == pattern_id:
                return pattern
        return None
    
    def get_all_patterns(self) -> List[Dict]:
        return [
            {
                'id': p.id,
                'name': p.name,
                'description': p.description,
                'severity': p.severity,
                'metric_patterns': p.metric_patterns,
                'confidence': p.confidence,
                'root_cause_hint': p.root_cause_hint
            }
            for p in self.patterns
        ]
    
    def match_and_enrich_anomalies(self, anomalies: List[Dict], 
                                    df: pd.DataFrame) -> List[Dict]:
        matched_patterns = self.match_patterns(anomalies, df)
        
        if matched_patterns:
            best_pattern = matched_patterns[0]
            for anomaly in anomalies:
                anomaly['matched_pattern'] = {
                    'id': best_pattern['pattern_id'],
                    'name': best_pattern['pattern_name'],
                    'match_score': best_pattern['match_score'],
                    'root_cause_hint': best_pattern['root_cause_hint']
                }
        
        return anomalies, matched_patterns
