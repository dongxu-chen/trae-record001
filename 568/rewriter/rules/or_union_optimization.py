from typing import List, Optional, Any
from sqlglot import exp, parse_one
from .base_rule import BaseRewriteRule, RuleApplicationResult


class OrToUnionRule(BaseRewriteRule):
    """
    将OR条件优化为UNION/UNION ALL，避免全表扫描。
    
    优化场景：
    - WHERE col1 = val1 OR col2 = val2 -> 两个索引扫描 + UNION
    - WHERE (col1, col2) IN ((a,b), (c,d)) -> 拆分为多个条件 + UNION
    
    注意：需要确保两个分支互斥或使用UNION去重
    """

    @property
    def rule_name(self) -> str:
        return "OR to UNION Optimization"

    @property
    def rule_description(self) -> str:
        return "Convert OR conditions in WHERE clause to UNION/UNION ALL to leverage multiple index scans"

    def apply(self, ast: exp.Expression, analysis: Any = None) -> RuleApplicationResult:
        if not isinstance(ast, exp.Select):
            return RuleApplicationResult(applied=False)

        self.applied_changes = []
        new_ast = self._optimize_or_conditions(ast)

        if new_ast and new_ast.sql() != ast.sql():
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=self.applied_changes,
                description="Converted OR conditions to UNION for better index usage"
            )

        return RuleApplicationResult(applied=False)

    def _optimize_or_conditions(self, ast: exp.Expression) -> Optional[exp.Expression]:
        where = ast.find(exp.Where)
        if not where:
            return None

        or_conditions = self._extract_top_level_or_conditions(where.this)
        if len(or_conditions) < 2:
            return None

        new_ast = ast.copy()
        new_where = new_ast.find(exp.Where)

        if new_where:
            new_where.pop()

        union_query = self._build_union_query(new_ast, or_conditions)

        self.applied_changes.append(
            f"Converted {len(or_conditions)} OR conditions to UNION query"
        )

        return union_query

    def _extract_top_level_or_conditions(self, expr: exp.Expression) -> List[exp.Expression]:
        conditions = []
        self._traverse_or_tree(expr, conditions)
        return conditions

    def _traverse_or_tree(self, expr: exp.Expression, conditions: List[exp.Expression]):
        if isinstance(expr, exp.Or):
            self._traverse_or_tree(expr.this, conditions)
            self._traverse_or_tree(expr.expression, conditions)
        else:
            conditions.append(expr.copy())

    def _build_union_query(self, base_select: exp.Select, conditions: List[exp.Expression]) -> exp.Select:
        select_queries = []

        for i, cond in enumerate(conditions):
            query = base_select.copy()
            where_clause = exp.Where(this=cond)
            query.set("where", where_clause)
            select_queries.append(query)

        result = select_queries[0]
        for query in select_queries[1:]:
            union = exp.Union(
                this=result,
                expression=query,
                distinct=True
            )
            result = exp.Subquery(this=union)
            result = exp.Select(expressions=[exp.Star()], from_=exp.From(this=result))

        return self._flatten_union(select_queries)

    def _flatten_union(self, queries: List[exp.Select]) -> exp.Expression:
        if len(queries) == 1:
            return queries[0]

        result = queries[0]
        for query in queries[1:]:
            result = exp.Union(
                this=result,
                expression=query,
                distinct=True
            )

        return result
