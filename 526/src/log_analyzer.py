import re
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field

import pandas as pd
import numpy as np

from .utils import (
    extract_endpoint_pattern,
    parse_timestamp,
    extract_fields_from_response,
    calculate_size_bytes,
    calculate_redundancy_ratio,
    group_by_time_window,
    normalize_params,
    compute_content_hash,
    parse_url_params,
    get_nested_value,
    DATA_FRESHNESS_TAGS,
    classify_data_freshness
)


@dataclass
class LogEntry:
    """日志条目数据类"""
    timestamp: Optional[datetime] = None
    method: str = "GET"
    endpoint: str = ""
    status_code: int = 200
    response_time_ms: float = 0.0
    response_size: int = 0
    user_id: Optional[str] = None
    request_params: Dict[str, Any] = field(default_factory=dict)
    response_body: Optional[Dict[str, Any]] = None
    raw_log: str = ""
    normalized_params: Dict[str, Any] = field(default_factory=dict)
    content_hash: str = ""
    freshness_tag: Optional[str] = None


@dataclass
class ContentDuplicateGroup:
    """内容重复组"""
    content_hash: str
    pattern: str
    request_count: int
    unique_params_count: int
    total_response_size: int
    avg_response_time: float
    endpoints: List[str]
    sample_response: Optional[Dict[str, Any]] = None


class LogParser:
    """访问日志解析器"""
    
    def __init__(self):
        self.patterns = [
            re.compile(
                r'(?P<ip>[\d.,]+|-) (?P<user>[\w-]+) (?P<auth>[\w-]+) '
                r'\[(?P<timestamp>[^\]]+)\] "(?P<method>\w+) (?P<path>[^\s?]+)(?P<query>\?[^"]*)? (?P<protocol>[^"]+)" '
                r'(?P<status>\d+) (?P<size>\d+|-)'
            ),
            re.compile(
                r'(?P<timestamp>\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}[.\d]*[Zz]?)'
                r'.*?(?P<method>GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)'
                r'.*?(?P<endpoint>/[^\s"]+).*?'
                r'(?P<status>\d{3}).*?'
                r'(?P<size>\d+).*?'
                r'(?P<time>\d+\.?\d*)\s*(ms|s)?'
            ),
            re.compile(
                r'\{"timestamp":\s*"(?P<timestamp>[^"]+)".*?'
                r'"method":\s*"(?P<method>[^"]+)".*?'
                r'"endpoint":\s*"(?P<endpoint>[^"]+)".*?'
                r'"status":\s*(?P<status>\d+).*?'
                r'"size":\s*(?P<size>\d+).*?'
                r'"responseTime":\s*(?P<time>\d+\.?\d*)'
            ),
        ]
    
    def parse_line(self, line: str) -> Optional[LogEntry]:
        """解析单行日志"""
        line = line.strip()
        if not line:
            return None
        
        entry = LogEntry(raw_log=line)
        
        if line.startswith('{'):
            try:
                data = json.loads(line)
                entry.timestamp = parse_timestamp(data.get('timestamp', ''))
                entry.method = data.get('method', 'GET')
                entry.endpoint = data.get('endpoint', data.get('path', ''))
                entry.status_code = int(data.get('status', 200))
                entry.response_size = int(data.get('size', data.get('responseSize', 0)))
                entry.response_time_ms = float(data.get('responseTime', data.get('latency', 0)))
                entry.user_id = data.get('userId', data.get('user_id'))
                entry.request_params = data.get('params', {})
                entry.response_body = data.get('response', data.get('responseBody'))
                
                entry.normalized_params = normalize_params(entry.request_params)
                if entry.response_body:
                    entry.content_hash = compute_content_hash(entry.response_body)
                entry.freshness_tag = classify_data_freshness(
                    entry.endpoint, entry.response_body, entry.normalized_params
                ).tag
                
                return entry
            except (json.JSONDecodeError, ValueError):
                pass
        
        for pattern in self.patterns:
            match = pattern.search(line)
            if match:
                groups = match.groupdict()
                entry.timestamp = parse_timestamp(groups.get('timestamp', ''))
                entry.method = groups.get('method', 'GET')
                entry.endpoint = groups.get('endpoint', groups.get('path', ''))
                entry.status_code = int(groups.get('status', '200'))
                size = groups.get('size', '0')
                entry.response_size = 0 if size == '-' else int(size)
                
                time_str = groups.get('time', '')
                if time_str:
                    try:
                        entry.response_time_ms = float(time_str)
                        if groups.get('') and 's' in groups.get('', ''):
                            entry.response_time_ms *= 1000
                    except ValueError:
                        pass
                
                if groups.get('query'):
                    try:
                        query = groups['query'].lstrip('?')
                        params = {}
                        for kv in query.split('&'):
                            if '=' in kv:
                                k, v = kv.split('=', 1)
                                params[k] = v
                        entry.request_params = params
                    except Exception:
                        pass
                
                if '?' in entry.endpoint:
                    url_params = parse_url_params(entry.endpoint)
                    entry.request_params.update(url_params)
                    entry.endpoint = entry.endpoint.split('?')[0]
                
                entry.normalized_params = normalize_params(entry.request_params)
                if entry.response_body:
                    entry.content_hash = compute_content_hash(entry.response_body)
                entry.freshness_tag = classify_data_freshness(
                    entry.endpoint, entry.response_body, entry.normalized_params
                ).tag
                
                return entry
        
        return None
    
    def parse_file(self, filepath: str) -> List[LogEntry]:
        """解析日志文件"""
        entries = []
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                entry = self.parse_line(line)
                if entry:
                    entries.append(entry)
        return entries


class AccessLogAnalyzer:
    """访问日志分析器"""
    
    def __init__(self):
        self.parser = LogParser()
        self.entries: List[LogEntry] = []
        self.df: Optional[pd.DataFrame] = None
        self._analysis_cache: Dict[str, Any] = {}
    
    def load_logs(self, filepath: str) -> int:
        """加载日志文件"""
        self.entries = self.parser.parse_file(filepath)
        self._build_dataframe()
        self._analysis_cache.clear()
        return len(self.entries)
    
    def load_entries(self, entries: List[LogEntry]) -> int:
        """直接加载日志条目"""
        self.entries = entries
        self._build_dataframe()
        self._analysis_cache.clear()
        return len(self.entries)
    
    def _build_dataframe(self) -> None:
        """构建DataFrame用于分析"""
        if not self.entries:
            self.df = None
            return
        
        data = []
        for entry in self.entries:
            normalized_params_json = json.dumps(entry.normalized_params, sort_keys=True, ensure_ascii=False)
            data.append({
                'timestamp': entry.timestamp,
                'method': entry.method,
                'endpoint': entry.endpoint,
                'pattern': extract_endpoint_pattern(entry.endpoint),
                'status_code': entry.status_code,
                'response_time_ms': entry.response_time_ms,
                'response_size': entry.response_size,
                'user_id': entry.user_id,
                'normalized_params': normalized_params_json,
                'content_hash': entry.content_hash,
                'freshness_tag': entry.freshness_tag,
            })
        
        self.df = pd.DataFrame(data)
        if 'timestamp' in self.df.columns and not self.df.empty:
            self.df = self.df.sort_values('timestamp').reset_index(drop=True)
    
    def get_basic_stats(self) -> Dict[str, Any]:
        """获取基本统计信息"""
        if self.df is None or self.df.empty:
            return {}
        
        if 'basic_stats' in self._analysis_cache:
            return self._analysis_cache['basic_stats']
        
        stats = {
            'total_requests': len(self.df),
            'unique_endpoints': self.df['endpoint'].nunique(),
            'unique_patterns': self.df['pattern'].nunique(),
            'time_span': self._get_time_span(),
            'avg_response_time_ms': self.df['response_time_ms'].mean(),
            'p50_response_time_ms': self.df['response_time_ms'].median(),
            'p95_response_time_ms': self.df['response_time_ms'].quantile(0.95),
            'avg_response_size': self.df['response_size'].mean(),
            'total_response_size': self.df['response_size'].sum(),
            'success_rate': (self.df['status_code'] < 400).mean() * 100,
            'method_distribution': self.df['method'].value_counts().to_dict(),
            'status_distribution': self.df['status_code'].value_counts().head(10).to_dict(),
        }
        
        self._analysis_cache['basic_stats'] = stats
        return stats
    
    def _get_time_span(self) -> Dict[str, Any]:
        """获取时间跨度"""
        if self.df is None or self.df.empty:
            return {}
        
        timestamps = self.df['timestamp'].dropna()
        if timestamps.empty:
            return {}
        
        min_ts = timestamps.min()
        max_ts = timestamps.max()
        delta = max_ts - min_ts
        
        return {
            'start': min_ts.isoformat() if min_ts else None,
            'end': max_ts.isoformat() if max_ts else None,
            'duration_hours': delta.total_seconds() / 3600,
            'duration_days': delta.total_seconds() / 86400,
        }
    
    def get_endpoint_frequency(self, top_n: int = 20) -> pd.DataFrame:
        """获取端点访问频率"""
        if self.df is None or self.df.empty:
            return pd.DataFrame()
        
        cache_key = f'endpoint_freq_{top_n}'
        if cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]
        
        grouped = self.df.groupby('pattern').agg({
            'endpoint': 'count',
            'response_time_ms': ['mean', 'median'],
            'response_size': ['mean', 'sum'],
            'user_id': 'nunique',
        }).reset_index()
        
        grouped.columns = ['pattern', 'request_count', 'avg_response_time', 
                          'median_response_time', 'avg_response_size', 
                          'total_response_size', 'unique_users']
        
        grouped = grouped.sort_values('request_count', ascending=False).head(top_n)
        grouped['duplication_rate'] = grouped.apply(
            lambda row: 1 - (row['unique_users'] / row['request_count']) 
            if row['request_count'] > 0 else 0,
            axis=1
        )
        
        self._analysis_cache[cache_key] = grouped
        return grouped
    
    def analyze_duplication_patterns(self) -> Dict[str, Any]:
        """分析重复请求模式"""
        if self.df is None or self.df.empty:
            return {}
        
        if 'duplication' in self._analysis_cache:
            return self._analysis_cache['duplication']
        
        endpoint_counts = self.df['pattern'].value_counts()
        repeated_endpoints = endpoint_counts[endpoint_counts > 1]
        
        total_repeated_requests = repeated_endpoints.sum()
        unique_repeated_endpoints = len(repeated_endpoints)
        
        duplicate_stats = []
        for pattern, count in repeated_endpoints.items():
            subset = self.df[self.df['pattern'] == pattern]
            timestamps = subset['timestamp'].dropna()
            
            if len(timestamps) >= 2:
                intervals = timestamps.diff().dropna().dt.total_seconds()
                stats = {
                    'pattern': pattern,
                    'request_count': count,
                    'avg_interval_seconds': intervals.mean(),
                    'median_interval_seconds': intervals.median(),
                    'min_interval_seconds': intervals.min(),
                    'total_response_size': subset['response_size'].sum(),
                    'avg_response_time': subset['response_time_ms'].mean(),
                }
                duplicate_stats.append(stats)
        
        duplicate_df = pd.DataFrame(duplicate_stats)
        
        result = {
            'total_requests': len(self.df),
            'repeated_requests': total_repeated_requests,
            'duplication_ratio': total_repeated_requests / len(self.df) if len(self.df) > 0 else 0,
            'unique_endpoints_with_duplicates': unique_repeated_endpoints,
            'total_duplicate_endpoints': len(repeated_endpoints),
            'endpoint_duplication_stats': duplicate_df,
            'time_based_duplication': self._analyze_time_based_duplication(),
        }
        
        self._analysis_cache['duplication'] = result
        return result
    
    def _analyze_time_based_duplication(self) -> Dict[str, Any]:
        """分析基于时间的重复模式"""
        if self.df is None or self.df.empty:
            return {}
        
        timestamps = self.df['timestamp'].dropna()
        if timestamps.empty:
            return {}
        
        hourly_counts = timestamps.dt.hour.value_counts().sort_index()
        weekday_counts = timestamps.dt.dayofweek.value_counts().sort_index()
        
        time_groups = group_by_time_window(timestamps.tolist(), 60)
        
        return {
            'hourly_distribution': hourly_counts.to_dict(),
            'weekday_distribution': weekday_counts.to_dict(),
            'hourly_request_count': time_groups,
            'peak_hour': hourly_counts.idxmax() if not hourly_counts.empty else None,
            'quiet_hour': hourly_counts.idxmin() if not hourly_counts.empty else None,
        }
    
    def analyze_content_hash_duplication(self) -> Dict[str, Any]:
        """
        基于内容哈希分析重复请求
        识别参数不同但响应内容相同的请求
        """
        if self.df is None or self.df.empty:
            return {}
        
        if 'content_hash_duplication' in self._analysis_cache:
            return self._analysis_cache['content_hash_duplication']
        
        entries_with_hash = [e for e in self.entries if e.content_hash and e.response_body]
        
        hash_groups = defaultdict(list)
        for entry in entries_with_hash:
            hash_groups[entry.content_hash].append(entry)
        
        duplicate_groups = []
        for content_hash, group_entries in hash_groups.items():
            if len(group_entries) >= 2:
                patterns = set(extract_endpoint_pattern(e.endpoint) for e in group_entries)
                pattern = list(patterns)[0] if len(patterns) == 1 else 'mixed'
                
                unique_params = set()
                for e in group_entries:
                    params_key = json.dumps(e.normalized_params, sort_keys=True, ensure_ascii=False)
                    unique_params.add(params_key)
                
                total_size = sum(e.response_size for e in group_entries)
                avg_rt = sum(e.response_time_ms for e in group_entries) / len(group_entries)
                
                duplicate_groups.append(ContentDuplicateGroup(
                    content_hash=content_hash,
                    pattern=pattern,
                    request_count=len(group_entries),
                    unique_params_count=len(unique_params),
                    total_response_size=total_size,
                    avg_response_time=avg_rt,
                    endpoints=[e.endpoint for e in group_entries],
                    sample_response=group_entries[0].response_body
                ))
        
        duplicate_groups.sort(key=lambda x: x.request_count, reverse=True)
        
        total_same_content_requests = sum(g.request_count for g in duplicate_groups)
        unique_duplicate_hashes = len(duplicate_groups)
        
        potential_savings = 0
        for g in duplicate_groups:
            if g.unique_params_count > 1:
                first_size = g.total_response_size / g.request_count
                potential_savings += int(first_size * (g.request_count - 1))
        
        df_groups = pd.DataFrame([{
            'content_hash': g.content_hash[:16] + '...',
            'pattern': g.pattern,
            'request_count': g.request_count,
            'unique_params_count': g.unique_params_count,
            'total_response_size': g.total_response_size,
            'avg_response_time': g.avg_response_time,
            'has_different_params': g.unique_params_count > 1,
        } for g in duplicate_groups])
        
        result = {
            'total_duplicate_groups': unique_duplicate_hashes,
            'total_same_content_requests': total_same_content_requests,
            'same_content_ratio': total_same_content_requests / len(entries_with_hash) if entries_with_hash else 0,
            'potential_savings_bytes': potential_savings,
            'groups_with_different_params': sum(1 for g in duplicate_groups if g.unique_params_count > 1),
            'duplicate_groups': duplicate_groups,
            'groups_dataframe': df_groups,
        }
        
        self._analysis_cache['content_hash_duplication'] = result
        return result
    
    def analyze_response_similarity(self) -> Dict[str, Any]:
        """分析响应相似度和冗余（基于内容哈希优化）"""
        if self.df is None or self.df.empty:
            return {}
        
        if 'similarity' in self._analysis_cache:
            return self._analysis_cache['similarity']
        
        result = {}
        
        hash_to_pattern = {}
        for entry in self.entries:
            if entry.response_body and entry.endpoint:
                pattern = extract_endpoint_pattern(entry.endpoint)
                
                if entry.content_hash:
                    hash_to_pattern[entry.content_hash] = pattern
                
                if pattern not in result:
                    result[pattern] = {
                        'responses': [],
                        'response_hashes': set(),
                        'fields': set(),
                        'sizes': [],
                    }
                result[pattern]['responses'].append(entry.response_body)
                if entry.content_hash:
                    result[pattern]['response_hashes'].add(entry.content_hash)
                result[pattern]['fields'].update(
                    extract_fields_from_response(entry.response_body)
                )
                result[pattern]['sizes'].append(calculate_size_bytes(entry.response_body))
        
        similarity_results = []
        for pattern, data in result.items():
            if len(data['responses']) >= 2:
                unique_hashes = len(data['response_hashes'])
                total_responses = len(data['responses'])
                content_duplication_ratio = 1 - (unique_hashes / total_responses) if total_responses > 0 else 0
                
                field_redundancy = {}
                all_fields = list(data['fields'])
                
                for field in all_fields:
                    values = []
                    for resp in data['responses']:
                        val = get_nested_value(resp, field)
                        if val is not None:
                            values.append(val)
                    
                    if values:
                        redundancy = calculate_redundancy_ratio(values)
                        field_redundancy[field] = {
                            'redundancy_ratio': redundancy,
                            'values_count': len(values),
                            'unique_values': len(set([json.dumps(v, sort_keys=True) for v in values])),
                        }
                
                avg_size = np.mean(data['sizes']) if data['sizes'] else 0
                similarity_results.append({
                    'pattern': pattern,
                    'response_count': total_responses,
                    'unique_content_hashes': unique_hashes,
                    'content_duplication_ratio': content_duplication_ratio,
                    'total_fields': len(all_fields),
                    'avg_response_size': avg_size,
                    'field_redundancy': field_redundancy,
                    'cacheable_fields': [
                        f for f, r in field_redundancy.items() 
                        if r['redundancy_ratio'] > 0.5
                    ],
                    'overall_redundancy': np.mean([
                        r['redundancy_ratio'] for r in field_redundancy.values()
                    ]) if field_redundancy else 0,
                })
        
        final_result = {
            'endpoints_analyzed': len(result),
            'endpoints_with_multiple_responses': len(similarity_results),
            'similarity_details': pd.DataFrame(similarity_results) if similarity_results else pd.DataFrame(),
        }
        
        self._analysis_cache['similarity'] = final_result
        return final_result
    
    @staticmethod
    def _get_nested_value(data: Any, path: str) -> Any:
        """通过点路径获取嵌套值"""
        try:
            keys = path.replace('[', '.').replace(']', '').split('.')
            keys = [k for k in keys if k]
            
            current = data
            for key in keys:
                if isinstance(current, dict):
                    current = current.get(key)
                elif isinstance(current, list) and key.isdigit():
                    idx = int(key)
                    current = current[idx] if idx < len(current) else None
                else:
                    return None
                
                if current is None:
                    return None
            
            return current
        except (KeyError, IndexError, TypeError):
            return None
    
    def get_requests_dataframe(self) -> Optional[pd.DataFrame]:
        """获取请求DataFrame"""
        return self.df
    
    def get_entries(self) -> List[LogEntry]:
        """获取原始日志条目"""
        return self.entries
