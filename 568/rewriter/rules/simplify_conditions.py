from typing import List, Optional, Any
from sqlglot import exp
from .base_rule import BaseRewriteRule, RuleApplicationResult


class SimplifyConditionsRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Simplify Conditions"

    @property
    def rule_description(self) -> str:
        return "Simplify WHERE/HAVING conditions: remove redundant checks, optimize IN clauses, simplify boolean expressions"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        simplified = self._simplify_boolean_expressions(new_ast)
        if simplified:
            changes.append("Simplified boolean expressions")
            new_ast = simplified

        optimized_in = self._optimize_in_clauses(new_ast)
        if optimized_in:
            changes.append("Optimized IN clauses with many values")
            new_ast = optimized_in

        removed_redundant = self._remove_redundant_conditions(new_ast)
        if removed_redundant:
            changes.append("Removed redundant conditions")
            new_ast = removed_redundant

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _simplify_boolean_expressions(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        where = ast.find(exp.Where)
        having = ast.find(exp.Having)

        if not where and not having:
            return None

        modified = False
        new_ast = ast.copy()

        for clause in [new_ast.find(exp.Where), new_ast.find(exp.Having)]:
            if not clause:
                continue

            original_sql = clause.this.sql()
            simplified = self._simplify_expression_tree(clause.this)

            if simplified is not None:
                simplified_sql = simplified.sql()
                if simplified_sql != original_sql:
                    clause.set("this", simplified)
                    modified = True

        if modified:
            return new_ast

        return None

    def _simplify_expression_tree(self, expr: exp.Expression) -> Optional[exp.Expression]:
        if isinstance(expr, exp.And):
            left = self._simplify_expression_tree(expr.this) or expr.this
            right = self._simplify_expression_tree(expr.expression) or expr.expression

            if left == exp.TRUE:
                return right
            if right == exp.TRUE:
                return left
            if left == exp.FALSE or right == exp.FALSE:
                return exp.FALSE

            if left.sql() == right.sql():
                return left

            new_expr = exp.And(this=left, expression=right)
            return new_expr

        elif isinstance(expr, exp.Or):
            left = self._simplify_expression_tree(expr.this) or expr.this
            right = self._simplify_expression_tree(expr.expression) or expr.expression

            if left == exp.TRUE or right == exp.TRUE:
                return exp.TRUE
            if left == exp.FALSE:
                return right
            if right == exp.FALSE:
                return left

            if left.sql() == right.sql():
                return left

            new_expr = exp.Or(this=left, expression=right)
            return new_expr

        elif isinstance(expr, exp.Not):
            inner = expr.this

            if isinstance(inner, exp.Not):
                return self._simplify_expression_tree(inner.this) or inner.this

            if isinstance(inner, exp.EQ):
                return exp.NEQ(this=inner.this, expression=inner.expression)

            if isinstance(inner, exp.NEQ):
                return exp.EQ(this=inner.this, expression=inner.expression)

            if isinstance(inner, exp.GT):
                return exp.LTE(this=inner.this, expression=inner.expression)

            if isinstance(inner, exp.GTE):
                return exp.LT(this=inner.this, expression=inner.expression)

            if isinstance(inner, exp.LT):
                return exp.GTE(this=inner.this, expression=inner.expression)

            if isinstance(inner, exp.LTE):
                return exp.GT(this=inner.this, expression=inner.expression)

            if isinstance(inner, exp.And):
                return exp.Or(
                    this=exp.Not(this=inner.this),
                    expression=exp.Not(this=inner.expression),
                )

            if isinstance(inner, exp.Or):
                return exp.And(
                    this=exp.Not(this=inner.this),
                    expression=exp.Not(this=inner.expression),
                )

        return None

    def _optimize_in_clauses(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        where = ast.find(exp.Where)
        if not where:
            return None

        modified = False
        new_ast = ast.copy()

        for in_expr in list(new_ast.find_all(exp.In)):
            values = in_expr.expressions

            if len(values) > 50:
                modified = True

            if len(values) >= 2 and all(isinstance(v, exp.Literal) for v in values):
                sorted_values = sorted(values, key=lambda v: str(v))
                in_expr.set("expressions", sorted_values)
                modified = True

        if modified:
            return new_ast

        return None

    def _remove_redundant_conditions(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        where = ast.find(exp.Where)
        if not where:
            return None

        conditions = self._extract_all_conditions(where.this)
        if len(conditions) < 2:
            return None

        seen = set()
        unique_conditions = []

        for cond in conditions:
            cond_sql = cond.sql()
            if cond_sql not in seen:
                seen.add(cond_sql)
                unique_conditions.append(cond)

        if len(unique_conditions) < len(conditions):
            try:
                new_ast = ast.copy()
                new_where = new_ast.find(exp.Where)

                if unique_conditions:
                    new_condition = unique_conditions[0]
                    for cond in unique_conditions[1:]:
                        new_condition = exp.And(this=new_condition, expression=cond)
                    new_where.set("this", new_condition)
                    return new_ast
            except Exception:
                pass

        return None

    def _extract_all_conditions(self, expr: exp.Expression) -> List[exp.Expression]:
        conditions = []

        if isinstance(expr, exp.And):
            conditions.extend(self._extract_all_conditions(expr.this))
            conditions.extend(self._extract_all_conditions(expr.expression))
        else:
            conditions.append(expr)

        return conditions
