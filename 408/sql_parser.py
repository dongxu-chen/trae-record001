import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Comparison, Parenthesis, Function, Operation
from sqlparse.tokens import Keyword, DML, DDL, Whitespace, Name, String, Number, Operator, Punctuation
import re
from collections import defaultdict


class SQLParser:
    def __init__(self):
        self.tables = []
        self.columns = []
        self.where_conditions = []
        self.join_conditions = []
        self.group_by = []
        self.order_by = []
        self.having = []
        self.limit = None
        self.aggregations = []
        self.subqueries = []
        self.query_type = None
        self.original_sql = None

    def parse(self, sql):
        self.original_sql = sql
        parsed = sqlparse.parse(sql)[0]
        self.query_type = parsed.get_type()
        self._extract_tables(parsed)
        self._extract_where(parsed)
        self._extract_group_by(parsed)
        self._extract_order_by(parsed)
        self._extract_limit(parsed)
        self._extract_having(parsed)
        self._extract_aggregations(parsed)
        return self.get_analysis()

    def _extract_tables(self, parsed):
        table_keywords = ['FROM', 'JOIN', 'UPDATE', 'INTO']
        tables = set()
        for stmt in parsed.tokens:
            if isinstance(stmt, IdentifierList):
                for identifier in stmt.get_identifiers():
                    table_name = self._clean_identifier(str(identifier))
                    if table_name:
                        tables.add(table_name)
            elif isinstance(stmt, Identifier):
                table_name = self._clean_identifier(str(stmt))
                if table_name:
                    tables.add(table_name)
            elif stmt.ttype is Keyword:
                continue

        from_seen = False
        for token in parsed.flatten():
            if token.ttype is Keyword and token.value.upper() in ['FROM', 'JOIN', 'UPDATE', 'INTO']:
                from_seen = True
                continue
            if from_seen and token.ttype is Name:
                table_name = token.value.strip('`').strip('"')
                if table_name and not table_name.upper() in ['WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT', 'ON', 'AS', 'AND', 'OR', 'NOT', 'IN', 'LIKE', 'BETWEEN', 'IS', 'NULL', 'LEFT', 'RIGHT', 'INNER', 'OUTER', 'FULL', 'CROSS', 'NATURAL', 'STRAIGHT_JOIN', 'INNER', 'JOIN', 'UNION', 'SELECT', 'INSERT', 'UPDATE', 'DELETE']:
                    tables.add(table_name)
                    from_seen = False

        self.tables = list(tables)

    def _clean_identifier(self, identifier):
        identifier = identifier.strip()
        if identifier.upper().startswith(('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE', 'ALTER', 'DROP')):
            return None
        if ' ' in identifier:
            parts = identifier.split()
            if len(parts) >= 2 and parts[1].upper() == 'AS':
                return parts[0].strip('`').strip('"')
            elif len(parts) == 2:
                return parts[0].strip('`').strip('"')
        return identifier.strip('`').strip('"')

    def _extract_where(self, parsed):
        conditions = []
        where_token = None
        for token in parsed.tokens:
            if isinstance(token, Where):
                where_token = token
                break

        if where_token:
            self._parse_conditions(where_token, conditions)
        self.where_conditions = conditions

    def _parse_conditions(self, token, conditions, depth=0):
        if depth > 10:
            return
        for child in token.tokens:
            if child.ttype in (Keyword,) and child.value.upper() in ('AND', 'OR', 'NOT'):
                continue
            if isinstance(child, Comparison):
                left = str(child.left).strip()
                op = str(child.token_next(0)).strip() if child.token_next(0) else ''
                right = str(child.right).strip() if child.right else ''
                conditions.append({
                    'column': left,
                    'operator': op,
                    'value': right,
                    'full': str(child).strip()
                })
            elif hasattr(child, 'tokens'):
                self._parse_conditions(child, conditions, depth + 1)

    def _extract_group_by(self, parsed):
        groups = []
        for token in parsed.tokens:
            if token.ttype is Keyword and token.value.upper() == 'GROUP':
                continue
            if hasattr(token, 'tokens'):
                for t in token.flatten():
                    if t.ttype is Name:
                        groups.append(t.value.strip('`'))
        self.group_by = list(set(groups))

    def _extract_order_by(self, parsed):
        orders = []
        for token in parsed.tokens:
            if token.ttype is Keyword and token.value.upper() == 'ORDER':
                for t in token.flatten():
                    if t.ttype is Name:
                        orders.append(t.value.strip('`'))
        self.order_by = orders

    def _extract_limit(self, parsed):
        for token in parsed.flatten():
            if token.ttype is Keyword and token.value.upper() == 'LIMIT':
                idx = list(parsed.flatten()).index(token)
                tokens = list(parsed.flatten())
                if idx + 1 < len(tokens):
                    try:
                        self.limit = int(tokens[idx + 1].value)
                    except (ValueError, AttributeError):
                        pass

    def _extract_having(self, parsed):
        conditions = []
        for token in parsed.tokens:
            if hasattr(token, 'tokens'):
                for t in token.flatten():
                    if t.ttype is Keyword and t.value.upper() == 'HAVING':
                        self._parse_conditions(token, conditions)
        self.having = conditions

    def _extract_aggregations(self, parsed):
        agg_funcs = ['COUNT', 'SUM', 'AVG', 'MIN', 'MAX', 'GROUP_CONCAT', 'STD', 'VARIANCE']
        aggregations = []
        for token in parsed.flatten():
            if isinstance(token, Function):
                func_name = token.get_name().upper() if hasattr(token, 'get_name') else ''
                if func_name in agg_funcs:
                    aggregations.append({
                        'function': func_name,
                        'expression': str(token).strip()
                    })
        self.aggregations = aggregations

    def get_analysis(self):
        return {
            'query_type': self.query_type,
            'tables': self.tables,
            'columns': self._extract_columns_from_select(),
            'where_conditions': self.where_conditions,
            'group_by': self.group_by,
            'order_by': self.order_by,
            'having': self.having,
            'limit': self.limit,
            'aggregations': self.aggregations,
            'has_subquery': self._check_subquery(),
            'has_union': self._check_union(),
            'uses_select_star': self._check_select_star(),
            'has_distinct': self._check_distinct(),
            'has_implicit_cast': self._check_implicit_cast(),
            'has_like_prefix': self._check_like_prefix(),
            'has_or_in_where': self._check_or_in_where(),
            'has_null_comparison': self._check_null_comparison()
        }

    def _extract_columns_from_select(self):
        columns = []
        if not self.original_sql:
            return columns
        sql_upper = self.original_sql.upper()
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', self.original_sql, re.IGNORECASE | re.DOTALL)
        if select_match:
            cols_str = select_match.group(1).strip()
            if cols_str == '*':
                return ['*']
            for col in re.split(r',\s*', cols_str):
                col = col.strip()
                if col:
                    columns.append(col)
        return columns

    def _check_subquery(self):
        if not self.original_sql:
            return False
        return bool(re.search(r'\(SELECT', self.original_sql, re.IGNORECASE))

    def _check_union(self):
        if not self.original_sql:
            return False
        return bool(re.search(r'\bUNION\b', self.original_sql, re.IGNORECASE))

    def _check_select_star(self):
        if not self.original_sql:
            return False
        return bool(re.search(r'SELECT\s+\*', self.original_sql, re.IGNORECASE))

    def _check_distinct(self):
        if not self.original_sql:
            return False
        return bool(re.search(r'SELECT\s+DISTINCT', self.original_sql, re.IGNORECASE))

    def _check_implicit_cast(self):
        if not self.original_sql:
            return False
        conditions = self.where_conditions
        for cond in conditions:
            val = cond.get('value', '')
            col = cond.get('column', '')
            if val and col:
                if re.match(r"^'?\d+'?$", val) and re.search(r'char|varchar|text', col, re.IGNORECASE):
                    return True
                if re.match(r"^'[^']*'$", val) and re.search(r'int|decimal|float|double|numeric', col, re.IGNORECASE):
                    return True
        return False

    def _check_like_prefix(self):
        if not self.original_sql:
            return False
        for cond in self.where_conditions:
            if cond.get('operator', '').upper() == 'LIKE':
                val = cond.get('value', '')
                if val.startswith("'%") or val.startswith('"%') or val.startswith('%'):
                    return True
        return False

    def _check_or_in_where(self):
        if not self.original_sql:
            return False
        return bool(re.search(r'\bOR\b', self.original_sql, re.IGNORECASE))

    def _check_null_comparison(self):
        if not self.original_sql:
            return False
        return bool(re.search(r'=\s*NULL|!=\s*NULL|<>\s*NULL', self.original_sql, re.IGNORECASE))


def parse_sql(sql):
    parser = SQLParser()
    return parser.parse(sql)


def extract_table_aliases(sql):
    aliases = {}
    sql_upper = sql.upper()
    from_match = re.search(r'FROM\s+(.*?)(?:WHERE|GROUP|ORDER|LIMIT|HAVING|$)', sql, re.IGNORECASE | re.DOTALL)
    if from_match:
        from_clause = from_match.group(1)
        for match in re.finditer(r'(\w+)\s+(?:AS\s+)?(\w+)', from_clause, re.IGNORECASE):
            table = match.group(1)
            alias = match.group(2)
            if table.upper() not in ['ON', 'AND', 'OR', 'WHERE', 'INNER', 'LEFT', 'RIGHT', 'JOIN', 'OUTER', 'CROSS']:
                aliases[alias] = table
    return aliases


def normalize_sql(sql):
    return sqlparse.format(sql, reindent=True, keyword_case='upper')


def format_sql(sql):
    return sqlparse.format(sql, reindent=True, keyword_case='upper')


def split_statements(sql):
    return sqlparse.split(sql)


def get_statement_count(sql):
    return len(sqlparse.split(sql))


def validate_syntax(sql):
    try:
        parsed = sqlparse.parse(sql)
        if not parsed:
            return False, "SQL语句为空"
        return True, "语法有效"
    except Exception as e:
        return False, str(e)