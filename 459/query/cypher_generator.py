from typing import List, Dict, Any
from kg.schema import RELATION_INTENT_MAP


class CypherGenerator:
    def __init__(self):
        self.relation_map = RELATION_INTENT_MAP

    def generate_single_hop(
        self,
        intent: str,
        entity_name: str,
        entity_type: str = None
    ) -> Dict[str, Any]:
        if intent not in self.relation_map:
            return {
                "cypher": None,
                "error": f"不支持的意图类型: {intent}"
            }

        relation_info = self.relation_map[intent]
        relation = relation_info["relation"]
        target_type = relation_info["target"]
        direction = relation_info["direction"]

        if direction == "out":
            cypher = f"""
            MATCH (n {{name: $entity_name}})-[r:{relation}]->(m:{target_type})
            RETURN m.name as result, m as node, type(r) as relation_type
            """
        else:
            cypher = f"""
            MATCH (n:{target_type})-[r:{relation}]->(m {{name: $entity_name}})
            RETURN n.name as result, n as node, type(r) as relation_type
            """

        return {
            "cypher": cypher,
            "parameters": {"entity_name": entity_name},
            "query_type": "single_hop",
            "entity": entity_name,
            "relation": relation,
            "target_type": target_type
        }

    def generate_multi_hop(
        self,
        start_entity: str,
        relations: List[str],
        max_hops: int = 3
    ) -> Dict[str, Any]:
        relation_pattern = "->".join([f"[r{i}:{r}]" for i, r in enumerate(relations)])
        relation_pattern = "-" + relation_pattern + "->"

        cypher = f"""
        MATCH path = (n {{name: $start_entity}}){relation_pattern}(m)
        RETURN 
            m.name as final_result,
            [node IN nodes(path) | node.name] as path_nodes,
            [rel IN relationships(path) | type(rel)] as path_relations,
            path
        LIMIT 20
        """

        return {
            "cypher": cypher,
            "parameters": {"start_entity": start_entity},
            "query_type": "multi_hop",
            "start_entity": start_entity,
            "relations": relations
        }

    def generate_variable_hop(
        self,
        start_entity: str,
        relation_type: str,
        min_hops: int = 1,
        max_hops: int = 3
    ) -> Dict[str, Any]:
        cypher = f"""
        MATCH path = (n {{name: $start_entity}})-[*{min_hops}..{max_hops}]-(m)
        WHERE ALL(r IN relationships(path) WHERE type(r) = '{relation_type}')
        RETURN 
            m.name as result,
            [node IN nodes(path) | node.name] as path_nodes,
            length(path) as hop_count,
            path
        LIMIT 20
        """

        return {
            "cypher": cypher,
            "parameters": {"start_entity": start_entity},
            "query_type": "variable_hop",
            "min_hops": min_hops,
            "max_hops": max_hops
        }

    def generate_fuzzy_match(
        self,
        search_term: str,
        entity_types: List[str] = None
    ) -> Dict[str, Any]:
        type_filter = ""
        if entity_types:
            type_str = " OR ".join([f"'{t}' IN labels(n)" for t in entity_types])
            type_filter = f"AND ({type_str})"

        cypher = f"""
        MATCH (n)
        WHERE toLower(n.name) CONTAINS toLower($search_term)
        {type_filter}
        RETURN 
            n.name as result,
            labels(n) as entity_types,
            n as node
        ORDER BY size(n.name) ASC
        LIMIT 10
        """

        return {
            "cypher": cypher,
            "parameters": {"search_term": search_term},
            "query_type": "fuzzy_match"
        }

    def generate_entity_details(
        self,
        entity_name: str
    ) -> Dict[str, Any]:
        cypher = f"""
        MATCH (n {{name: $entity_name}})
        OPTIONAL MATCH (n)-[r_out]->(out)
        OPTIONAL MATCH (in_n)-[r_in]->(n)
        RETURN 
            n,
            collect(DISTINCT {{relation: type(r_out), target: out.name}}) as outgoing_relations,
            collect(DISTINCT {{relation: type(r_in), source: in_n.name}}) as incoming_relations
        """

        return {
            "cypher": cypher,
            "parameters": {"entity_name": entity_name},
            "query_type": "entity_details"
        }

    def generate_path_between_entities(
        self,
        entity1: str,
        entity2: str,
        max_hops: int = 4
    ) -> Dict[str, Any]:
        cypher = f"""
        MATCH path = shortestPath(
            (n1 {{name: $entity1}})-[*1..{max_hops}]-(n2 {{name: $entity2}})
        )
        RETURN 
            [node IN nodes(path) | node.name] as path_nodes,
            [rel IN relationships(path) | type(rel)] as path_relations,
            length(path) as hop_count,
            path
        """

        return {
            "cypher": cypher,
            "parameters": {"entity1": entity1, "entity2": entity2},
            "query_type": "path_between"
        }

    def generate_complex_query(
        self,
        intent_chain: List[str],
        entities: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        if len(entities) == 0:
            return {"cypher": None, "error": "没有识别到实体"}

        start_entity = entities[0]["canonical_name"]
        relations = []

        for intent in intent_chain:
            if intent in self.relation_map:
                relations.append(self.relation_map[intent]["relation"])

        if not relations:
            return self.generate_entity_details(start_entity)

        if len(relations) == 1:
            return self.generate_single_hop(intent_chain[0], start_entity)
        else:
            return self.generate_multi_hop(start_entity, relations)
