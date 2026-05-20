import re
import hashlib

class SQLFingerprint:
    def __init__(self):
        self.patterns = [
            (re.compile(r"([\"'])(?:(?=(\\?))\2.)*?\1", re.DOTALL), '?'),
            (re.compile(r'\b\d+\.\d+\b'), '?'),
            (re.compile(r'\b\d+\b'), '?'),
            (re.compile(r'\b0x[0-9a-fA-F]+\b'), '?'),
            (re.compile(r'\btrue\b|\bfalse\b', re.IGNORECASE), '?'),
            (re.compile(r'\bnull\b', re.IGNORECASE), '?'),
            (re.compile(r'\s+'), ' '),
            (re.compile(r'\(\s*(\?(?:\s*,\s*\?)*)\s*\)'), '(?)'),
            (re.compile(r'in\s*\([^)]+\)', re.IGNORECASE), 'IN (?)'),
            (re.compile(r'values\s*\([^)]+\)', re.IGNORECASE), 'VALUES (?)'),
        ]
    
    def generate_fingerprint(self, sql):
        if not sql:
            return None
        
        sql = sql.strip()
        
        for pattern, replacement in self.patterns:
            sql = pattern.sub(replacement, sql)
        
        keywords = ['SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'ORDER', 'BY', 
                   'GROUP', 'HAVING', 'LIMIT', 'OFFSET', 'JOIN', 'INNER', 
                   'LEFT', 'RIGHT', 'OUTER', 'ON', 'AS', 'IN', 'NOT', 
                   'LIKE', 'BETWEEN', 'IS', 'NULL', 'UPDATE', 'SET', 
                   'DELETE', 'INSERT', 'INTO', 'VALUES', 'CREATE', 'DROP',
                   'ALTER', 'TABLE', 'INDEX', 'UNION', 'ALL', 'DISTINCT']
        
        for kw in keywords:
            sql = re.sub(r'\b' + re.escape(kw) + r'\b', kw, sql, flags=re.IGNORECASE)
        
        return sql.strip()
    
    def generate_hash(self, sql):
        fingerprint = self.generate_fingerprint(sql)
        if not fingerprint:
            return None
        
        return hashlib.md5(fingerprint.encode('utf-8')).hexdigest()
    
    def extract_tables(self, sql):
        tables = set()
        
        from_patterns = [
            r'FROM\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?',
            r'JOIN\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?',
            r'UPDATE\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?',
            r'INTO\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?',
            r'TABLE\s+`?([a-zA-Z_][a-zA-Z0-9_]*)`?',
        ]
        
        for pattern in from_patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            for match in matches:
                if match.upper() not in ['SELECT', 'WHERE', 'AND', 'OR', 'FROM', 'JOIN']:
                    tables.add(match)
        
        return sorted(list(tables))
    
    def classify_query_type(self, sql):
        sql_upper = sql.strip().upper()
        if sql_upper.startswith('SELECT'):
            return 'SELECT'
        elif sql_upper.startswith('INSERT'):
            return 'INSERT'
        elif sql_upper.startswith('UPDATE'):
            return 'UPDATE'
        elif sql_upper.startswith('DELETE'):
            return 'DELETE'
        elif sql_upper.startswith('REPLACE'):
            return 'REPLACE'
        elif sql_upper.startswith('CREATE'):
            return 'CREATE'
        elif sql_upper.startswith('ALTER'):
            return 'ALTER'
        elif sql_upper.startswith('DROP'):
            return 'DROP'
        else:
            return 'OTHER'
    
    def analyze_queries(self, queries):
        results = []
        fingerprint_counts = {}
        
        for sql in queries:
            fingerprint = self.generate_fingerprint(sql)
            sql_hash = self.generate_hash(sql)
            tables = self.extract_tables(sql)
            query_type = self.classify_query_type(sql)
            
            if fingerprint:
                fingerprint_counts[fingerprint] = fingerprint_counts.get(fingerprint, 0) + 1
            
            results.append({
                'original_sql': sql,
                'fingerprint': fingerprint,
                'hash': sql_hash,
                'tables': tables,
                'query_type': query_type
            })
        
        return results, fingerprint_counts
    
    def normalize_spaces(self, sql):
        sql = re.sub(r'\s+', ' ', sql)
        sql = re.sub(r'\s*([(),=<>+\-*/])\s*', r'\1', sql)
        return sql.strip()
