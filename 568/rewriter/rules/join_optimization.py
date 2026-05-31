from typing import List, Optional, Any
from sqlglot import exp
from .base_rule import BaseRewriteRule, RuleApplicationResult


class JoinOptimizationRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Join Optimization"

    @property
    def rule_description(self) -> str:
        return "Optimize JOIN operations: reorder tables, add missing join conditions, convert implicit joins"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        implicit_converted = self._convert_implicit_joins(new_ast)
        if implicit_converted:
            changes.append("Converted implicit comma joins to explicit JOINs")
            new_ast = implicit_converted

        if analysis and hasattr(analysis, "join_issues") and analysis.join_issues:
            fixed = self._fix_join_issues(new_ast, analysis)
            if fixed:
                changes.append("Fixed join order based on analysis")
                new_ast = fixed

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _convert_implicit_joins(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        from_clause = ast.find(exp.From)
        if not from_clause:
            return None

        from_expressions = list(from_clause.find_all(exp.Expression, depth=1))
        tables_in_from = []

        for expr in from_expressions:
            if isinstance(expr, exp.Table):
                tables_in_from.append(expr)
            elif isinstance(expr, exp.Alias) and isinstance(expr.this, exp.Table):
                tables_in_from.append(expr.this)

        if len(tables_in_from) < 2:
            return None

        where = ast.find(exp.Where)
        if not where:
            return None

        join_conditions = []
        for cond in where.find_all(exp.EQ):
            left_cols = list(cond.this.find_all(exp.Column))
            right_cols = list(cond.expression.find_all(exp.Column))

            if left_cols and right_cols:
                left_table = left_cols[0].table if left_cols[0].table else ""
                right_table = right_cols[0].table if right_cols[0].table else ""

                if left_table and right_table and left_table != right_table:
                    join_conditions.append((cond, left_table, right_table))

        if not join_conditions:
            return None

        try:
            new_ast = ast.copy()
            new_from = new_ast.find(exp.From)

            first_table = tables_in_from[0]
            remaining_tables = tables_in_from[1:]

            new_joins = []
            for i, table in enumerate(remaining_tables):
                join_cond = None
                table_alias = table.alias or table.name

                for cond, lt, rt in join_conditions:
                    if table_alias in (lt, rt):
                        join_cond = cond.copy()
                        break

                new_join = exp.Join(
                    this=table.copy(),
                    side="INNER",
                    kind="INNER",
                    on=join_cond if join_cond else exp.TRUE,
                )
                new_joins.append(new_join)

            if new_joins:
                new_ast.set("joins", new_joins)

                for cond, _, _ in join_conditions:
                    for c in list(new_ast.find_all(exp.EQ)):
                        if c.sql() == cond.sql():
                            c.replace(exp.TRUE)

                return new_ast

        except Exception:
            return None

        return None

    def _fix_join_issues(self, ast: exp.Expression, analysis: Any) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        joins = list(ast.find_all(exp.Join))
        if not joins:
            return None

        try:
            new_ast = ast.copy()
            reordered = False

            for join in new_ast.find_all(exp.Join):
                if not join.args.get("on") or join.args["on"] == exp.TRUE:
                    continue

                on_condition = join.args["on"]
                if isinstance(on_condition, exp.EQ):
                    left_col = on_condition.this
                    right_col = on_condition.expression

                    if isinstance(left_col, exp.Column) and isinstance(right_col, exp.Column):
                        if left_col.table and right_col.table:
                            join_table = join.this
                            join_table_name = join_table.alias if hasattr(join_table, "alias") and join_table.alias else join_table.name if hasattr(join_table, "name") else ""

                            if right_col.table == join_table_name and left_col.table != join_table_name:
                                new_on = exp.EQ(
                                    this=right_col.copy(),
                                    expression=left_col.copy(),
                                )
                                join.set("on", new_on)
                                reordered = True

            if reordered:
                return new_ast

        except Exception:
            return None

        return None
