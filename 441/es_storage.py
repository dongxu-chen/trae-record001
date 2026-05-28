import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Optional
import json
from config import Config

try:
    from elasticsearch import Elasticsearch
    ES_AVAILABLE = True
except ImportError:
    ES_AVAILABLE = False
    print("Elasticsearch package not installed. Using fallback storage.")

class ElasticsearchStorage:
    def __init__(self, host: str = None, port: int = None, 
                 username: str = None, password: str = None, index: str = None):
        self.host = host or Config.ES_HOST
        self.port = port or Config.ES_PORT
        self.username = username or Config.ES_USER
        self.password = password or Config.ES_PASSWORD
        self.index = index or Config.ES_INDEX
        self.client = None
        self._fallback_data = {
            'metrics': [],
            'anomalies': []
        }
        
        if ES_AVAILABLE:
            self._connect()
        else:
            print("Using in-memory fallback storage.")
    
    def _connect(self):
        try:
            if self.username and self.password:
                self.client = Elasticsearch(
                    [{'host': self.host, 'port': self.port}],
                    http_auth=(self.username, self.password),
                    scheme='http'
                )
            else:
                self.client = Elasticsearch(
                    [{'host': self.host, 'port': self.port}],
                    scheme='http'
                )
            
            if not self.client.ping():
                print(f"Could not connect to Elasticsearch at {self.host}:{self.port}. Using fallback storage.")
                self.client = None
            else:
                self._create_index()
        except Exception as e:
            print(f"Elasticsearch connection error: {e}. Using fallback storage.")
            self.client = None
    
    def _create_index(self):
        if not self.client:
            return
        
        if not self.client.indices.exists(index=self.index):
            mappings = {
                'mappings': {
                    'properties': {
                        'timestamp': {'type': 'date'},
                        'metric_type': {'type': 'keyword'},
                        'value': {'type': 'float'},
                        'is_anomaly': {'type': 'boolean'},
                        'anomaly_score': {'type': 'float'},
                        'detection_method': {'type': 'keyword'},
                        'data_type': {'type': 'keyword'}
                    }
                }
            }
            self.client.indices.create(index=self.index, body=mappings)
        
        anomaly_index = f"{self.index}_anomalies"
        if not self.client.indices.exists(index=anomaly_index):
            anomaly_mappings = {
                'mappings': {
                    'properties': {
                        'timestamp': {'type': 'date'},
                        'total_score': {'type': 'float'},
                        'anomaly_count': {'type': 'integer'},
                        'is_joint_anomaly': {'type': 'boolean'},
                        'detected_by': {'type': 'keyword'},
                        'metrics': {'type': 'object', 'enabled': False},
                        'root_cause_candidates': {'type': 'object', 'enabled': False}
                    }
                }
            }
            self.client.indices.create(index=anomaly_index, body=anomaly_mappings)
    
    def store_metrics(self, df: pd.DataFrame):
        if self.client:
            self._store_metrics_es(df)
        else:
            self._store_metrics_fallback(df)
    
    def _store_metrics_es(self, df: pd.DataFrame):
        actions = []
        
        for _, row in df.iterrows():
            for metric in ['qps', 'latency', 'error_rate']:
                if metric in row:
                    doc = {
                        'timestamp': row['timestamp'],
                        'metric_type': metric,
                        'value': row[metric],
                        'data_type': 'metric'
                    }
                    actions.append({'index': {'_index': self.index}})
                    actions.append(doc)
        
        if actions:
            self.client.bulk(body=actions, refresh='wait_for')
    
    def _store_metrics_fallback(self, df: pd.DataFrame):
        for _, row in df.iterrows():
            for metric in ['qps', 'latency', 'error_rate']:
                if metric in row:
                    self._fallback_data['metrics'].append({
                        'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                        'metric_type': metric,
                        'value': row[metric]
                    })
    
    def store_anomalies(self, anomalies: List[Dict]):
        if self.client:
            self._store_anomalies_es(anomalies)
        else:
            self._store_anomalies_fallback(anomalies)
    
    def _store_anomalies_es(self, anomalies: List[Dict]):
        anomaly_index = f"{self.index}_anomalies"
        actions = []
        
        for anomaly in anomalies:
            doc = anomaly.copy()
            if isinstance(doc['timestamp'], datetime):
                doc['timestamp'] = doc['timestamp'].isoformat()
            doc['metrics'] = json.dumps(doc['metrics']) if 'metrics' in doc else '{}'
            
            actions.append({'index': {'_index': anomaly_index}})
            actions.append(doc)
        
        if actions:
            self.client.bulk(body=actions, refresh='wait_for')
    
    def _store_anomalies_fallback(self, anomalies: List[Dict]):
        for anomaly in anomalies:
            anomaly_copy = anomaly.copy()
            if isinstance(anomaly_copy['timestamp'], datetime):
                anomaly_copy['timestamp'] = anomaly_copy['timestamp'].isoformat()
            self._fallback_data['anomalies'].append(anomaly_copy)
    
    def query_metrics(self, start_time: datetime, end_time: datetime, 
                      metric_type: str = None) -> pd.DataFrame:
        if self.client:
            return self._query_metrics_es(start_time, end_time, metric_type)
        else:
            return self._query_metrics_fallback(start_time, end_time, metric_type)
    
    def _query_metrics_es(self, start_time: datetime, end_time: datetime, 
                          metric_type: str = None) -> pd.DataFrame:
        query = {
            'query': {
                'bool': {
                    'must': [
                        {'range': {'timestamp': {'gte': start_time.isoformat(), 'lte': end_time.isoformat()}}},
                        {'term': {'data_type': 'metric'}}
                    ]
                }
            },
            'size': 10000,
            'sort': [{'timestamp': 'asc'}]
        }
        
        if metric_type:
            query['query']['bool']['must'].append({'term': {'metric_type': metric_type}})
        
        response = self.client.search(index=self.index, body=query)
        
        data = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            data.append({
                'timestamp': source['timestamp'],
                'metric_type': source['metric_type'],
                'value': source['value']
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def _query_metrics_fallback(self, start_time: datetime, end_time: datetime, 
                                 metric_type: str = None) -> pd.DataFrame:
        data = []
        for metric in self._fallback_data['metrics']:
            ts = datetime.fromisoformat(metric['timestamp'].replace('Z', '+00:00')) if isinstance(metric['timestamp'], str) else metric['timestamp']
            if start_time <= ts <= end_time:
                if metric_type is None or metric['metric_type'] == metric_type:
                    data.append(metric)
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        return df
    
    def query_anomalies(self, start_time: datetime = None, end_time: datetime = None,
                        min_score: float = 0.0, limit: int = 100) -> List[Dict]:
        if self.client:
            return self._query_anomalies_es(start_time, end_time, min_score, limit)
        else:
            return self._query_anomalies_fallback(start_time, end_time, min_score, limit)
    
    def _query_anomalies_es(self, start_time: datetime = None, end_time: datetime = None,
                             min_score: float = 0.0, limit: int = 100) -> List[Dict]:
        anomaly_index = f"{self.index}_anomalies"
        
        must_conditions = []
        if start_time or end_time:
            range_query = {}
            if start_time:
                range_query['gte'] = start_time.isoformat()
            if end_time:
                range_query['lte'] = end_time.isoformat()
            must_conditions.append({'range': {'timestamp': range_query}})
        
        if min_score > 0:
            must_conditions.append({'range': {'total_score': {'gte': min_score}}})
        
        query = {
            'query': {'bool': {'must': must_conditions}} if must_conditions else {'match_all': {}},
            'size': limit,
            'sort': [{'total_score': 'desc', 'timestamp': 'desc'}]
        }
        
        response = self.client.search(index=anomaly_index, body=query)
        
        anomalies = []
        for hit in response['hits']['hits']:
            source = hit['_source']
            if 'metrics' in source:
                source['metrics'] = json.loads(source['metrics'])
            anomalies.append(source)
        
        return anomalies
    
    def _query_anomalies_fallback(self, start_time: datetime = None, end_time: datetime = None,
                                   min_score: float = 0.0, limit: int = 100) -> List[Dict]:
        anomalies = []
        for anomaly in self._fallback_data['anomalies']:
            ts = datetime.fromisoformat(anomaly['timestamp'].replace('Z', '+00:00')) if isinstance(anomaly['timestamp'], str) else anomaly['timestamp']
            
            matches = True
            if start_time and ts < start_time:
                matches = False
            if end_time and ts > end_time:
                matches = False
            if anomaly['total_score'] < min_score:
                matches = False
            
            if matches:
                anomalies.append(anomaly)
        
        anomalies.sort(key=lambda x: (-x['total_score'], x['timestamp']))
        return anomalies[:limit]
    
    def get_anomaly_summary(self, days: int = 7) -> Dict:
        if self.client:
            return self._get_anomaly_summary_es(days)
        else:
            return self._get_anomaly_summary_fallback(days)
    
    def _get_anomaly_summary_es(self, days: int = 7) -> Dict:
        anomaly_index = f"{self.index}_anomalies"
        
        end_time = datetime.now()
        start_time = end_time - pd.Timedelta(days=days)
        
        query = {
            'query': {
                'range': {
                    'timestamp': {'gte': start_time.isoformat(), 'lte': end_time.isoformat()}
                }
            },
            'size': 0,
            'aggs': {
                'total_anomalies': {'value_count': {'field': 'total_score'}},
                'joint_anomalies': {'filter': {'term': {'is_joint_anomaly': True}}},
                'avg_score': {'avg': {'field': 'total_score'}},
                'by_method': {'terms': {'field': 'detected_method'}}
            }
        }
        
        response = self.client.search(index=anomaly_index, body=query)
        
        return {
            'period_days': days,
            'total_anomalies': response['aggregations']['total_anomalies']['value'],
            'joint_anomalies': response['aggregations']['joint_anomalies']['doc_count'],
            'avg_score': response['aggregations']['avg_score']['value'] or 0,
            'by_method': [
                {'method': bucket['key'], 'count': bucket['doc_count']}
                for bucket in response['aggregations']['by_method']['buckets']
            ]
        }
    
    def _get_anomaly_summary_fallback(self, days: int = 7) -> Dict:
        end_time = datetime.now()
        start_time = end_time - pd.Timedelta(days=days)
        
        anomalies = [
            a for a in self._fallback_data['anomalies']
            if start_time <= datetime.fromisoformat(a['timestamp']) <= end_time
        ]
        
        by_method = {}
        for a in anomalies:
            for method in a.get('detected_by', []):
                by_method[method] = by_method.get(method, 0) + 1
        
        return {
            'period_days': days,
            'total_anomalies': len(anomalies),
            'joint_anomalies': len([a for a in anomalies if a.get('is_joint_anomaly', False)]),
            'avg_score': np.mean([a['total_score'] for a in anomalies]) if anomalies else 0,
            'by_method': [{'method': k, 'count': v} for k, v in by_method.items()]
        }
