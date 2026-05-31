from typing import List, Optional, Any
from sqlglot import exp, select
from .base_rule import BaseRewriteRule, RuleApplicationResult


class SubqueryUnfoldingRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Subquery Unfolding"

    @property
    def rule_description(self) -> str:
        return "Convert correlated subqueries and IN subqueries to JOINs for better performance"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        changes = []
        new_ast = ast.copy()

        unfolded = self._unfold_in_subqueries(new_ast)
        if unfolded:
            changes.append("Unfolded IN subquery to JOIN")
            new_ast = unfolded

        unfolded_exists = self._unfold_exists_subqueries(new_ast)
        if unfolded_exists:
            changes.append("Unfolded EXISTS subquery to JOIN")
            new_ast = unfolded_exists

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _unfold_in_subqueries(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        where = ast.find(exp.Where)
        if not where:
            return None

        for in_expr in list(where.find_all(exp.In)):
            if isinstance(in_expr.expressions[0], exp.Subquery):
                subquery = in_expr.expressions[0]
                left_col = in_expr.this

                if isinstance(subquery.this, exp.Select):
                    sub_select = subquery.this
                    sub_cols = list(sub_select.find_all(exp.Column))

                    if len(sub_cols) > 0:
                        sub_table = None
                        for tbl in sub_select.find_all(exp.Table):
                            sub_table = tbl
                            break

                        if sub_table:
                            new_ast = self._convert_in_to_join(
                                ast, left_col, sub_select, sub_table
                            )
                            if new_ast:
                                return new_ast

        return None

    def _convert_in_to_join(
        self,
        ast: exp.Select,
        left_col: exp.Column,
        sub_select: exp.Select,
        sub_table: exp.Table,
    ) -> Optional[exp.Expression]:
        try:
            new_ast = ast.copy()

            sub_col = None
            for col in sub_select.find_all(exp.Column):
                sub_col = col
                break

            if not sub_col:
                return None

            table_alias = sub_table.alias or f"sub_{sub_table.name}"
            new_table = exp.Table(
                this=exp.to_identifier(sub_table.name),
                alias=exp.to_identifier(table_alias),
            )

            new_join = exp.Join(
                this=new_table,
                side="INNER",
                kind="INNER",
                on=exp.EQ(
                    this=left_col.copy(),
                    expression=exp.Column(
                        this=exp.to_identifier(sub_col.name),
                        table=exp.to_identifier(table_alias),
                    ),
                ),
            )

            if new_ast.args.get("joins"):
                new_ast.args["joins"].append(new_join)
            else:
                new_ast.set("joins", [new_join])

            for in_expr in list(new_ast.find_all(exp.In)):
                if (
                    isinstance(in_expr.expressions[0], exp.Subquery)
                    and in_expr.this.sql() == left_col.sql()
                ):
                    in_expr.replace(exp.TRUE)

            if new_ast.find(exp.Distinct) is None:
                if new_ast.args.get("expressions"):
                    new_ast.set("expressions", [exp.Distinct(expressions=new_ast.args["expressions"])])

            return new_ast
        except Exception:
            return None

    def _unfold_exists_subqueries(self, ast: exp.Expression) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        where = ast.find(exp.Where)
        if not where:
            return None

        for exists_expr in list(where.find_all(exp.Exists)):
            if isinstance(exists_expr.this, exp.Subquery):
                subquery = exists_expr.this
                if isinstance(subquery.this, exp.Select):
                    new_ast = self._convert_exists_to_join(ast, exists_expr, subquery.this)
                    if new_ast:
                        return new_ast

        return None

    def _convert_exists_to_join(
        self,
        ast: exp.Select,
        exists_expr: exp.Exists,
        sub_select: exp.Select,
    ) -> Optional[exp.Expression]:
        try:
            new_ast = ast.copy()

            sub_table = None
            for tbl in sub_select.find_all(exp.Table):
                sub_table = tbl
                break

            if not sub_table:
                return None

            table_alias = sub_table.alias or f"exists_{sub_table.name}"
            new_table = exp.Table(
                this=exp.to_identifier(sub_table.name),
                alias=exp.to_identifier(table_alias),
            )

            sub_where = sub_select.find(exp.Where)
            join_condition = None
            if sub_where:
                join_condition = sub_where.this.copy()

            new_join = exp.Join(
                this=new_table,
                side="INNER",
                kind="INNER",
                on=join_condition if join_condition else exp.TRUE,
            )

            if new_ast.args.get("joins"):
                new_ast.args["joins"].append(new_join)
            else:
                new_ast.set("joins", [new_join])

            for e in list(new_ast.find_all(exp.Exists)):
                if e.this.sql() == exists_expr.this.sql():
                    e.replace(exp.TRUE)

            if new_ast.find(exp.Distinct) is None:
                if new_ast.args.get("expressions"):
                    new_ast.set("expressions", [exp.Distinct(expressions=new_ast.args["expressions"])])

            return new_ast
        except Exception:
            return None
