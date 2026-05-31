from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Set, Tuple
import sqlglot
from sqlglot import exp, parse_one
import sqlparse


@dataclass
class ParsedSQL:
    original_sql: str
    ast: Optional[exp.Expression] = None
    sql_type: str = ""
    tables: List[str] = field(default_factory=list)
    columns: List[str] = field(default_factory=list)
    where_conditions: List[str] = field(default_factory=list)
    joins: List[Dict[str, Any]] = field(default_factory=list)
    subqueries: List[str] = field(default_factory=list)
    has_order_by: bool = False
    has_group_by: bool = False
    has_having: bool = False
    has_limit: bool = False
    has_distinct: bool = False
    has_union: bool = False
    is_valid: bool = False
    error: Optional[str] = None
    dialect: str = "mysql"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_sql": self.original_sql,
            "sql_type": self.sql_type,
            "tables": self.tables,
            "columns": self.columns,
            "where_conditions": self.where_conditions,
            "joins": self.joins,
            "subqueries": self.subqueries,
            "has_order_by": self.has_order_by,
            "has_group_by": self.has_group_by,
            "has_having": self.has_having,
            "has_limit": self.has_limit,
            "has_distinct": self.has_distinct,
            "has_union": self.has_union,
            "is_valid": self.is_valid,
            "error": self.error,
        }


class SQLParser:
    def __init__(self, dialect: str = "mysql"):
        self.dialect = dialect
        self._sqlglot_dialect = self._map_dialect(dialect)

    def _map_dialect(self, dialect: str) -> str:
        dialect_map = {
            "mysql": "mysql",
            "postgresql": "postgres",
            "pg": "postgres",
        }
        return dialect_map.get(dialect.lower(), "mysql")

    def parse(self, sql: str) -> ParsedSQL:
        result = ParsedSQL(original_sql=sql, dialect=self.dialect)

        try:
            formatted_sql = self._format_sql(sql)
            ast = parse_one(formatted_sql, dialect=self._sqlglot_dialect)
            result.ast = ast
            result.is_valid = True
            result.sql_type = self._get_sql_type(ast)
            result.tables = self._extract_tables(ast)
            result.columns = self._extract_columns(ast)
            result.where_conditions = self._extract_where_conditions(ast)
            result.joins = self._extract_joins(ast)
            result.subqueries = self._extract_subqueries(ast)
            result.has_order_by = self._has_order_by(ast)
            result.has_group_by = self._has_group_by(ast)
            result.has_having = self._has_having(ast)
            result.has_limit = self._has_limit(ast)
            result.has_distinct = self._has_distinct(ast)
            result.has_union = self._has_union(ast)
        except Exception as e:
            result.is_valid = False
            result.error = str(e)

        return result

    def _format_sql(self, sql: str) -> str:
        formatted = sqlparse.format(sql, reindent=True, keyword_case="upper")
        return formatted.strip()

    def _get_sql_type(self, ast: exp.Expression) -> str:
        if isinstance(ast, exp.Select):
            return "SELECT"
        elif isinstance(ast, exp.Insert):
            return "INSERT"
        elif isinstance(ast, exp.Update):
            return "UPDATE"
        elif isinstance(ast, exp.Delete):
            return "DELETE"
        elif isinstance(ast, exp.Create):
            return "CREATE"
        elif isinstance(ast, exp.Drop):
            return "DROP"
        else:
            return type(ast).__name__.upper()

    def _extract_tables(self, ast: exp.Expression) -> List[str]:
        tables = set()
        for table in ast.find_all(exp.Table):
            table_name = table.name
            if table.db:
                table_name = f"{table.db}.{table_name}"
            tables.add(table_name)
        return sorted(list(tables))

    def _extract_columns(self, ast: exp.Expression) -> List[str]:
        columns = set()
        for col in ast.find_all(exp.Column):
            col_name = col.name
            if col.table:
                col_name = f"{col.table}.{col_name}"
            columns.add(col_name)
        return sorted(list(columns))

    def _extract_where_conditions(self, ast: exp.Expression) -> List[str]:
        conditions = []
        where = ast.find(exp.Where)
        if where:
            for cond in where.find_all((exp.EQ, exp.NEQ, exp.GT, exp.LT, exp.GTE, exp.LTE,
                                         exp.Like, exp.In, exp.Between, exp.Is, exp.And, exp.Or)):
                if not isinstance(cond, (exp.And, exp.Or)):
                    conditions.append(cond.sql(dialect=self._sqlglot_dialect))
        return conditions

    def _extract_joins(self, ast: exp.Expression) -> List[Dict[str, Any]]:
        joins = []
        for join in ast.find_all(exp.Join):
            join_info = {
                "type": join.args.get("side", "").upper() if join.args.get("side") else "INNER",
                "table": join.this.name if hasattr(join.this, "name") else str(join.this),
                "on": join.args.get("on").sql(dialect=self._sqlglot_dialect) if join.args.get("on") else "",
            }
            joins.append(join_info)
        return joins

    def _extract_subqueries(self, ast: exp.Expression) -> List[str]:
        subqueries = []
        for subquery in ast.find_all(exp.Subquery):
            subqueries.append(subquery.sql(dialect=self._sqlglot_dialect))
        return subqueries

    def _has_order_by(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Order) is not None

    def _has_group_by(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Group) is not None

    def _has_having(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Having) is not None

    def _has_limit(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Limit) is not None

    def _has_distinct(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Distinct) is not None

    def _has_union(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Union) is not None

    def generate_sql(self, ast: exp.Expression, dialect: Optional[str] = None) -> str:
        target_dialect = self._map_dialect(dialect) if dialect else self._sqlglot_dialect
        return ast.sql(dialect=target_dialect, pretty=True)

    def validate_sql(self, sql: str) -> Tuple[bool, Optional[str]]:
        try:
            parse_one(sql, dialect=self._sqlglot_dialect)
            return True, None
        except Exception as e:
            return False, str(e)
