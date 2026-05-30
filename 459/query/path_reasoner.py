from typing import List, Dict, Any, Optional, Tuple
import logging
from kg.neo4j_client import Neo4jClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PathReasoner:
    def __init__(self, neo4j_client: Neo4jClient):
        self.neo4j_client = neo4j_client

    def path_completion(
        self,
        start_entity: str,
        end_entity: str,
        max_hops: int = 5,
        known_intermediates: List[str] = None
    ) -> Dict[str, Any]:
        logger.info(f"路径补全: {start_entity} -> {end_entity}")

        direct_path = self._find_direct_path(start_entity, end_entity, max_hops)
        if direct_path:
            return {
                "status": "complete",
                "path_found": True,
                "paths": direct_path,
                "completion_needed": False,
                "message": "找到直接路径"
            }

        logger.info("未找到直接路径，开始路径补全...")

        bridge_nodes = self._find_bridge_nodes(start_entity, end_entity, known_intermediates)

        if bridge_nodes:
            completed_paths = self._build_bridge_paths(start_entity, end_entity, bridge_nodes, max_hops)
            if completed_paths:
                return {
                    "status": "completed_by_bridge",
                    "path_found": True,
                    "paths": completed_paths,
                    "completion_needed": True,
                    "bridge_nodes": bridge_nodes,
                    "message": f"通过桥接节点补全路径: {', '.join(bridge_nodes)}"
                }

        return {
            "status": "no_path",
            "path_found": False,
            "paths": [],
            "completion_needed": True,
            "message": "无法找到连接路径，节点间可能不存在关联"
        }

    def missing_node_hop_query(
        self,
        start_entity: str,
        target_relation: str = None,
        target_entity_type: str = None,
        max_hops: int = 4,
        skip_nodes: List[str] = None
    ) -> Dict[str, Any]:
        logger.info(f"缺失节点跳跃查询: start={start_entity}, relation={target_relation}, target_type={target_entity_type}")

        start_info = self._get_entity_info(start_entity)
        if not start_info:
            return {
                "status": "entity_not_found",
                "results": [],
                "message": f"未找到起始实体: {start_entity}"
            }

        if target_relation and target_entity_type:
            query = f"""
            MATCH path = (n {{name: $start_entity}})-[*1..{max_hops}]-(m:{target_entity_type})
            WHERE ANY(r IN relationships(path) WHERE type(r) = '{target_relation}')
            RETURN 
                m.name as result,
                m as node,
                [node2 IN nodes(path) | node2.name] as path_nodes,
                [r IN relationships(path) | type(r)] as path_relations,
                length(path) as hop_count
            ORDER BY hop_count ASC
            LIMIT 15
            """
        elif target_relation:
            query = f"""
            MATCH path = (n {{name: $start_entity}})-[*1..{max_hops}]-(m)
            WHERE ANY(r IN relationships(path) WHERE type(r) = '{target_relation}')
            RETURN 
                m.name as result,
                m as node,
                [node2 IN nodes(path) | node2.name] as path_nodes,
                [r IN relationships(path) | type(r)] as path_relations,
                length(path) as hop_count
            ORDER BY hop_count ASC
            LIMIT 15
            """
        elif target_entity_type:
            query = f"""
            MATCH path = (n {{name: $start_entity}})-[*1..{max_hops}]-(m:{target_entity_type})
            RETURN 
                m.name as result,
                m as node,
                [node2 IN nodes(path) | node2.name] as path_nodes,
                [r IN relationships(path) | type(r)] as path_relations,
                length(path) as hop_count
            ORDER BY hop_count ASC
            LIMIT 15
            """
        else:
            query = f"""
            MATCH path = (n {{name: $start_entity}})-[*1..{max_hops}]-(m)
            WHERE m.name <> $start_entity
            RETURN 
                m.name as result,
                labels(m) as entity_types,
                [node2 IN nodes(path) | node2.name] as path_nodes,
                [r IN relationships(path) | type(r)] as path_relations,
                length(path) as hop_count
            ORDER BY hop_count ASC
            LIMIT 20
            """

        results = self.neo4j_client.execute_query(query, {"start_entity": start_entity})

        if skip_nodes:
            results = [r for r in results if r.get("result") not in skip_nodes]

        if results:
            return {
                "status": "success",
                "start_entity": start_entity,
                "results": results,
                "hop_distribution": self._compute_hop_distribution(results),
                "message": f"通过跳跃查询找到 {len(results)} 个相关实体"
            }

        return {
            "status": "no_results",
            "start_entity": start_entity,
            "results": [],
            "message": "未找到相关实体"
        }

    def multi_hop_with_completion(
        self,
        start_entity: str,
        relation_chain: List[str],
        max_hops: int = 4
    ) -> Dict[str, Any]:
        logger.info(f"多跳推理(含补全): start={start_entity}, relations={relation_chain}")

        strict_result = self._strict_multi_hop(start_entity, relation_chain)
        if strict_result:
            return {
                "status": "strict_match",
                "results": strict_result,
                "completion_used": False,
                "message": "严格多跳匹配成功"
            }

        logger.info("严格匹配未找到结果，尝试路径补全...")
        relaxed_result = self._relaxed_multi_hop(start_entity, relation_chain, max_hops)

        if relaxed_result:
            return {
                "status": "relaxed_match",
                "results": relaxed_result,
                "completion_used": True,
                "message": "通过放宽条件补全路径"
            }

        return self._fallback_exploration(start_entity, relation_chain)

    def find_all_paths_between(
        self,
        entity1: str,
        entity2: str,
        max_hops: int = 5,
        limit: int = 5
    ) -> Dict[str, Any]:
        query = f"""
        MATCH path = (n1 {{name: $entity1}})-[*1..{max_hops}]-(n2 {{name: $entity2}})
        RETURN 
            [node IN nodes(path) | node.name] as path_nodes,
            [rel IN relationships(path) | type(rel)] as path_relations,
            length(path) as hop_count,
            [node IN nodes(path) | labels(node)] as node_types
        ORDER BY hop_count ASC
        LIMIT {limit}
        """
        results = self.neo4j_client.execute_query(query, {"entity1": entity1, "entity2": entity2})

        return {
            "entity1": entity1,
            "entity2": entity2,
            "paths": results,
            "total_paths": len(results),
            "shortest_hop": min((r["hop_count"] for r in results), default=0)
        }

    def _find_direct_path(self, start: str, end: str, max_hops: int) -> List[Dict]:
        query = f"""
        MATCH path = shortestPath(
            (n1 {{name: $entity1}})-[*1..{max_hops}]-(n2 {{name: $entity2}})
        )
        RETURN 
            [node IN nodes(path) | node.name] as path_nodes,
            [rel IN relationships(path) | type(rel)] as path_relations,
            length(path) as hop_count
        """
        return self.neo4j_client.execute_query(query, {"entity1": start, "entity2": end})

    def _find_bridge_nodes(
        self,
        start: str,
        end: str,
        known_intermediates: List[str] = None
    ) -> List[str]:
        bridge_nodes = []

        if known_intermediates:
            for node_name in known_intermediates:
                to_start = self._find_direct_path(start, node_name, 3)
                to_end = self._find_direct_path(node_name, end, 3)
                if to_start and to_end:
                    bridge_nodes.append(node_name)

        if not bridge_nodes:
            query = """
            MATCH (n1 {name: $entity1})-[*1..2]-(bridge)-[*1..2]-(n2 {name: $entity2})
            WHERE bridge.name <> $entity1 AND bridge.name <> $entity2
            RETURN DISTINCT bridge.name as bridge_node, labels(bridge) as bridge_type
            LIMIT 5
            """
            results = self.neo4j_client.execute_query(
                query, {"entity1": start, "entity2": end}
            )
            bridge_nodes = [r["bridge_node"] for r in results]

        if not bridge_nodes:
            bridge_nodes = self._find_type_based_bridges(start, end)

        return bridge_nodes

    def _find_type_based_bridges(self, start: str, end: str) -> List[str]:
        start_info = self._get_entity_info(start)
        end_info = self._get_entity_info(end)

        if not start_info or not end_info:
            return []

        query = """
        MATCH (n1 {name: $entity1})-[r1]-(bridge)-[r2]-(n2 {name: $entity2})
        WHERE bridge.name <> $entity1 AND bridge.name <> $entity2
        RETURN DISTINCT bridge.name as bridge_node, labels(bridge) as bridge_type,
               type(r1) as rel_from_start, type(r2) as rel_to_end
        LIMIT 5
        """
        results = self.neo4j_client.execute_query(
            query, {"entity1": start, "entity2": end}
        )

        if results:
            return [r["bridge_node"] for r in results]

        start_neighbors_query = """
        MATCH (n1 {name: $entity1})-[r]-(neighbor)
        RETURN DISTINCT neighbor.name as neighbor_name
        LIMIT 20
        """
        start_neighbors = self.neo4j_client.execute_query(
            start_neighbors_query, {"entity1": start}
        )

        end_neighbors_query = """
        MATCH (n2 {name: $entity2})-[r]-(neighbor)
        RETURN DISTINCT neighbor.name as neighbor_name
        LIMIT 20
        """
        end_neighbors = self.neo4j_client.execute_query(
            end_neighbors_query, {"entity2": end}
        )

        start_set = {r["neighbor_name"] for r in start_neighbors}
        end_set = {r["neighbor_name"] for r in end_neighbors}
        common = start_set & end_set

        return list(common)[:5]

    def _build_bridge_paths(
        self,
        start: str,
        end: str,
        bridge_nodes: List[str],
        max_hops: int
    ) -> List[Dict]:
        all_paths = []

        for bridge in bridge_nodes:
            path_to_bridge = self._find_direct_path(start, bridge, max_hops // 2 + 1)
            path_from_bridge = self._find_direct_path(bridge, end, max_hops // 2 + 1)

            if path_to_bridge and path_from_bridge:
                combined = {
                    "path_nodes": path_to_bridge[0]["path_nodes"] + path_from_bridge[0]["path_nodes"][1:],
                    "path_relations": path_to_bridge[0]["path_relations"] + path_from_bridge[0]["path_relations"],
                    "hop_count": path_to_bridge[0]["hop_count"] + path_from_bridge[0]["hop_count"],
                    "bridge_node": bridge,
                    "completion_type": "bridge"
                }
                all_paths.append(combined)

        return all_paths

    def _strict_multi_hop(self, start: str, relation_chain: List[str]) -> List[Dict]:
        relation_pattern = "->".join([f"[r{i}:{r}]" for i, r in enumerate(relation_chain)])
        relation_pattern = "-" + relation_pattern + "->"

        query = f"""
        MATCH path = (n {{name: $start_entity}}){relation_pattern}(m)
        RETURN 
            m.name as result,
            [node IN nodes(path) | node.name] as path_nodes,
            [rel IN relationships(path) | type(rel)] as path_relations
        LIMIT 20
        """
        return self.neo4j_client.execute_query(query, {"start_entity": start})

    def _relaxed_multi_hop(self, start: str, relation_chain: List[str], max_hops: int) -> List[Dict]:
        if len(relation_chain) >= 2:
            for skip_idx in range(len(relation_chain)):
                reduced = [r for i, r in enumerate(relation_chain) if i != skip_idx]
                result = self._strict_multi_hop(start, reduced)
                if result:
                    for r in result:
                        r["skipped_relation"] = relation_chain[skip_idx]
                        r["completion_type"] = "relation_skip"
                    return result

        query = f"""
        MATCH path = (n {{name: $start_entity}})-[*1..{max_hops}]-(m)
        WHERE ANY(r IN relationships(path) WHERE type(r) IN {str(relation_chain).replace("'", '"')})
        RETURN 
            m.name as result,
            [node IN nodes(path) | node.name] as path_nodes,
            [rel IN relationships(path) | type(rel)] as path_relations,
            length(path) as hop_count
        ORDER BY hop_count ASC
        LIMIT 15
        """
        results = self.neo4j_client.execute_query(query, {"start_entity": start})
        for r in results:
            r["completion_type"] = "any_relation_match"
        return results

    def _fallback_exploration(self, start: str, relation_chain: List[str]) -> Dict[str, Any]:
        logger.info("多跳推理回退到邻居探索")

        query = """
        MATCH (n {name: $start_entity})-[r]-(neighbor)
        RETURN 
            neighbor.name as result,
            type(r) as relation_type,
            labels(neighbor) as neighbor_types
        LIMIT 10
        """
        results = self.neo4j_client.execute_query(query, {"start_entity": start})

        target_relations = set(relation_chain)
        priority_results = [r for r in results if r.get("relation_type") in target_relations]
        other_results = [r for r in results if r.get("relation_type") not in target_relations]

        return {
            "status": "fallback_exploration",
            "results": priority_results + other_results,
            "completion_used": True,
            "message": "严格多跳匹配失败，返回邻居探索结果"
        }

    def _get_entity_info(self, entity_name: str) -> Optional[Dict]:
        query = """
        MATCH (n {name: $name})
        RETURN n.name as name, labels(n) as types, properties(n) as props
        LIMIT 1
        """
        results = self.neo4j_client.execute_query(query, {"name": entity_name})
        return results[0] if results else None

    def _compute_hop_distribution(self, results: List[Dict]) -> Dict[int, int]:
        dist = {}
        for r in results:
            hop = r.get("hop_count", 0)
            dist[hop] = dist.get(hop, 0) + 1
        return dist
