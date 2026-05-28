import re
import hashlib
from collections import defaultdict
from difflib import SequenceMatcher
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN
import numpy as np


class SQLFingerprintClusterer:
    def __init__(self):
        self._stop_words = {'select', 'from', 'where', 'and', 'or', 'join', 'on', 'group', 'by', 'order', 'having', 'limit', 'offset', 'inner', 'left', 'right', 'outer', 'as', 'in', 'not', 'like', 'between', 'is', 'null', 'asc', 'desc', 'distinct', 'count', 'sum', 'avg', 'max', 'min', 'union', 'all'}
        self._vectorizer = TfidfVectorizer(
            token_pattern=r'\b[a-zA-Z_]+\b',
            stop_words=self._stop_words
        )

    def normalize_sql(self, sql):
        if not sql:
            return ''
        sql = sql.strip()
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        sql = re.sub(r'\s+', ' ', sql)
        return sql.strip()

    def get_fingerprint_v1(self, sql):
        if not sql:
            return ''
        fp = self.normalize_sql(sql)
        fp = fp.lower()
        fp = re.sub(r'\b\d+\b', '?', fp)
        fp = re.sub(r"'[^']*'", "?", fp)
        fp = re.sub(r'"[^"]*"', "?", fp)
        fp = re.sub(r'\b0x[0-9a-f]+\b', '?', fp)
        fp = re.sub(r'\btrue\b', '?', fp)
        fp = re.sub(r'\bfalse\b', '?', fp)
        fp = re.sub(r'\bnull\b', '?', fp)
        fp = re.sub(r'\s+', ' ', fp)
        fp = re.sub(r'\b(?:in|values)\s*\([^)]+\)', r'\g<1>(?)', fp, flags=re.IGNORECASE)
        return fp.strip()

    def get_fingerprint_v2(self, sql):
        if not sql:
            return ''
        fp = self.get_fingerprint_v1(sql)
        fp = re.sub(r'\s*=\s*\?', ' = ?', fp)
        fp = re.sub(r'\s*<[=>]?\s*\?', ' op ?', fp)
        fp = re.sub(r'\s*>\s*=?\s*\?', ' op ?', fp)
        return fp

    def get_structural_fingerprint(self, sql):
        if not sql:
            return ''
        normalized = self.normalize_sql(sql).lower()
        tokens = re.findall(r'\b[a-z_]+\b', normalized)
        structural_tokens = [t for t in tokens if t in {'select', 'from', 'where', 'join', 'group', 'order', 'having', 'limit', 'union', 'insert', 'update', 'delete', 'inner', 'left', 'right', 'distinct'}]
        return ' '.join(structural_tokens)

    def hash_fingerprint(self, fingerprint):
        return hashlib.md5(fingerprint.encode('utf-8')).hexdigest()

    def calculate_similarity(self, sql1, sql2):
        fp1 = self.get_fingerprint_v1(sql1)
        fp2 = self.get_fingerprint_v1(sql2)
        return SequenceMatcher(None, fp1, fp2).ratio()

    def cluster_queries(self, queries, similarity_threshold=0.85):
        if not queries:
            return []
        sql_texts = []
        for q in queries:
            sql = q.get('sql_text', '') or q.get('argument', '') or q.get('query', '')
            sql_texts.append(sql)
        if len(sql_texts) <= 1:
            return [{'cluster_id': 0, 'queries': queries, 'count': len(queries)}]
        fingerprints = [self.get_fingerprint_v1(sql) for sql in sql_texts]
        clusters = defaultdict(list)
        for i, fp in enumerate(fingerprints):
            clusters[fp].append(i)
        result = []
        cluster_id = 0
        for fp, indices in clusters.items():
            cluster_queries = [queries[i] for i in indices]
            sample_sql = sql_texts[indices[0]]
            total_time = 0
            max_time = 0
            min_time = float('inf')
            for q in cluster_queries:
                qt = q.get('query_time', 0)
                if hasattr(qt, 'total_seconds'):
                    qt = qt.total_seconds()
                elif isinstance(qt, str):
                    try:
                        parts = qt.split(':')
                        if len(parts) == 3:
                            qt = int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
                        else:
                            qt = float(qt)
                    except:
                        qt = 0
                total_time += qt
                max_time = max(max_time, qt)
                min_time = min(min_time, qt)
            result.append({
                'cluster_id': cluster_id,
                'fingerprint': fp,
                'fingerprint_hash': self.hash_fingerprint(fp),
                'count': len(cluster_queries),
                'sample_query': sample_sql,
                'total_time': total_time,
                'avg_time': total_time / len(cluster_queries) if cluster_queries else 0,
                'max_time': max_time,
                'min_time': min_time if min_time != float('inf') else 0,
                'queries': cluster_queries
            })
            cluster_id += 1
        result.sort(key=lambda x: x['total_time'], reverse=True)
        return result

    def advanced_cluster_queries(self, queries, eps=0.3, min_samples=2):
        if not queries:
            return []
        sql_texts = []
        for q in queries:
            sql = q.get('sql_text', '') or q.get('argument', '') or q.get('query', '')
            sql_texts.append(sql)
        if len(sql_texts) < min_samples:
            return self.cluster_queries(queries)
        try:
            fingerprints = [self.get_fingerprint_v1(sql) for sql in sql_texts]
            tfidf_matrix = self._vectorizer.fit_transform(fingerprints)
            clustering = DBSCAN(eps=eps, min_samples=min_samples, metric='cosine')
            labels = clustering.fit_predict(tfidf_matrix)
            clusters = defaultdict(list)
            for i, label in enumerate(labels):
                clusters[label].append(i)
            result = []
            for label, indices in clusters.items():
                cluster_queries = [queries[i] for i in indices]
                sample_sql = sql_texts[indices[0]]
                total_time = 0
                for q in cluster_queries:
                    qt = q.get('query_time', 0)
                    if hasattr(qt, 'total_seconds'):
                        qt = qt.total_seconds()
                    total_time += qt
                result.append({
                    'cluster_id': label if label != -1 else 'noise',
                    'count': len(cluster_queries),
                    'sample_query': sample_sql,
                    'total_time': total_time,
                    'avg_time': total_time / len(cluster_queries) if cluster_queries else 0,
                    'is_noise': label == -1,
                    'queries': cluster_queries
                })
            result.sort(key=lambda x: x['total_time'], reverse=True)
            return result
        except Exception as e:
            return self.cluster_queries(queries)

    def find_similar_queries(self, target_sql, queries, threshold=0.7):
        results = []
        for q in queries:
            sql = q.get('sql_text', '') or q.get('argument', '') or q.get('query', '')
            similarity = self.calculate_similarity(target_sql, sql)
            if similarity >= threshold:
                results.append({
                    'query': q,
                    'similarity': similarity,
                    'sql': sql
                })
        results.sort(key=lambda x: x['similarity'], reverse=True)
        return results

    def extract_patterns(self, queries):
        if not queries:
            return []
        fingerprints = defaultdict(int)
        tables = defaultdict(int)
        operations = defaultdict(int)
        for q in queries:
            sql = q.get('sql_text', '') or q.get('argument', '') or q.get('query', '')
            if sql:
                fp = self.get_fingerprint_v1(sql)
                fingerprints[fp] += 1
                table_matches = re.findall(r'FROM\s+(\w+)', sql, re.IGNORECASE)
                for t in table_matches:
                    tables[t] += 1
                op = sql.strip().split()[0].upper() if sql.strip() else 'UNKNOWN'
                operations[op] += 1
        return {
            'fingerprints': dict(sorted(fingerprints.items(), key=lambda x: x[1], reverse=True)[:20]),
            'tables': dict(sorted(tables.items(), key=lambda x: x[1], reverse=True)[:20]),
            'operations': dict(operations)
        }
