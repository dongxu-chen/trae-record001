from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple
from sqlglot import exp, parse_one
import sqlparse

from config import RewriteConfig
from sql_analyzer import SQLParser, ParsedSQL
from execution_plan import PlanAnalysis
from .rules import (
    BaseRewriteRule,
    SubqueryUnfoldingRule,
    JoinOptimizationRule,
    PredicatePushdownRule,
    RemoveRedundantColumnsRule,
    SimplifyConditionsRule,
    IndexHintRule,
    LimitPushdownRule,
    DistinctOptimizationRule,
    OrToUnionRule,
    NotExistsToLeftJoinRule,
)


@dataclass
class RewriteStep:
    rule_name: str
    rule_description: str
    applied: bool
    changes: List[str] = field(default_factory=list)
    sql_before: str = ""
    sql_after: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_name": self.rule_name,
            "rule_description": self.rule_description,
            "applied": self.applied,
            "changes": self.changes,
            "sql_before": self.sql_before,
            "sql_after": self.sql_after,
        }


@dataclass
class RewriteResult:
    original_sql: str
    rewritten_sql: str = ""
    is_rewritten: bool = False
    steps: List[RewriteStep] = field(default_factory=list)
    rules_applied: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "original_sql": self.original_sql,
            "rewritten_sql": self.rewritten_sql,
            "is_rewritten": self.is_rewritten,
            "rules_applied": self.rules_applied,
            "steps": [step.to_dict() for step in self.steps],
            "error": self.error,
        }


class SQLRewriter:
    def __init__(self, dialect: str = "mysql", config: Optional[RewriteConfig] = None):
        self.dialect = dialect
        self.config = config or RewriteConfig()
        self.parser = SQLParser(dialect)
        self._sqlglot_dialect = self._map_dialect(dialect)

    def _map_dialect(self, dialect: str) -> str:
        dialect_map = {
            "mysql": "mysql",
            "postgresql": "postgres",
            "pg": "postgres",
        }
        return dialect_map.get(dialect.lower(), "mysql")

    def _get_rules(self) -> List[BaseRewriteRule]:
        rules = []

        if self.config.enable_remove_redundant:
            rules.append(RemoveRedundantColumnsRule(self.dialect))

        if self.config.enable_simplify_conditions:
            rules.append(SimplifyConditionsRule(self.dialect))

        if self.config.enable_or_to_union:
            rules.append(OrToUnionRule(self.dialect))

        if self.config.enable_not_exists_to_leftjoin:
            rules.append(NotExistsToLeftJoinRule(self.dialect))

        if self.config.enable_subquery_unfolding:
            rules.append(SubqueryUnfoldingRule(self.dialect))

        if self.config.enable_push_predicates:
            rules.append(PredicatePushdownRule(self.dialect))

        if self.config.enable_optimize_joins:
            rules.append(JoinOptimizationRule(self.dialect))

        rules.append(LimitPushdownRule(self.dialect))
        rules.append(DistinctOptimizationRule(self.dialect))

        if self.config.enable_use_index_hints:
            rules.append(IndexHintRule(self.dialect))

        return rules

    def rewrite(
        self,
        sql: str,
        plan_analysis: Optional[PlanAnalysis] = None,
        max_attempts: Optional[int] = None,
    ) -> RewriteResult:
        result = RewriteResult(original_sql=sql)

        try:
            parsed = self.parser.parse(sql)
            if not parsed.is_valid or parsed.ast is None:
                result.error = parsed.error or "Invalid SQL"
                return result

            current_ast = parsed.ast.copy()
            rules = self._get_rules()
            max_attempts = max_attempts or self.config.max_rewrite_attempts

            for attempt in range(max_attempts):
                applied_any = False

                for rule in rules:
                    sql_before = self._generate_sql(current_ast)

                    try:
                        rule_result = rule.apply(current_ast, plan_analysis)

                        if rule_result.applied and rule_result.new_ast is not None:
                            current_ast = rule_result.new_ast
                            sql_after = self._generate_sql(current_ast)

                            step = RewriteStep(
                                rule_name=rule.rule_name,
                                rule_description=rule.rule_description,
                                applied=True,
                                changes=rule_result.changes,
                                sql_before=sql_before,
                                sql_after=sql_after,
                            )
                            result.steps.append(step)
                            result.rules_applied += 1
                            applied_any = True

                    except Exception as e:
                        step = RewriteStep(
                            rule_name=rule.rule_name,
                            rule_description=rule.rule_description,
                            applied=False,
                            changes=[f"Error: {str(e)}"],
                            sql_before=sql_before,
                            sql_after=sql_before,
                        )
                        result.steps.append(step)

                if not applied_any:
                    break

            rewritten_sql = self._generate_sql(current_ast)
            rewritten_sql = self._format_sql(rewritten_sql)

            if rewritten_sql != self._format_sql(sql):
                result.rewritten_sql = rewritten_sql
                result.is_rewritten = True
            else:
                result.rewritten_sql = sql
                result.is_rewritten = False

        except Exception as e:
            result.error = str(e)

        return result

    def rewrite_with_plan(
        self,
        sql: str,
        plan_analysis: PlanAnalysis,
    ) -> RewriteResult:
        return self.rewrite(sql, plan_analysis)

    def _generate_sql(self, ast: exp.Expression) -> str:
        return ast.sql(dialect=self._sqlglot_dialect, pretty=True)

    def _format_sql(self, sql: str) -> str:
        formatted = sqlparse.format(
            sql,
            reindent=True,
            keyword_case="upper",
            identifier_case="lower",
            comma_first=False,
        )
        return formatted.strip()

    def validate_rewrite(self, original_sql: str, rewritten_sql: str) -> Tuple[bool, Optional[str]]:
        try:
            original_parsed = self.parser.parse(original_sql)
            rewritten_parsed = self.parser.parse(rewritten_sql)

            if not original_parsed.is_valid:
                return False, f"Original SQL is invalid: {original_parsed.error}"

            if not rewritten_parsed.is_valid:
                return False, f"Rewritten SQL is invalid: {rewritten_parsed.error}"

            valid_types = {"SELECT", "UNION", "UNION ALL", "INTERSECT", "EXCEPT"}
            if not (original_parsed.sql_type in valid_types and rewritten_parsed.sql_type in valid_types):
                return False, f"SQL type mismatch: {original_parsed.sql_type} vs {rewritten_parsed.sql_type}"

            original_tables = set(original_parsed.tables)
            rewritten_tables = set(rewritten_parsed.tables)
            if not rewritten_tables.issuperset(original_tables):
                missing = original_tables - rewritten_tables
                return False, f"Missing tables in rewritten SQL: {missing}"

            return True, None

        except Exception as e:
            return False, str(e)

    def get_available_rules(self) -> List[Dict[str, str]]:
        return [
            {
                "name": rule.rule_name,
                "description": rule.rule_description,
            }
            for rule in self._get_rules()
        ]
