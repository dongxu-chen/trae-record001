import json
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

from data.models import CompanyInput


@dataclass
class GraphNode:
    id: str
    label: str
    type: str
    properties: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.type,
            "properties": self.properties or {}
        }


@dataclass
class GraphEdge:
    source: str
    target: str
    relation: str
    weight: float = 1.0
    properties: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "relation": self.relation,
            "weight": self.weight,
            "properties": self.properties or {}
        }


@dataclass
class RelationGraph:
    nodes: List[GraphNode]
    edges: List[GraphEdge]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "statistics": self._get_statistics()
        }

    def _get_statistics(self) -> Dict[str, Any]:
        node_types = {}
        edge_types = {}
        for node in self.nodes:
            node_types[node.type] = node_types.get(node.type, 0) + 1
        for edge in self.edges:
            edge_types[edge.relation] = edge_types.get(edge.relation, 0) + 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_type_distribution": node_types,
            "edge_type_distribution": edge_types,
            "density": self._calculate_density(),
            "centrality": self._calculate_centrality()
        }

    def _calculate_density(self) -> float:
        n = len(self.nodes)
        if n < 2:
            return 0.0
        max_edges = n * (n - 1)
        return round(len(self.edges) / max_edges, 4)

    def _calculate_centrality(self) -> Dict[str, float]:
        connections = {}
        for edge in self.edges:
            connections[edge.source] = connections.get(edge.source, 0) + 1
            connections[edge.target] = connections.get(edge.target, 0) + 1

        centrality = {}
        n = len(self.nodes)
        for node_id, count in connections.items():
            centrality[node_id] = round(count / max(n - 1, 1), 4)

        return dict(sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:10])


def build_enterprise_graph(
    company: CompanyInput,
    max_depth: int = 2,
    include_types: List[str] = None
) -> RelationGraph:
    if include_types is None:
        include_types = ["shareholder", "executive", "supply_chain", "legal", "industry"]

    nodes: Dict[str, GraphNode] = {}
    edges: List[GraphEdge] = []

    company_id = company.business_info.company_id
    company_node = GraphNode(
        id=company_id,
        label=company.business_info.company_name,
        type="company",
        properties={
            "industry": company.business_info.industry,
            "registered_capital": company.business_info.registered_capital,
            "established_date": company.business_info.established_date,
            "operating_status": company.business_info.operating_status,
        }
    )
    nodes[company_id] = company_node

    if "shareholder" in include_types:
        _add_shareholder_relations(company, nodes, edges)

    if "executive" in include_types:
        _add_executive_relations(company, nodes, edges)

    if "industry" in include_types:
        _add_industry_relations(company, nodes, edges)

    if "supply_chain" in include_types:
        _add_supply_chain_relations(company, nodes, edges)

    if "legal" in include_types:
        _add_legal_relations(company, nodes, edges)

    graph = RelationGraph(nodes=list(nodes.values()), edges=edges)
    return graph


def _add_shareholder_relations(
    company: CompanyInput,
    nodes: Dict[str, GraphNode],
    edges: List[GraphEdge]
) -> None:
    company_id = company.business_info.company_id

    for idx, sh in enumerate(company.shareholders):
        sh_id = f"sh_{sh.shareholder_name.replace(' ', '_')}_{idx}"
        if sh_id not in nodes:
            sh_type = "institutional_shareholder" if sh.shareholder_type == "法人股东" else "individual_shareholder"
            nodes[sh_id] = GraphNode(
                id=sh_id,
                label=sh.shareholder_name,
                type=sh_type,
                properties={
                    "shareholder_type": sh.shareholder_type,
                }
            )

        edges.append(GraphEdge(
            source=sh_id,
            target=company_id,
            relation="holds_shares",
            weight=sh.share_ratio,
            properties={
                "share_ratio": sh.share_ratio,
                "shareholder_type": sh.shareholder_type,
            }
        ))


def _add_executive_relations(
    company: CompanyInput,
    nodes: Dict[str, GraphNode],
    edges: List[GraphEdge]
) -> None:
    company_id = company.business_info.company_id

    for idx, ex in enumerate(company.executives):
        ex_id = f"ex_{ex.name.replace(' ', '_')}_{idx}"
        if ex_id not in nodes:
            nodes[ex_id] = GraphNode(
                id=ex_id,
                label=ex.name,
                type="executive",
                properties={
                    "position": ex.position,
                    "tenure_years": ex.tenure_years,
                }
            )

        edges.append(GraphEdge(
            source=ex_id,
            target=company_id,
            relation="manages",
            weight=min(ex.tenure_years / 10, 1.0),
            properties={
                "position": ex.position,
                "tenure_years": ex.tenure_years,
            }
        ))


def _add_industry_relations(
    company: CompanyInput,
    nodes: Dict[str, GraphNode],
    edges: List[GraphEdge]
) -> None:
    company_id = company.business_info.company_id
    industry_id = f"industry_{company.business_info.industry}"

    if industry_id not in nodes:
        nodes[industry_id] = GraphNode(
            id=industry_id,
            label=company.business_info.industry,
            type="industry",
            properties={}
        )

    edges.append(GraphEdge(
        source=company_id,
        target=industry_id,
        relation="belongs_to_industry",
        weight=1.0,
        properties={}
    ))


def _add_supply_chain_relations(
    company: CompanyInput,
    nodes: Dict[str, GraphNode],
    edges: List[GraphEdge]
) -> None:
    company_id = company.business_info.company_id

    sample_suppliers = [
        ("供应商A", "原材料供应", 0.6),
        ("供应商B", "零部件供应", 0.4),
        ("客户A", "产品销售", 0.5),
        ("客户B", "服务提供", 0.3),
    ]

    for idx, (name, rel_type, strength) in enumerate(sample_suppliers):
        partner_id = f"partner_{name.replace(' ', '_')}_{idx}"
        if partner_id not in nodes:
            nodes[partner_id] = GraphNode(
                id=partner_id,
                label=name,
                type="supply_chain_partner",
                properties={
                    "relation_type": rel_type,
                }
            )

        is_supplier = "供应" in rel_type
        edges.append(GraphEdge(
            source=partner_id if is_supplier else company_id,
            target=company_id if is_supplier else partner_id,
            relation="supplies_to" if is_supplier else "sells_to",
            weight=strength,
            properties={
                "relation_type": rel_type,
                "strength": strength,
            }
        ))


def _add_legal_relations(
    company: CompanyInput,
    nodes: Dict[str, GraphNode],
    edges: List[GraphEdge]
) -> None:
    company_id = company.business_info.company_id
    jr = company.judicial_risk

    if jr.lawsuit_count > 0:
        legal_id = f"legal_{company_id}_lawsuits"
        if legal_id not in nodes:
            nodes[legal_id] = GraphNode(
                id=legal_id,
                label=f"诉讼关联",
                type="legal_entity",
                properties={
                    "lawsuit_count": jr.lawsuit_count,
                    "total_executed_amount": jr.total_executed_amount,
                }
            )

        edges.append(GraphEdge(
            source=company_id,
            target=legal_id,
            relation="has_litigation",
            weight=min(jr.lawsuit_count * 0.1, 1.0),
            properties={
                "lawsuit_count": jr.lawsuit_count,
                "executed_person_count": jr.executed_person_count,
            }
        ))


def export_graph_for_visualization(graph: RelationGraph, format: str = "json") -> Any:
    if format == "json":
        return graph.to_dict()
    elif format == "cytoscape":
        cy_elements = []
        for node in graph.nodes:
            cy_elements.append({
                "data": {
                    "id": node.id,
                    "label": node.label,
                    "type": node.type,
                    **node.properties
                }
            })
        for edge in graph.edges:
            cy_elements.append({
                "data": {
                    "id": f"{edge.source}-{edge.target}-{edge.relation}",
                    "source": edge.source,
                    "target": edge.target,
                    "relation": edge.relation,
                    "weight": edge.weight,
                    **edge.properties
                }
            })
        return {"elements": cy_elements}
    elif format == "graphviz":
        lines = ["digraph G {"]
        lines.append('  node [fontname="Microsoft YaHei"];')
        type_colors = {
            "company": "#3498db",
            "individual_shareholder": "#2ecc71",
            "institutional_shareholder": "#27ae60",
            "executive": "#e74c3c",
            "industry": "#9b59b6",
            "supply_chain_partner": "#f39c12",
            "legal_entity": "#e67e22",
        }
        for node in graph.nodes:
            color = type_colors.get(node.type, "#95a5a6")
            label = node.label.replace('"', '\\"')
            lines.append(f'  "{node.id}" [label="{label}", style=filled, fillcolor="{color}"];')
        for edge in graph.edges:
            label = edge.relation.replace('"', '\\"')
            lines.append(f'  "{edge.source}" -> "{edge.target}" [label="{label}", weight="{edge.weight}"];')
        lines.append("}")
        return "\n".join(lines)
    else:
        return graph.to_dict()


def get_graph_summary(graph: RelationGraph) -> Dict[str, Any]:
    summary = graph._get_statistics()
    summary["key_entities"] = []

    centrality = summary.get("centrality", {})
    for node_id, cent in list(centrality.items())[:5]:
        node = next((n for n in graph.nodes if n.id == node_id), None)
        if node:
            summary["key_entities"].append({
                "id": node_id,
                "label": node.label,
                "type": node.type,
                "centrality": cent,
            })

    high_risk_edges = [
        e for e in graph.edges
        if e.relation in ["has_litigation", "has_legal_relation"]
    ]
    summary["high_risk_relations_count"] = len(high_risk_edges)

    return summary
