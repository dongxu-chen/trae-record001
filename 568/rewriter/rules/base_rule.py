from dataclasses import dataclass, field
from typing import List, Optional, Any, Tuple
from abc import ABC, abstractmethod
from sqlglot import exp
import sqlglot


@dataclass
class RuleApplicationResult:
    applied: bool
    new_ast: Optional[exp.Expression] = None
    changes: List[str] = field(default_factory=list)
    description: str = ""


class BaseRewriteRule(ABC):
    def __init__(self, dialect: str = "mysql"):
        self.dialect = dialect
        self._sqlglot_dialect = self._map_dialect(dialect)
        self.applied_changes: List[str] = []

    def _map_dialect(self, dialect: str) -> str:
        dialect_map = {
            "mysql": "mysql",
            "postgresql": "postgres",
            "pg": "postgres",
        }
        return dialect_map.get(dialect.lower(), "mysql")

    @abstractmethod
    def apply(self, ast: exp.Expression, analysis: Any = None) -> RuleApplicationResult:
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        pass

    @property
    @abstractmethod
    def rule_description(self) -> str:
        pass

    def _generate_sql(self, ast: exp.Expression) -> str:
        return ast.sql(dialect=self._sqlglot_dialect, pretty=True)

    def _has_subquery(self, ast: exp.Expression) -> bool:
        return ast.find(exp.Subquery) is not None

    def _get_aliases(self, ast: exp.Expression) -> dict:
        aliases = {}
        for alias in ast.find_all(exp.Alias):
            if isinstance(alias.parent, exp.From):
                if hasattr(alias.this, "name"):
                    aliases[alias.alias] = alias.this.name
        for table in ast.find_all(exp.Table):
            if table.alias:
                aliases[table.alias] = table.name
        return aliases

    def _is_equivalent_expression(self, expr1: exp.Expression, expr2: exp.Expression) -> bool:
        return expr1.sql() == expr2.sql()
