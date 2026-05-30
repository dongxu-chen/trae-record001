from typing import List, Dict, Any, Optional
import logging
from kg.neo4j_client import Neo4jClient
from kg.schema import ENTITY_TYPES, RELATION_TYPES

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ENTITY_COLORS = {
    "Disease": "#e74c3c",
    "Symptom": "#f39c12",
    "Drug": "#2ecc71",
    "Department": "#3498db",
    "Doctor": "#9b59b6",
    "Hospital": "#1abc9c",
    "Treatment": "#e67e22",
    "Examination": "#34495e",
}

ENTITY_ICONS = {
    "Disease": "🦠",
    "Symptom": "🤒",
    "Drug": "💊",
    "Department": "🏥",
    "Doctor": "👨‍⚕️",
    "Hospital": "🏢",
    "Treatment": "💉",
    "Examination": "🔬",
}


class GraphVisualizer:
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j_client = neo4j_client

    def get_subgraph(
        self,
        center_entity: str,
        depth: int = 2,
        limit: int = 50
    ) -> Dict[str, Any]:
        logger.info(f"获取子图: center={center_entity}, depth={depth}")

        nodes = {}
        edges = []

        query = f"""
        MATCH path = (center {{name: $center_name}})-[*1..{depth}]-(neighbor)
        RETURN
            [node IN nodes(path) | {{name: node.name, labels: labels(node), properties: properties(node)}}] as path_nodes,
            [rel IN relationships(path) | {{
                start: startNode(rel).name,
                end: endNode(rel).name,
                type: type(rel),
                properties: properties(rel)
            }}] as path_edges
        LIMIT {limit}
        """
        results = self.neo4j_client.execute_query(query, {"center_name": center_entity})

        for result in results:
            for node in result.get("path_nodes", []):
                name = node.get("name")
                if name and name not in nodes:
                    primary_label = node.get("labels", ["Unknown"])[0] if node.get("labels") else "Unknown"
                    nodes[name] = {
                        "id": name,
                        "label": name,
                        "type": primary_label,
                        "type_label": ENTITY_TYPES.get(primary_label, primary_label),
                        "color": ENTITY_COLORS.get(primary_label, "#95a5a6"),
                        "icon": ENTITY_ICONS.get(primary_label, "●"),
                        "properties": node.get("properties", {}),
                        "size": 30 if name == center_entity else 20,
                        "highlighted": False
                    }

            for edge in result.get("path_edges", []):
                edge_key = f"{edge['start']}-{edge['type']}-{edge['end']}"
                if not any(e["id"] == edge_key for e in edges):
                    edges.append({
                        "id": edge_key,
                        "source": edge["start"],
                        "target": edge["end"],
                        "relation": edge["type"],
                        "relation_label": RELATION_TYPES.get(edge["type"], edge["type"]),
                        "properties": edge.get("properties", {}),
                        "highlighted": False
                    })

        if center_entity not in nodes:
            center_query = """
            MATCH (n {name: $name})
            RETURN n.name as name, labels(n) as labels, properties(n) as properties
            LIMIT 1
            """
            center_result = self.neo4j_client.execute_query(center_query, {"name": center_entity})
            if center_result:
                r = center_result[0]
                primary_label = r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown"
                nodes[center_entity] = {
                    "id": center_entity,
                    "label": center_entity,
                    "type": primary_label,
                    "type_label": ENTITY_TYPES.get(primary_label, primary_label),
                    "color": ENTITY_COLORS.get(primary_label, "#95a5a6"),
                    "icon": ENTITY_ICONS.get(primary_label, "●"),
                    "properties": r.get("properties", {}),
                    "size": 40,
                    "highlighted": False
                }

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "center": center_entity,
            "depth": depth,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }

    def get_full_graph(self, limit: int = 200) -> Dict[str, Any]:
        logger.info(f"获取全图, limit={limit}")

        nodes = {}
        edges = []

        query = f"""
        MATCH (n)
        RETURN n.name as name, labels(n) as labels, properties(n) as properties
        LIMIT {limit}
        """
        node_results = self.neo4j_client.execute_query(query)

        for r in node_results:
            name = r.get("name")
            if name:
                primary_label = r.get("labels", ["Unknown"])[0] if r.get("labels") else "Unknown"
                nodes[name] = {
                    "id": name,
                    "label": name,
                    "type": primary_label,
                    "type_label": ENTITY_TYPES.get(primary_label, primary_label),
                    "color": ENTITY_COLORS.get(primary_label, "#95a5a6"),
                    "icon": ENTITY_ICONS.get(primary_label, "●"),
                    "properties": r.get("properties", {}),
                    "size": 20,
                    "highlighted": False
                }

        edge_query = f"""
        MATCH (a)-[r]->(b)
        RETURN a.name as start, b.name as end, type(r) as rel_type, properties(r) as rel_props
        LIMIT {limit * 2}
        """
        edge_results = self.neo4j_client.execute_query(edge_query)

        for r in edge_results:
            edge_key = f"{r['start']}-{r['rel_type']}-{r['end']}"
            edges.append({
                "id": edge_key,
                "source": r["start"],
                "target": r["end"],
                "relation": r["rel_type"],
                "relation_label": RELATION_TYPES.get(r["rel_type"], r["rel_type"]),
                "properties": r.get("rel_props", {}),
                "highlighted": False
            })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }

    def highlight_answer_path(
        self,
        graph_data: Dict[str, Any],
        path_nodes: List[str],
        path_relations: List[str] = None
    ) -> Dict[str, Any]:
        logger.info(f"高亮路径: {path_nodes}")

        highlighted_nodes = {name: False for name in path_nodes}
        highlighted_edges = set()

        for node in graph_data["nodes"]:
            if node["id"] in path_nodes:
                node["highlighted"] = True
                node["size"] = 40
                idx = path_nodes.index(node["id"])
                node["path_order"] = idx
                highlighted_nodes[node["id"]] = True

        for edge in graph_data["edges"]:
            src_in_path = edge["source"] in path_nodes
            tgt_in_path = edge["target"] in path_nodes
            if src_in_path and tgt_in_path:
                src_idx = path_nodes.index(edge["source"])
                tgt_idx = path_nodes.index(edge["target"])
                if abs(src_idx - tgt_idx) == 1:
                    edge["highlighted"] = True
                    if path_relations:
                        for rel in path_relations:
                            if rel == edge["relation"]:
                                edge["highlighted"] = True
                                break
                    highlighted_edges.add(edge["id"])

        graph_data["path_info"] = {
            "path_nodes": path_nodes,
            "path_relations": path_relations or [],
            "highlighted_node_count": sum(1 for v in highlighted_nodes.values() if v),
            "highlighted_edge_count": len(highlighted_edges)
        }

        return graph_data

    def get_visualization_with_answer(
        self,
        center_entity: str,
        answer_result: Dict[str, Any],
        depth: int = 2
    ) -> Dict[str, Any]:
        graph_data = self.get_subgraph(center_entity, depth)

        source = answer_result.get("source", {})
        path_nodes = []
        path_relations = []

        if source:
            source_type = source.get("type", "")

            if source_type == "single_hop":
                path_nodes = [source.get("query_entity", center_entity)]
                for tup in source.get("evidence_tuples", []):
                    path_nodes.append(tup.get("target", ""))
                path_relations = [source.get("query_relation", "")]

            elif source_type == "multi_hop":
                for path_info in source.get("paths", []):
                    pn = path_info.get("path_nodes", [])
                    pr = path_info.get("path_relations", [])
                    if len(pn) > len(path_nodes):
                        path_nodes = pn
                        path_relations = pr

            elif source_type == "path_between":
                for path_info in source.get("paths", []):
                    pn = path_info.get("path_nodes", [])
                    pr = path_info.get("path_relations", [])
                    if len(pn) > len(path_nodes):
                        path_nodes = pn
                        path_relations = pr

            elif source_type == "entity_details":
                path_nodes = [source.get("entity", center_entity)]
                for rel in source.get("outgoing_relations", []):
                    path_nodes.append(rel.get("target", ""))
                    path_relations.append(rel.get("relation", ""))
                for rel in source.get("incoming_relations", []):
                    path_nodes.insert(0, rel.get("source", ""))
                    path_relations.insert(0, rel.get("relation", ""))

        if path_nodes:
            graph_data = self.highlight_answer_path(graph_data, path_nodes, path_relations)

        graph_data["answer_text"] = answer_result.get("answer", "")
        graph_data["has_answer"] = answer_result.get("has_answer", False)

        return graph_data

    def get_entity_neighborhood(
        self,
        entity_name: str,
        relation_filter: str = None,
        direction: str = "both"
    ) -> Dict[str, Any]:
        if direction == "out":
            dir_pattern = "->"
        elif direction == "in":
            dir_pattern = "<-"
        else:
            dir_pattern = "-"

        rel_filter = f":{relation_filter}" if relation_filter else ""

        query = f"""
        MATCH (center {{name: $name}})-[r{rel_filter}]{dir_pattern}(neighbor)
        RETURN
            center.name as center_name,
            labels(center) as center_labels,
            neighbor.name as neighbor_name,
            labels(neighbor) as neighbor_labels,
            type(r) as rel_type,
            properties(center) as center_props,
            properties(neighbor) as neighbor_props
        """
        results = self.neo4j_client.execute_query(query, {"name": entity_name})

        nodes = {}
        edges = []

        for r in results:
            cn = r.get("center_name")
            nn = r.get("neighbor_name")
            if cn and cn not in nodes:
                cl = r.get("center_labels", ["Unknown"])[0]
                nodes[cn] = {
                    "id": cn, "label": cn, "type": cl,
                    "type_label": ENTITY_TYPES.get(cl, cl),
                    "color": ENTITY_COLORS.get(cl, "#95a5a6"),
                    "icon": ENTITY_ICONS.get(cl, "●"),
                    "properties": r.get("center_props", {}),
                    "size": 35, "highlighted": True
                }
            if nn and nn not in nodes:
                nl = r.get("neighbor_labels", ["Unknown"])[0]
                nodes[nn] = {
                    "id": nn, "label": nn, "type": nl,
                    "type_label": ENTITY_TYPES.get(nl, nl),
                    "color": ENTITY_COLORS.get(nl, "#95a5a6"),
                    "icon": ENTITY_ICONS.get(nl, "●"),
                    "properties": r.get("neighbor_props", {}),
                    "size": 20, "highlighted": False
                }
            if cn and nn:
                edge_key = f"{cn}-{r['rel_type']}-{nn}"
                edges.append({
                    "id": edge_key, "source": cn, "target": nn,
                    "relation": r["rel_type"],
                    "relation_label": RELATION_TYPES.get(r["rel_type"], r["rel_type"]),
                    "highlighted": True
                })

        return {
            "nodes": list(nodes.values()),
            "edges": edges,
            "center": entity_name,
            "total_nodes": len(nodes),
            "total_edges": len(edges)
        }
