from typing import List, Dict, Any
import json
from .analyzer import ExecutionPlanAnalyzer, PlanAnalysis, PlanNode


class PostgreSQLExecutionPlanAnalyzer(ExecutionPlanAnalyzer):
    def __init__(self):
        super().__init__("postgresql")
        self._node_id_counter = 0

    def get_explain_sql(self, sql: str) -> str:
        return f"EXPLAIN (FORMAT JSON, ANALYZE, BUFFERS) {sql}"

    def parse_plan(self, raw_plan: Any) -> PlanAnalysis:
        analysis = PlanAnalysis(raw_plan=raw_plan)

        if raw_plan is None:
            analysis.potential_problems.append("No execution plan available")
            return analysis

        try:
            plan_data = self._extract_plan_data(raw_plan)
            if plan_data:
                self._node_id_counter = 0
                analysis.plan_tree = self._build_plan_tree(plan_data)
                if analysis.plan_tree:
                    analysis.total_cost = analysis.plan_tree.total_cost
                    analysis.estimated_rows = analysis.plan_tree.rows
                    self._analyze_common_issues(analysis, analysis.plan_tree)
        except Exception as e:
            analysis.potential_problems.append(f"Error parsing execution plan: {str(e)}")

        return analysis

    def _extract_plan_data(self, raw_plan: Any) -> Dict[str, Any]:
        if isinstance(raw_plan, list) and len(raw_plan) > 0:
            plan = raw_plan[0]
            if isinstance(plan, dict):
                return plan.get("Plan", plan)
        elif isinstance(raw_plan, dict):
            return raw_plan.get("Plan", raw_plan)
        elif isinstance(raw_plan, str):
            try:
                parsed = json.loads(raw_plan)
                if isinstance(parsed, list) and len(parsed) > 0:
                    return parsed[0].get("Plan", parsed[0])
                return parsed.get("Plan", parsed)
            except:
                pass
        return {}

    def _build_plan_tree(self, plan_data: Dict[str, Any], parent: PlanNode = None) -> PlanNode:
        self._node_id_counter += 1
        node_id = self._node_id_counter

        operation = plan_data.get("Node Type", "UNKNOWN")
        table_name = plan_data.get("Relation Name", "")
        scan_type = plan_data.get("Node Type", "") if "Scan" in operation else ""

        node = PlanNode(
            id=node_id,
            operation=operation.upper(),
            table_name=table_name,
            scan_type=scan_type,
            rows=plan_data.get("Plan Rows", 0),
            cost=plan_data.get("Startup Cost", 0.0),
            total_cost=plan_data.get("Total Cost", 0.0),
            width=plan_data.get("Plan Width", 0),
            condition=self._extract_condition(plan_data),
            index_name=plan_data.get("Index Name", ""),
            extra=self._extract_extra(plan_data),
            parent=parent,
        )

        if operation == "Sort":
            node.extra = "Using filesort"
        elif operation == "HashAggregate" or operation == "GroupAggregate":
            if plan_data.get("Group Key"):
                node.extra = "Using temporary"

        for child_data in plan_data.get("Plans", []):
            child_node = self._build_plan_tree(child_data, node)
            node.children.append(child_node)

        return node

    def _extract_condition(self, plan_data: Dict[str, Any]) -> str:
        conditions = []
        for key in ["Filter", "Index Cond", "Join Filter", "Hash Cond", "Merge Cond"]:
            if key in plan_data:
                conditions.append(f"{key}: {plan_data[key]}")
        return "; ".join(conditions)

    def _extract_extra(self, plan_data: Dict[str, Any]) -> str:
        extras = []
        if plan_data.get("Parallel Aware", False):
            extras.append("Parallel")
        if plan_data.get("Actual Rows"):
            extras.append(f"Actual Rows: {plan_data['Actual Rows']}")
        if plan_data.get("Actual Loops"):
            extras.append(f"Loops: {plan_data['Actual Loops']}")
        if plan_data.get("Buffers"):
            buffers = plan_data["Buffers"]
            if buffers.get("Shared Hit"):
                extras.append(f"Shared Hit: {buffers['Shared Hit']}")
            if buffers.get("Shared Read"):
                extras.append(f"Shared Read: {buffers['Shared Read']}")
        return "; ".join(extras)
