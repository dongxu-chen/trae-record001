from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


@dataclass
class PlanNode:
    id: int
    operation: str
    table_name: str = ""
    join_type: str = ""
    scan_type: str = ""
    rows: int = 0
    cost: float = 0.0
    total_cost: float = 0.0
    width: int = 0
    condition: str = ""
    index_name: str = ""
    extra: str = ""
    children: List["PlanNode"] = field(default_factory=list)
    parent: Optional["PlanNode"] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "operation": self.operation,
            "table_name": self.table_name,
            "join_type": self.join_type,
            "scan_type": self.scan_type,
            "rows": self.rows,
            "cost": self.cost,
            "total_cost": self.total_cost,
            "width": self.width,
            "condition": self.condition,
            "index_name": self.index_name,
            "extra": self.extra,
            "children": [child.to_dict() for child in self.children],
        }


@dataclass
class PlanAnalysis:
    raw_plan: Any = None
    plan_tree: Optional[PlanNode] = None
    total_cost: float = 0.0
    estimated_rows: int = 0
    has_full_table_scan: bool = False
    has_using_filesort: bool = False
    has_using_temporary: bool = False
    suggested_indexes: List[str] = field(default_factory=list)
    potential_problems: List[str] = field(default_factory=list)
    join_issues: List[str] = field(default_factory=list)
    subquery_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_cost": self.total_cost,
            "estimated_rows": self.estimated_rows,
            "has_full_table_scan": self.has_full_table_scan,
            "has_using_filesort": self.has_using_filesort,
            "has_using_temporary": self.has_using_temporary,
            "suggested_indexes": self.suggested_indexes,
            "potential_problems": self.potential_problems,
            "join_issues": self.join_issues,
            "subquery_issues": self.subquery_issues,
            "recommendations": self.recommendations,
            "plan_tree": self.plan_tree.to_dict() if self.plan_tree else None,
        }


class ExecutionPlanAnalyzer(ABC):
    def __init__(self, db_type: str):
        self.db_type = db_type

    @abstractmethod
    def parse_plan(self, raw_plan: Any) -> PlanAnalysis:
        pass

    @abstractmethod
    def get_explain_sql(self, sql: str) -> str:
        pass

    def _analyze_common_issues(self, analysis: PlanAnalysis, root_node: PlanNode) -> None:
        self._check_full_table_scan(analysis, root_node)
        self._check_filesort(analysis, root_node)
        self._check_temporary(analysis, root_node)
        self._check_large_scans(analysis, root_node)
        self._check_join_types(analysis, root_node)
        self._generate_recommendations(analysis)

    def _check_full_table_scan(self, analysis: PlanAnalysis, node: PlanNode) -> None:
        if node.scan_type and "ALL" in node.scan_type.upper():
            analysis.has_full_table_scan = True
            if node.table_name:
                analysis.potential_problems.append(
                    f"Full table scan on table '{node.table_name}'"
                )
                analysis.suggested_indexes.append(
                    f"Consider adding an index on table '{node.table_name}' for filtered columns"
                )
        for child in node.children:
            self._check_full_table_scan(analysis, child)

    def _check_filesort(self, analysis: PlanAnalysis, node: PlanNode) -> None:
        if "filesort" in node.extra.lower() or "filesort" in node.operation.lower():
            analysis.has_using_filesort = True
            analysis.potential_problems.append(
                "Using filesort - ORDER BY/GROUP BY optimization needed"
            )
        for child in node.children:
            self._check_filesort(analysis, child)

    def _check_temporary(self, analysis: PlanAnalysis, node: PlanNode) -> None:
        if "temporary" in node.extra.lower() or "temporary" in node.operation.lower():
            analysis.has_using_temporary = True
            analysis.potential_problems.append(
                "Using temporary table - GROUP BY/DISTINCT optimization needed"
            )
        for child in node.children:
            self._check_temporary(analysis, child)

    def _check_large_scans(self, analysis: PlanAnalysis, node: PlanNode) -> None:
        if node.rows > 10000:
            analysis.potential_problems.append(
                f"Large scan on '{node.table_name}': {node.rows:,} rows estimated"
            )
        for child in node.children:
            self._check_large_scans(analysis, child)

    def _check_join_types(self, analysis: PlanAnalysis, node: PlanNode) -> None:
        if node.join_type:
            join_type_upper = node.join_type.upper()
            if join_type_upper in ["ALL", "index"]:
                analysis.join_issues.append(
                    f"Inefficient join type '{node.join_type}' on table '{node.table_name}'"
                )
        for child in node.children:
            self._check_join_types(analysis, child)

    def _generate_recommendations(self, analysis: PlanAnalysis) -> None:
        if analysis.has_full_table_scan:
            analysis.recommendations.append(
                "Add appropriate indexes to avoid full table scans"
            )
        if analysis.has_using_filesort:
            analysis.recommendations.append(
                "Add index for ORDER BY columns to avoid filesort"
            )
        if analysis.has_using_temporary:
            analysis.recommendations.append(
                "Optimize GROUP BY or DISTINCT operations to avoid temporary tables"
            )
        if analysis.join_issues:
            analysis.recommendations.append(
                "Optimize join conditions and ensure joined columns are indexed"
            )
        if analysis.subquery_issues:
            analysis.recommendations.append(
                "Consider rewriting subqueries as JOINs for better performance"
            )
