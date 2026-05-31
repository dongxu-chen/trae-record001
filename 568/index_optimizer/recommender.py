from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from sqlglot import exp, parse_one
import hashlib

from sql_analyzer import SQLParser, ParsedSQL
from execution_plan import PlanAnalysis
from db_connector import DatabaseConnector


@dataclass
class IndexRecommendation:
    table_name: str
    columns: List[str]
    index_type: str = "BTREE"
    index_name: str = ""
    estimated_benefit: float = 0.0
    confidence: float = 0.0
    reason: str = ""
    is_unique: bool = False
    cardinality: Optional[int] = None

    def generate_index_name(self, prefix: str = "idx_opt") -> str:
        cols_str = "_".join(self.columns)
        short_hash = hashlib.md5(cols_str.encode()).hexdigest()[:6]
        return f"{prefix}_{self.table_name}_{short_hash}"

    def to_sql(self, dialect: str = "mysql") -> str:
        if not self.index_name:
            self.index_name = self.generate_index_name()

        cols_str = ", ".join(self.columns)

        if dialect == "mysql" or dialect == "mariadb":
            unique_str = "UNIQUE " if self.is_unique else ""
            return f"CREATE {unique_str}INDEX {self.index_name} ON {self.table_name} ({cols_str}) USING {self.index_type};"
        elif dialect in ["postgresql", "postgres", "pg"]:
            unique_str = "UNIQUE " if self.is_unique else ""
            return f"CREATE {unique_str}INDEX {self.index_name} ON {self.table_name} USING {self.index_type.lower()} ({cols_str});"
        else:
            return f"CREATE INDEX {self.index_name} ON {self.table_name} ({cols_str});"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_name": self.table_name,
            "columns": self.columns,
            "index_type": self.index_type,
            "index_name": self.index_name,
            "estimated_benefit": self.estimated_benefit,
            "confidence": self.confidence,
            "reason": self.reason,
            "is_unique": self.is_unique,
            "cardinality": self.cardinality,
            "sql": self.to_sql(),
        }


@dataclass
class IndexRecommendationResult:
    recommendations: List[IndexRecommendation] = field(default_factory=list)
    existing_indexes: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    analyzed_queries: int = 0
    analyzed_tables: List[str] = field(default_factory=list)

    def sort_by_benefit(self, descending: bool = True) -> List[IndexRecommendation]:
        return sorted(self.recommendations, key=lambda x: x.estimated_benefit, reverse=descending)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "recommendations": [r.to_dict() for r in self.sort_by_benefit()],
            "existing_indexes": self.existing_indexes,
            "analyzed_queries": self.analyzed_queries,
            "analyzed_tables": self.analyzed_tables,
        }


class IndexRecommender:
    def __init__(self, db_connector: DatabaseConnector, dialect: str = "mysql"):
        self.db_connector = db_connector
        self.dialect = dialect
        self.sql_parser = SQLParser(dialect)
        self._cache: Dict[str, List[Dict[str, Any]]] = {}

    def recommend_for_query(
        self,
        sql: str,
        plan_analysis: Optional[PlanAnalysis] = None,
    ) -> IndexRecommendationResult:
        result = IndexRecommendationResult(analyzed_queries=1)

        try:
            parsed = self.sql_parser.parse(sql)
            if not parsed.is_valid:
                return result

            result.analyzed_tables = list(parsed.tables)

            for table in parsed.tables:
                existing = self._get_existing_indexes(table)
                result.existing_indexes[table] = existing

            recommendations = []

            where_cols = self._extract_where_columns(parsed)
            join_cols = self._extract_join_columns(parsed)
            order_cols = self._extract_order_columns(parsed)
            group_cols = self._extract_group_columns(parsed)

            for table in parsed.tables:
                table_where_cols = [c for c in where_cols if c["table"] == table or c["table"] is None]
                table_join_cols = [c for c in join_cols if c["table"] == table or c["table"] is None]
                table_order_cols = [c for c in order_cols if c["table"] == table or c["table"] is None]
                table_group_cols = [c for c in group_cols if c["table"] == table or c["table"] is None]

                if table_where_cols:
                    rec = self._create_where_index(table, table_where_cols, parsed)
                    if rec and not self._is_index_exists(table, rec.columns, result.existing_indexes):
                        recommendations.append(rec)

                if table_join_cols:
                    rec = self._create_join_index(table, table_join_cols)
                    if rec and not self._is_index_exists(table, rec.columns, result.existing_indexes):
                        recommendations.append(rec)

                if table_order_cols and not table_where_cols and not table_join_cols:
                    rec = self._create_order_index(table, table_order_cols)
                    if rec and not self._is_index_exists(table, rec.columns, result.existing_indexes):
                        recommendations.append(rec)

                if table_group_cols and not table_where_cols and not table_join_cols:
                    rec = self._create_group_index(table, table_group_cols)
                    if rec and not self._is_index_exists(table, rec.columns, result.existing_indexes):
                        recommendations.append(rec)

                composite_cols = self._analyze_composite_index(table, table_where_cols, table_join_cols)
                if composite_cols and len(composite_cols) > 1:
                    rec = self._create_composite_index(table, composite_cols, parsed)
                    if rec and not self._is_index_exists(table, rec.columns, result.existing_indexes):
                        recommendations.append(rec)

            if plan_analysis:
                recommendations = self._enhance_with_plan_analysis(recommendations, plan_analysis)

            result.recommendations = self._deduplicate_recommendations(recommendations)

        except Exception as e:
            pass

        return result

    def recommend_for_queries(
        self,
        sql_list: List[str],
    ) -> IndexRecommendationResult:
        all_recommendations: Dict[str, IndexRecommendation] = {}
        all_tables: set = set()
        existing_indexes: Dict[str, List[Dict[str, Any]]] = {}

        for sql in sql_list:
            result = self.recommend_for_query(sql)
            all_tables.update(result.analyzed_tables)
            existing_indexes.update(result.existing_indexes)

            for rec in result.recommendations:
                key = f"{rec.table_name}:{','.join(rec.columns)}"
                if key in all_recommendations:
                    all_recommendations[key].estimated_benefit += rec.estimated_benefit
                    all_recommendations[key].confidence = max(
                        all_recommendations[key].confidence, rec.confidence
                    )
                else:
                    all_recommendations[key] = rec

        final_result = IndexRecommendationResult(
            recommendations=list(all_recommendations.values()),
            existing_indexes=existing_indexes,
            analyzed_queries=len(sql_list),
            analyzed_tables=list(all_tables),
        )

        return final_result

    def _get_existing_indexes(self, table_name: str) -> List[Dict[str, Any]]:
        cache_key = f"idx_{table_name}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        indexes = []
        try:
            if self.dialect in ["mysql", "mariadb"]:
                sql = f"SHOW INDEX FROM {table_name}"
                result = self.db_connector.execute(sql)
                if result.success and result.rows:
                    current_index = None
                    for row in result.rows:
                        idx_name = row[2] if len(row) > 2 else None
                        col_name = row[4] if len(row) > 4 else None
                        non_unique = row[1] == 1 if len(row) > 1 else True

                        if idx_name != current_index:
                            if current_index:
                                indexes.append(index_data)
                            index_data = {
                                "name": idx_name,
                                "columns": [],
                                "unique": not non_unique,
                            }
                            current_index = idx_name
                        if col_name:
                            index_data["columns"].append(col_name)

                    if current_index:
                        indexes.append(index_data)

            elif self.dialect in ["postgresql", "postgres", "pg"]:
                sql = f"""
                SELECT
                    i.relname AS index_name,
                    a.attname AS column_name,
                    ix.indisunique AS is_unique
                FROM
                    pg_class t,
                    pg_class i,
                    pg_index ix,
                    pg_attribute a
                WHERE
                    t.oid = ix.indrelid
                    AND i.oid = ix.indexrelid
                    AND a.attrelid = t.oid
                    AND a.attnum = ANY(ix.indkey)
                    AND t.relname = '{table_name}'
                ORDER BY i.relname, array_position(ix.indkey, a.attnum)
                """
                result = self.db_connector.execute(sql)
                if result.success and result.rows:
                    current_index = None
                    for row in result.rows:
                        idx_name = row[0]
                        col_name = row[1]
                        is_unique = row[2]

                        if idx_name != current_index:
                            if current_index:
                                indexes.append(index_data)
                            index_data = {
                                "name": idx_name,
                                "columns": [],
                                "unique": is_unique,
                            }
                            current_index = idx_name
                        index_data["columns"].append(col_name)

                    if current_index:
                        indexes.append(index_data)

        except Exception:
            pass

        self._cache[cache_key] = indexes
        return indexes

    def _extract_where_columns(self, parsed: ParsedSQL) -> List[Dict[str, Any]]:
        columns = []
        if parsed.ast is None:
            return columns

        where = parsed.ast.find(exp.Where)
        if not where:
            return columns

        def extract_cols(expr):
            if isinstance(expr, exp.EQ):
                self._add_column_from_expr(expr.this, columns, "equality")
                self._add_column_from_expr(expr.expression, columns, "equality")
            elif isinstance(expr, (exp.GT, exp.GTE, exp.LT, exp.LTE)):
                self._add_column_from_expr(expr.this, columns, "range")
            elif isinstance(expr, exp.In):
                self._add_column_from_expr(expr.this, columns, "in_list")
            elif isinstance(expr, exp.Like):
                self._add_column_from_expr(expr.this, columns, "like")
            elif isinstance(expr, (exp.And, exp.Or)):
                extract_cols(expr.this)
                extract_cols(expr.expression)

        extract_cols(where.this)
        return columns

    def _add_column_from_expr(self, expr, columns: List, selectivity: str):
        if isinstance(expr, exp.Column):
            table = getattr(expr, "table", None)
            col_name = expr.name if hasattr(expr, "name") else str(expr.this)
            columns.append({
                "table": table,
                "column": col_name,
                "selectivity": selectivity,
            })

    def _extract_join_columns(self, parsed: ParsedSQL) -> List[Dict[str, Any]]:
        columns = []
        if parsed.joins:
            for join in parsed.joins:
                if "on" in join:
                    try:
                        ast = parse_one(f"SELECT 1 WHERE {join['on']}")
                        where = ast.find(exp.Where)
                        if where:
                            self._extract_join_conditions(where.this, columns)
                    except Exception:
                        pass
        return columns

    def _extract_join_conditions(self, expr, columns: List):
        if isinstance(expr, exp.EQ):
            left_is_col = isinstance(expr.this, exp.Column)
            right_is_col = isinstance(expr.expression, exp.Column)
            if left_is_col and right_is_col:
                columns.append({
                    "table": getattr(expr.this, "table", None),
                    "column": expr.this.name if hasattr(expr.this, "name") else str(expr.this.this),
                    "selectivity": "join",
                })
                columns.append({
                    "table": getattr(expr.expression, "table", None),
                    "column": expr.expression.name if hasattr(expr.expression, "name") else str(expr.expression.this),
                    "selectivity": "join",
                })
        elif isinstance(expr, exp.And):
            self._extract_join_conditions(expr.this, columns)
            self._extract_join_conditions(expr.expression, columns)

    def _extract_order_columns(self, parsed: ParsedSQL) -> List[Dict[str, Any]]:
        columns = []
        if parsed.ast is None:
            return columns

        order = parsed.ast.find(exp.Order)
        if order:
            for ordered in order.expressions:
                if isinstance(ordered.this, exp.Column):
                    columns.append({
                        "table": getattr(ordered.this, "table", None),
                        "column": ordered.this.name if hasattr(ordered.this, "name") else str(ordered.this.this),
                        "selectivity": "order",
                    })
        return columns

    def _extract_group_columns(self, parsed: ParsedSQL) -> List[Dict[str, Any]]:
        columns = []
        if parsed.ast is None:
            return columns

        group = parsed.ast.find(exp.Group)
        if group:
            for col in group.expressions:
                if isinstance(col, exp.Column):
                    columns.append({
                        "table": getattr(col, "table", None),
                        "column": col.name if hasattr(col, "name") else str(col.this),
                        "selectivity": "group",
                    })
        return columns

    def _create_where_index(
        self, table: str, cols: List[Dict[str, Any]], parsed: ParsedSQL
    ) -> Optional[IndexRecommendation]:
        if not cols:
            return None

        equality_cols = [c["column"] for c in cols if c["selectivity"] == "equality"]
        range_cols = [c["column"] for c in cols if c["selectivity"] == "range"]
        other_cols = [c["column"] for c in cols if c["selectivity"] not in ["equality", "range"]]

        ordered_cols = equality_cols + range_cols + other_cols
        if not ordered_cols:
            return None

        benefit = len(equality_cols) * 20 + len(range_cols) * 10 + len(other_cols) * 5

        return IndexRecommendation(
            table_name=table,
            columns=ordered_cols,
            index_type="BTREE",
            estimated_benefit=benefit,
            confidence=min(0.95, 0.5 + len(equality_cols) * 0.1),
            reason=f"WHERE clause optimization: {len(ordered_cols)} columns ({', '.join(ordered_cols[:3])}{'...' if len(ordered_cols) > 3 else ''})",
        )

    def _create_join_index(self, table: str, cols: List[Dict[str, Any]]) -> Optional[IndexRecommendation]:
        if not cols:
            return None

        col_names = list(dict.fromkeys([c["column"] for c in cols]))
        if not col_names:
            return None

        return IndexRecommendation(
            table_name=table,
            columns=col_names,
            index_type="BTREE",
            estimated_benefit=len(col_names) * 15,
            confidence=0.9,
            reason=f"JOIN optimization: {', '.join(col_names)}",
        )

    def _create_order_index(self, table: str, cols: List[Dict[str, Any]]) -> Optional[IndexRecommendation]:
        if not cols:
            return None

        col_names = [c["column"] for c in cols]
        return IndexRecommendation(
            table_name=table,
            columns=col_names,
            index_type="BTREE",
            estimated_benefit=len(col_names) * 8,
            confidence=0.6,
            reason=f"ORDER BY optimization: {', '.join(col_names)}",
        )

    def _create_group_index(self, table: str, cols: List[Dict[str, Any]]) -> Optional[IndexRecommendation]:
        if not cols:
            return None

        col_names = [c["column"] for c in cols]
        return IndexRecommendation(
            table_name=table,
            columns=col_names,
            index_type="BTREE",
            estimated_benefit=len(col_names) * 10,
            confidence=0.7,
            reason=f"GROUP BY optimization: {', '.join(col_names)}",
        )

    def _create_composite_index(
        self, table: str, cols: List[str], parsed: ParsedSQL
    ) -> Optional[IndexRecommendation]:
        if len(cols) < 2:
            return None

        return IndexRecommendation(
            table_name=table,
            columns=cols[:5],
            index_type="BTREE",
            estimated_benefit=len(cols) * 12,
            confidence=0.75,
            reason=f"Composite index for query optimization: {', '.join(cols[:5])}",
        )

    def _analyze_composite_index(
        self, table: str, where_cols: List[Dict[str, Any]], join_cols: List[Dict[str, Any]]
    ) -> List[str]:
        all_cols = where_cols + join_cols
        if not all_cols:
            return []

        col_names = list(dict.fromkeys([c["column"] for c in all_cols]))
        return col_names[:5]

    def _is_index_exists(
        self, table: str, columns: List[str], existing_indexes: Dict[str, List[Dict[str, Any]]]
    ) -> bool:
        if table not in existing_indexes:
            return False

        for idx in existing_indexes[table]:
            idx_cols = idx.get("columns", [])
            if len(idx_cols) >= len(columns):
                if idx_cols[:len(columns)] == columns:
                    return True
        return False

    def _enhance_with_plan_analysis(
        self, recommendations: List[IndexRecommendation], plan_analysis: PlanAnalysis
    ) -> List[IndexRecommendation]:
        for rec in recommendations:
            for problem in plan_analysis.potential_problems:
                if "全表扫描" in problem and rec.table_name in problem:
                    rec.estimated_benefit *= 2.0
                    rec.confidence = min(1.0, rec.confidence + 0.2)
                    rec.reason += " (based on full table scan detection)"
                elif "filesort" in problem and rec.table_name in problem:
                    rec.estimated_benefit *= 1.5
                    rec.reason += " (based on filesort detection)"

        return recommendations

    def _deduplicate_recommendations(
        self, recommendations: List[IndexRecommendation]
    ) -> List[IndexRecommendation]:
        seen = set()
        unique = []
        for rec in recommendations:
            key = f"{rec.table_name}:{','.join(sorted(rec.columns))}"
            if key not in seen:
                seen.add(key)
                unique.append(rec)
        return unique
