from typing import List, Optional, Any
from sqlglot import exp
from .base_rule import BaseRewriteRule, RuleApplicationResult


class PredicatePushdownRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Predicate Pushdown"

    @property
    def rule_description(self) -> str:
        return "Push WHERE/HAVING conditions down to subqueries and JOINs to reduce rows early"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        pushed = self._push_predicates_to_subqueries(new_ast)
        if pushed:
            changes.append("Pushed predicates down to subqueries")
            new_ast = pushed

        pushed_having = self._push_having_to_where(new_ast)
        if pushed_having:
            changes.append("Pushed HAVING conditions to WHERE clause")
            new_ast = pushed_having

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _push_predicates_to_subqueries(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        where = ast.find(exp.Where)
        if not where:
            return None

        outer_where_conditions = self._extract_simple_conditions(where.this)
        if not outer_where_conditions:
            return None

        modified = False
        new_ast = ast.copy()

        for subquery in list(new_ast.find_all(exp.Subquery)):
            if not isinstance(subquery.this, exp.Select):
                continue

            sub_select = subquery.this
            sub_where = sub_select.find(exp.Where)

            sub_aliases = self._get_subquery_aliases(sub_select)

            for cond in outer_where_conditions:
                cols_in_cond = list(cond.find_all(exp.Column))
                if all(col.table in sub_aliases for col in cols_in_cond if col.table):
                    if self._condition_is_safe_to_push(cond, sub_select):
                        if sub_where:
                            new_condition = exp.And(this=sub_where.this, expression=cond.copy())
                            sub_where.set("this", new_condition)
                        else:
                            new_where = exp.Where(this=cond.copy())
                            sub_select.set("where", new_where)

                        for outer_cond in list(new_ast.find_all(type(cond))):
                            if outer_cond.sql() == cond.sql():
                                outer_cond.replace(exp.TRUE)

                        modified = True

        if modified:
            self._cleanup_where_clause(new_ast)
            return new_ast

        return None

    def _extract_simple_conditions(self, condition: exp.Expression) -> List[exp.Expression]:
        conditions = []

        if isinstance(condition, exp.And):
            conditions.extend(self._extract_simple_conditions(condition.this))
            conditions.extend(self._extract_simple_conditions(condition.expression))
        elif isinstance(condition, (exp.EQ, exp.NEQ, exp.GT, exp.LT, exp.GTE, exp.LTE, exp.Like, exp.In)):
            conditions.append(condition)

        return conditions

    def _get_subquery_aliases(self, subquery: exp.Select) -> set:
        aliases = set()
        for tbl in subquery.find_all(exp.Table):
            if tbl.alias:
                aliases.add(tbl.alias)
            aliases.add(tbl.name)
        return aliases

    def _condition_is_safe_to_push(self, condition: exp.Expression, subquery: exp.Select) -> bool:
        if subquery.find(exp.Distinct):
            return False

        if subquery.find(exp.Group):
            cols_in_cond = list(condition.find_all(exp.Column))
            group_cols = list(subquery.find(exp.Group).find_all(exp.Column))
            group_col_names = {col.name for col in group_cols}

            for col in cols_in_cond:
                if col.name not in group_col_names:
                    return False

        if subquery.find(exp.Limit):
            return False

        return True

    def _push_having_to_where(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        having = ast.find(exp.Having)
        group_by = ast.find(exp.Group)

        if not having or not group_by:
            return None

        group_cols = {col.name for col in group_by.find_all(exp.Column)}
        aggregate_funcs = {exp.Sum, exp.Count, exp.Avg, exp.Min, exp.Max}

        conditions_to_push = []
        remaining_conditions = []

        for cond in self._extract_simple_conditions(having.this):
            has_aggregate = any(
                isinstance(expr, tuple(aggregate_funcs))
                for expr in cond.find_all(exp.Expression)
            )

            cols_in_cond = {col.name for col in cond.find_all(exp.Column)}

            if not has_aggregate and all(col in group_cols for col in cols_in_cond):
                conditions_to_push.append(cond)
            else:
                remaining_conditions.append(cond)

        if not conditions_to_push:
            return None

        try:
            new_ast = ast.copy()
            where = new_ast.find(exp.Where)

            for cond in conditions_to_push:
                if where:
                    new_condition = exp.And(this=where.this, expression=cond.copy())
                    where.set("this", new_condition)
                else:
                    new_where = exp.Where(this=cond.copy())
                    new_ast.set("where", new_where)
                    where = new_ast.find(exp.Where)

            if remaining_conditions:
                new_having_condition = remaining_conditions[0]
                for cond in remaining_conditions[1:]:
                    new_having_condition = exp.And(this=new_having_condition, expression=cond)
                new_ast.find(exp.Having).set("this", new_having_condition)
            else:
                for h in list(new_ast.find_all(exp.Having)):
                    h.pop()

            self._cleanup_where_clause(new_ast)
            return new_ast

        except Exception:
            return None

    def _cleanup_where_clause(self, ast: exp.Expression) -> None:
        where = ast.find(exp.Where)
        if not where:
            return

        def cleanup_condition(cond: exp.Expression) -> Optional[exp.Expression]:
            if isinstance(cond, exp.And):
                left = cleanup_condition(cond.this)
                right = cleanup_condition(cond.expression)

                if left == exp.TRUE and right == exp.TRUE:
                    return exp.TRUE
                elif left == exp.TRUE:
                    return right
                elif right == exp.TRUE:
                    return left
                else:
                    return exp.And(this=left, expression=right)
            return cond

        cleaned = cleanup_condition(where.this)
        if cleaned == exp.TRUE:
            where.pop()
        else:
            where.set("this", cleaned)
