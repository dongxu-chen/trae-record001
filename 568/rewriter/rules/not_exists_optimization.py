from typing import List, Optional, Any
from sqlglot import exp
from .base_rule import BaseRewriteRule, RuleApplicationResult


class NotExistsToLeftJoinRule(BaseRewriteRule):
    """
    将NOT EXISTS子查询优化为LEFT JOIN + IS NULL形式。
    
    优化场景：
    - WHERE NOT EXISTS (SELECT 1 FROM b WHERE a.id = b.a_id)
      -> LEFT JOIN b ON a.id = b.a_id WHERE b.id IS NULL
    
    优点：
    - 可以更好地利用索引
    - 优化器可以选择更好的连接算法
    - 避免相关子查询的逐行执行
    """

    @property
    def rule_name(self) -> str:
        return "NOT EXISTS to LEFT JOIN Optimization"

    @property
    def rule_description(self) -> str:
        return "Convert NOT EXISTS correlated subqueries to LEFT JOIN with IS NULL for better performance"

    def apply(self, ast: exp.Expression, analysis: Any = None) -> RuleApplicationResult:
        if not isinstance(ast, exp.Select):
            return RuleApplicationResult(applied=False)

        self.applied_changes = []
        new_ast = self._optimize_not_exists(ast)

        if new_ast and new_ast.sql() != ast.sql():
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=self.applied_changes,
                description="Converted NOT EXISTS subquery to LEFT JOIN with IS NULL check"
            )

        return RuleApplicationResult(applied=False)

    def _optimize_not_exists(self, ast: exp.Expression) -> Optional[exp.Expression]:
        where = ast.find(exp.Where)
        if not where:
            return None

        not_exists_subqueries = self._find_not_exists_subqueries(where.this)
        if not not_exists_subqueries:
            return None

        new_ast = ast.copy()

        for ne_subquery, parent_expr in not_exists_subqueries:
            subquery_select = ne_subquery.this
            if not isinstance(subquery_select, exp.Select):
                continue

            join_info = self._extract_join_info(subquery_select)
            if not join_info:
                continue

            join_alias = self._generate_unique_alias(new_ast, join_info["table_name"])
            join_info["alias"] = join_alias

            new_ast = self._add_left_join(new_ast, join_info)

            current_where = new_ast.find(exp.Where)
            if current_where:
                is_null_col = exp.Column(
                    table=join_alias,
                    this=exp.Identifier(this="id")
                )
                is_null = exp.Is(this=is_null_col, expression=exp.Null())

                if current_where.this is parent_expr:
                    current_where.set("this", is_null)
                else:
                    self._replace_not_exists(current_where.this, parent_expr, is_null)

            self.applied_changes.append(
                f"Converted NOT EXISTS on table '{join_info['table_name']}' "
                f"to LEFT JOIN with alias '{join_alias}' + IS NULL check"
            )

        return new_ast

    def _find_not_exists_subqueries(self, expr: exp.Expression) -> List[tuple]:
        results = []
        self._traverse_for_not_exists(expr, None, results)
        return results

    def _traverse_for_not_exists(self, expr: exp.Expression, parent: Optional[exp.Expression], results: List[tuple]):
        if isinstance(expr, exp.Not):
            inner = expr.this
            if isinstance(inner, exp.Exists):
                results.append((inner, expr))

        for child in expr.args.values():
            if isinstance(child, exp.Expression):
                self._traverse_for_not_exists(child, expr, results)
            elif isinstance(child, list):
                for item in child:
                    if isinstance(item, exp.Expression):
                        self._traverse_for_not_exists(item, expr, results)

    def _extract_join_info(self, subquery: exp.Select) -> Optional[dict]:
        tables = list(subquery.find_all(exp.Table))
        if len(tables) != 1:
            return None

        table = tables[0]
        table_name = table.name
        table_alias = table.alias or table_name

        where = subquery.find(exp.Where)
        if not where:
            return None

        join_conditions = self._extract_join_conditions(where.this, table_alias)
        if not join_conditions:
            return None

        return {
            "table_name": table_name,
            "table_alias_in_subquery": table_alias,
            "join_conditions": join_conditions
        }

    def _extract_join_conditions(self, expr: exp.Expression, table_alias: str) -> List[dict]:
        conditions = []
        self._traverse_join_conditions(expr, table_alias, conditions)
        return conditions

    def _traverse_join_conditions(self, expr: exp.Expression, table_alias: str, conditions: List[dict]):
        if isinstance(expr, exp.And):
            self._traverse_join_conditions(expr.this, table_alias, conditions)
            self._traverse_join_conditions(expr.expression, table_alias, conditions)
            return

        if isinstance(expr, exp.EQ):
            left, right = expr.this, expr.expression

            left_table = self._get_column_table(left)
            right_table = self._get_column_table(right)

            if left_table == table_alias and right_table != table_alias:
                conditions.append({
                    "left_col": right,
                    "right_col": left
                })
            elif right_table == table_alias and left_table != table_alias:
                conditions.append({
                    "left_col": left,
                    "right_col": right
                })

    def _get_column_table(self, expr: exp.Expression) -> Optional[str]:
        if isinstance(expr, exp.Column):
            if hasattr(expr, "table") and expr.table:
                return expr.table
        return None

    def _generate_unique_alias(self, ast: exp.Expression, base_name: str) -> str:
        existing_aliases = set()
        for table in ast.find_all(exp.Table):
            if table.alias:
                existing_aliases.add(table.alias)
            existing_aliases.add(table.name)

        alias = f"{base_name}_ne"
        counter = 1
        while alias in existing_aliases:
            alias = f"{base_name}_ne{counter}"
            counter += 1

        return alias

    def _add_left_join(self, ast: exp.Select, join_info: dict) -> exp.Select:
        join_conditions = join_info["join_conditions"]
        on_expr = None
        for cond in join_conditions:
            left_col = cond["left_col"].copy()
            right_col = cond["right_col"].copy()

            if isinstance(right_col, exp.Column) and right_col.table == join_info["table_alias_in_subquery"]:
                right_col.set("table", join_info["alias"])

            eq_expr = exp.EQ(this=left_col, expression=right_col)
            if on_expr is None:
                on_expr = eq_expr
            else:
                on_expr = exp.And(this=on_expr, expression=eq_expr)

        new_sql = f"""
        SELECT *
        FROM (
            {ast.sql()}
        ) AS orig_query
        LEFT JOIN {join_info['table_name']} AS {join_info['alias']}
            ON {on_expr.sql()}
        """.strip()

        from sqlglot import parse_one
        new_ast = parse_one(new_sql, dialect=self._sqlglot_dialect)

        return new_ast

    def _update_where_condition(self, where_cond: Optional[exp.Expression], 
                                parent_expr: exp.Expression,
                                not_exists_expr: exp.Expression,
                                join_info: dict) -> exp.Expression:
        is_null_col = exp.Column(
            table=join_info["alias"],
            this=exp.Identifier(this="id")
        )
        is_null = exp.Is(this=is_null_col)
        is_null.set("expression", exp.Null())

        if where_cond is None:
            return is_null

        if where_cond is parent_expr:
            return is_null

        self._replace_not_exists(where_cond, parent_expr, is_null)
        return where_cond

    def _replace_not_exists(self, expr: exp.Expression, target: exp.Expression, replacement: exp.Expression):
        for key, child in list(expr.args.items()):
            if child is target:
                expr.set(key, replacement)
            elif isinstance(child, exp.Expression):
                self._replace_not_exists(child, target, replacement)
            elif isinstance(child, list):
                for i, item in enumerate(child):
                    if item is target:
                        child[i] = replacement
                    elif isinstance(item, exp.Expression):
                        self._replace_not_exists(item, target, replacement)
