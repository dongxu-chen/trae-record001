from typing import List, Optional, Any
from sqlglot import exp
from .base_rule import BaseRewriteRule, RuleApplicationResult


class IndexHintRule(BaseRewriteRule):
    @property
    def rule_name(self) -> str:
        return "Index Hints"

    @property
    def rule_description(self) -> str:
        def rule_description(self) -> str:
            return "Add USE INDEX hints based on execution plan analysis (MySQL only)"

    def apply(self, ast: exp.Expression, analysis: Optional[Any] = None) -> RuleApplicationResult:
        if self.dialect.lower() != "mysql":
            return RuleApplicationResult(applied=False)

        if not analysis or not hasattr(analysis, "has_full_table_scan"):
            return RuleApplicationResult(applied=False)

        changes = []
        new_ast = ast.copy()

        if analysis.has_full_table_scan and hasattr(analysis, "suggested_indexes") and analysis.suggested_indexes:
            hinted = self._add_index_hints(new_ast, analysis)
            if hinted:
                changes.append("Added USE INDEX hints to avoid full table scans")
                new_ast = hinted

        if changes:
            return RuleApplicationResult(
                applied=True,
                new_ast=new_ast,
                changes=changes,
                description=self.rule_description,
            )

        return RuleApplicationResult(applied=False)

    def _add_index_hints(self, ast: exp.Expression, analysis: Any) -> Optional[exp.Expression]:
        if not isinstance(ast, exp.Select):
            return None

        try:
            new_ast = ast.copy()
            modified = False

            suggested_tables = {}
            for suggestion in analysis.suggested_indexes:
                if "table" in suggestion.lower():
                    words = suggestion.split("'")
                    if len(words) >= 2:
                        table_name = words[1]
                        suggested_tables[table_name] = True

            for table in new_ast.find_all(exp.Table):
                if table.name in suggested_tables:
                    if not table.args.get("hints"):
                        table_alias = table.alias or table.name

                        if table.args.get("db"):
                            hint = exp.Hint(
                                expressions=[
                                    exp.UseIndex(
                                        this=exp.Table(
                                            this=exp.to_identifier(table.name),
                                            db=table.args.get("db"),
                                        ),
                                        expressions=[exp.to_identifier(f"idx_{table_name}_optimization")],
                                    )
                                ]
                            )
                        else:
                            hint = exp.Hint(
                                expressions=[
                                    exp.UseIndex(
                                        this=exp.Table(this=exp.to_identifier(table.name)),
                                        expressions=[exp.to_identifier(f"idx_{table.name}_optimization")],
                                    )
                                ]
                            )
                        table.set("hints", hint)
                        modified = True

            if modified:
                return new_ast

        except Exception:
            return None

        return None
