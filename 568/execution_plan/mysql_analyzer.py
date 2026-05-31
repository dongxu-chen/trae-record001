from typing import List, Dict, Any
import json
from .analyzer import ExecutionPlanAnalyzer, PlanAnalysis, PlanNode


class MySQLExecutionPlanAnalyzer(ExecutionPlanAnalyzer):
    def __init__(self):
        super().__init__("mysql")
        self._node_id_counter = 0

    def get_explain_sql(self, sql: str) -> str:
        return f"EXPLAIN FORMAT=JSON {sql}"

    def parse_plan(self, raw_plan: Any) -> PlanAnalysis:
        analysis = PlanAnalysis(raw_plan=raw_plan)

        if raw_plan is None:
            analysis.potential_problems.append("No execution plan available")
            return analysis

        try:
            plan_data = self._extract_plan_data(raw_plan)
            if plan_data:
                analysis.plan_tree = self._build_plan_tree(plan_data)
                if analysis.plan_tree:
                    analysis.total_cost = self._extract_total_cost(plan_data)
                    analysis.estimated_rows = analysis.plan_tree.rows
                    self._analyze_common_issues(analysis, analysis.plan_tree)
        except Exception as e:
            analysis.potential_problems.append(f"Error parsing execution plan: {str(e)}")

        return analysis

    def _extract_plan_data(self, raw_plan: Any) -> Dict[str, Any]:
        if isinstance(raw_plan, dict):
            return raw_plan.get("query_block", raw_plan)
        elif isinstance(raw_plan, list) and len(raw_plan) > 0:
            if isinstance(raw_plan[0], dict):
                if "EXPLAIN" in raw_plan[0]:
                    plan_json = raw_plan[0]["EXPLAIN"]
                    if isinstance(plan_json, str):
                        return json.loads(plan_json).get("query_block", {})
                    return plan_json.get("query_block", {})
        elif isinstance(raw_plan, str):
            try:
                return json.loads(raw_plan).get("query_block", {})
            except:
                pass
        return {}

    def _build_plan_tree(self, plan_data: Dict[str, Any], parent: PlanNode = None) -> PlanNode:
        self._node_id_counter += 1
        node_id = self._node_id_counter

        operation = plan_data.get("access_type", "UNKNOWN")
        table_name = plan_data.get("table_name", "")
        scan_type = plan_data.get("access_type", "")

        node = PlanNode(
            id=node_id,
            operation=operation.upper(),
            table_name=table_name,
            scan_type=scan_type,
            rows=plan_data.get("rows", 0),
            cost=plan_data.get("cost", 0.0),
            total_cost=plan_data.get("total_cost", 0.0),
            condition=plan_data.get("condition", ""),
            index_name=plan_data.get("key", "") or plan_data.get("used_key_parts", ""),
            extra=plan_data.get("extra", ""),
            parent=parent,
        )

        for nested_block in plan_data.get("nested_loop", []):
            for table_data in nested_block.get("table", []):
                child_node = self._build_plan_tree(table_data, node)
                node.children.append(child_node)

        for subquery_data in plan_data.get("subqueries", []):
            subquery_node = self._build_plan_tree(subquery_data, node)
            node.children.append(subquery_node)

        if "ordering_operation" in plan_data:
            self._node_id_counter += 1
            sort_node = PlanNode(
                id=self._node_id_counter,
                operation="FILESORT",
                extra="Using filesort",
                parent=node,
            )
            node.children.append(sort_node)

        if "duplicates_removal" in plan_data or "grouping_operation" in plan_data:
            self._node_id_counter += 1
            temp_node = PlanNode(
                id=self._node_id_counter,
                operation="TEMPORARY",
                extra="Using temporary",
                parent=node,
            )
            node.children.append(temp_node)

        return node

    def _extract_total_cost(self, plan_data: Dict[str, Any]) -> float:
        total_cost = plan_data.get("total_cost", 0.0)
        if total_cost == 0.0:
            cost = plan_data.get("cost", 0.0)
            if cost:
                total_cost = cost
        return float(total_cost)
