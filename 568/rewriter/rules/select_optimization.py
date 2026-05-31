from typing import List, Optional, Any
from sqlglot import exp
from .base_rule import BaseRewriteRule, RuleApplicationResult


class RemoveRedundantColumnsRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Remove Redundant Columns"

    @property
    def rule_description(self) -> str:
        return "Replace SELECT * with specific columns and remove unused columns from projection"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        star_replaced = self._replace_select_star(new_ast)
        if star_replaced:
            changes.append("Replaced SELECT * with explicit columns")
            new_ast = star_replaced

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _replace_select_star(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        has_star = False
        select_expressions = ast.args.get("expressions", [])

        for expr in select_expressions:
            if isinstance(expr, exp.Star):
                has_star = True
                break
            if isinstance(expr, exp.All) and not hasattr(expr, "this"):
                has_star = True
                break

        if not has_star:
            return None

        try:
            new_ast = ast.copy()
            tables = list(new_ast.find_all(exp.Table))

            if not tables:
                return None

            new_select_exprs = []
            seen_columns = set()

            from_clause = new_ast.find(exp.From)
            joins = list(new_ast.find_all(exp.Join))

            all_tables = [t for t in tables]

            for table in all_tables:
                table_name = table.name
                table_alias = table.alias or table_name

                where = new_ast.find(exp.Where)
                if where:
                    for col in where.find_all(exp.Column):
                        if col.table == table_alias or col.table == table_name:
                            col_key = f"{table_alias}.{col.name}"
                            if col_key not in seen_columns:
                                seen_columns.add(col_key)
                                new_col = exp.Column(
                                    this=exp.to_identifier(col.name),
                                    table=exp.to_identifier(table_alias),
                                )
                                new_select_exprs.append(new_col)

                for join in joins:
                    join_on = join.args.get("on")
                    if join_on:
                        for col in join_on.find_all(exp.Column):
                            if col.table == table_alias or col.table == table_name:
                                col_key = f"{table_alias}.{col.name}"
                                if col_key not in seen_columns:
                                    seen_columns.add(col_key)
                                    new_col = exp.Column(
                                        this=exp.to_identifier(col.name),
                                        table=exp.to_identifier(table_alias),
                                    )
                                    new_select_exprs.append(new_col)

                group_by = new_ast.find(exp.Group)
                if group_by:
                    for col in group_by.find_all(exp.Column):
                        if col.table == table_alias or col.table == table_name:
                            col_key = f"{table_alias}.{col.name}"
                            if col_key not in seen_columns:
                                seen_columns.add(col_key)
                                new_col = exp.Column(
                                    this=exp.to_identifier(col.name),
                                    table=exp.to_identifier(table_alias),
                                )
                                new_select_exprs.append(new_col)

                order_by = new_ast.find(exp.Order)
                if order_by:
                    for col in order_by.find_all(exp.Column):
                        if col.table == table_alias or col.table == table_name:
                            col_key = f"{table_alias}.{col.name}"
                            if col_key not in seen_columns:
                                seen_columns.add(col_key)
                                new_col = exp.Column(
                                    this=exp.to_identifier(col.name),
                                    table=exp.to_identifier(table_alias),
                                )
                                new_select_exprs.append(new_col)

            if not new_select_exprs:
                for table in all_tables:
                    table_alias = table.alias or table.name
                    new_col = exp.Column(
                        this=exp.to_identifier("id"),
                        table=exp.to_identifier(table_alias),
                    )
                    new_select_exprs.append(new_col)

            if new_select_exprs:
                new_ast.set("expressions", new_select_exprs)
                return new_ast

        except Exception:
            return None

        return None


class LimitPushdownRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Limit Pushdown"

    @property
    def rule_description(self) -> str:
        return "Push LIMIT clause down to subqueries when safe to reduce intermediate result sizes"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        pushed = self._push_limit_to_subqueries(new_ast)
        if pushed:
            changes.append("Pushed LIMIT down to subqueries")
            new_ast = pushed

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _push_limit_to_subqueries(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        limit = ast.find(exp.Limit)
        if not limit:
            return None

        limit_value = limit.args.get("expression")
        if not limit_value:
            return None

        modified = False
        new_ast = ast.copy()

        for subquery in list(new_ast.find_all(exp.Subquery)):
            if not isinstance(subquery.this, exp.Select):
                continue

            sub_select = subquery.this

            if self._is_safe_to_push_limit(sub_select, new_ast):
                existing_limit = sub_select.find(exp.Limit)
                if not existing_limit:
                    new_limit = exp.Limit(expression=limit_value.copy())
                    sub_select.set("limit", new_limit)
                    modified = True

        if modified:
            return new_ast

        return None

    def _is_safe_to_push_limit(self, subquery: exp.Select, outer_query: exp.Select) -> bool:
        if subquery.find(exp.Distinct):
            return False

        if subquery.find(exp.Group):
            return False

        if subquery.find(exp.Order):
            return False

        if outer_query.find(exp.Distinct):
            return False

        if outer_query.find(exp.Group):
            return False

        joins = list(outer_query.find_all(exp.Join))
        for join in joins:
            subquery_tables = {t.name for t in subquery.find_all(exp.Table)}
            join_table = join.this
            if hasattr(join_table, "name") and join_table.name in subquery_tables:
                join_type = join.args.get("side", "INNER").upper()
                if join_type not in ["INNER", ""]:
                    return False

        return True


class DistinctOptimizationRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Distinct Optimization"

    @property
    def rule_description(self) -> str:
        return "Remove unnecessary DISTINCT when using EXISTS or key column with GROUP BY"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        removed = self._remove_unnecessary_distinct(new_ast)
        if removed:
            changes.append("Removed unnecessary DISTINCT")
            new_ast = removed

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _remove_unnecessary_distinct(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        distinct = ast.find(exp.Distinct)
        if not distinct:
            return None

        group_by = ast.find(exp.Group)
        if group_by:
            try:
                new_ast = ast.copy()
                for d in list(new_ast.find_all(exp.Distinct)):
                    if len(d.find_all(exp.Expression)) > 0:
                        inner_exprs = list(d.find_all(exp.Expression, depth=1))
                        if inner_exprs:
                            parent = d.parent
                            idx = list(parent.args.get("expressions", [])).index(d) if d in parent.args.get("expressions", []) else -1
                            if idx >= 0:
                                parent.args["expressions"][idx:idx+1] = inner_exprs
                            else:
                                d.pop()
                    else:
                        d.pop()
                return new_ast
            except Exception:
                pass

        select_exprs = ast.args.get("expressions", [])
        if distinct and len(select_exprs) == 1:
            expr = select_exprs[0]
            if isinstance(expr, exp.Distinct):
                inner_exprs = expr.args.get("expressions", [])
                if len(inner_exprs) == 1 and isinstance(inner_exprs[0], exp.Count):
                    try:
                        new_ast = ast.copy()
                        count_expr = inner_exprs[0]
                        for d in list(new_ast.find_all(exp.Distinct)):
                            d.replace(count_expr)
                        return new_ast
                    except Exception:
                        pass

        return None
