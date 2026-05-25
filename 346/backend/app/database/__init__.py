from neo4j import GraphDatabase, Driver, Session
from typing import List, Dict, Any, Optional
from app.models import Node, Edge, GraphData

class Neo4jDatabase:
    def __init__(self, uri: str, user: str, password: str):
        self._driver: Optional[Driver] = GraphDatabase.driver(uri, auth=(user, password))
    
    def close(self):
        if self._driver:
            self._driver.close()
    
    def test_connection(self) -> bool:
        try:
            with self._driver.session() as session:
                result = session.run("RETURN 1 AS test")
                return result.single() is not None
        except Exception:
            return False
    
    def get_all_graph_data(self, limit: int = 1000) -> GraphData:
        with self._driver.session() as session:
            result = session.run("""
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->(m)
                RETURN n, r, m
                LIMIT $limit
            """, limit=limit)
            
            nodes_dict: Dict[str, Node] = {}
            edges_dict: Dict[str, Edge] = {}
            
            for record in result:
                n = record['n']
                if n and n.id not in nodes_dict:
                    nodes_dict[str(n.id)] = Node(
                        id=str(n.id),
                        label=list(n.labels)[0] if n.labels else 'Node',
                        properties=dict(n)
                    )
                
                r = record['r']
                m = record['m']
                if r and m:
                    edge_key = f"{r.start_node.id}-{r.end_node.id}-{r.type}"
                    if edge_key not in edges_dict:
                        edges_dict[edge_key] = Edge(
                            source=str(r.start_node.id),
                            target=str(r.end_node.id),
                            relationship_type=r.type,
                            properties=dict(r)
                        )
            
            return GraphData(nodes=list(nodes_dict.values()), edges=list(edges_dict.values()))
    
    def get_nodes_by_label(self, label: str) -> List[Node]:
        with self._driver.session() as session:
            result = session.run(f"MATCH (n:`{label}`) RETURN n")
            nodes = []
            for record in result:
                n = record['n']
                nodes.append(Node(
                    id=str(n.id),
                    label=list(n.labels)[0],
                    properties=dict(n)
                ))
            return nodes
    
    def create_node(self, node: Node) -> Node:
        with self._driver.session() as session:
            props_str = ', '.join([f"{k}: ${k}" for k in node.properties.keys()])
            query = f"""
                CREATE (n:`{node.label}` {{{props_str}}})
                RETURN n, id(n) as node_id
            """
            result = session.run(query, **node.properties)
            record = result.single()
            created_node = record['n']
            return Node(
                id=str(record['node_id']),
                label=list(created_node.labels)[0],
                properties=dict(created_node)
            )
    
    def create_edge(self, edge: Edge) -> Edge:
        with self._driver.session() as session:
            props_str = ', '.join([f"{k}: ${k}" for k in edge.properties.keys()])
            query = f"""
                MATCH (a), (b)
                WHERE id(a) = $source_id AND id(b) = $target_id
                CREATE (a)-[r:`{edge.relationship_type}` {{{props_str}}}]->(b)
                RETURN r
            """
            result = session.run(query, 
                               source_id=int(edge.source), 
                               target_id=int(edge.target),
                               **edge.properties)
            created_edge = result.single()['r']
            return Edge(
                source=str(created_edge.start_node.id),
                target=str(created_edge.end_node.id),
                relationship_type=created_edge.type,
                properties=dict(created_edge)
            )
    
    def clear_database(self):
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
    
    def import_data(self, graph_data: GraphData):
        with self._driver.session() as session:
            for node in graph_data.nodes:
                self.create_node(node)
            
            for edge in graph_data.edges:
                self.create_edge(edge)
    
    def get_neighbors(self, node_id: str) -> List[Node]:
        with self._driver.session() as session:
            result = session.run("""
                MATCH (n)-[]->(neighbor) WHERE id(n) = $node_id RETURN neighbor
                UNION
                MATCH (neighbor)-[]->(n) WHERE id(n) = $node_id RETURN neighbor
            """, node_id=int(node_id))
            
            nodes = []
            for record in result:
                n = record['neighbor']
                nodes.append(Node(
                    id=str(n.id),
                    label=list(n.labels)[0],
                    properties=dict(n)
                ))
            return nodes
    
    def delete_node(self, node_id: str):
        with self._driver.session() as session:
            session.run("MATCH (n) WHERE id(n) = $node_id DETACH DELETE n", 
                       node_id=int(node_id))
    
    def get_graph_data_with_filters(
        self,
        relationship_types: Optional[List[str]] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 1000
    ) -> GraphData:
        with self._driver.session() as session:
            where_clauses = []
            params = {'limit': limit}
            
            if relationship_types:
                rel_types_str = '|'.join([f'`{rt}`' for rt in relationship_types])
                where_clauses.append(f"type(r) IN $relationship_types")
                params['relationship_types'] = relationship_types
            
            if start_time is not None:
                where_clauses.append("r.timestamp >= $start_time")
                params['start_time'] = start_time
            
            if end_time is not None:
                where_clauses.append("r.timestamp <= $end_time")
                params['end_time'] = end_time
            
            where_str = ""
            if where_clauses:
                where_str = "WHERE " + " AND ".join(where_clauses)
            
            query = f"""
                MATCH (n)
                OPTIONAL MATCH (n)-[r]->(m)
                {where_str}
                RETURN n, r, m
                LIMIT $limit
            """
            
            result = session.run(query, **params)
            
            nodes_dict: Dict[str, Node] = {}
            edges_dict: Dict[str, Edge] = {}
            
            for record in result:
                n = record['n']
                if n and n.id not in nodes_dict:
                    nodes_dict[str(n.id)] = Node(
                        id=str(n.id),
                        label=list(n.labels)[0] if n.labels else 'Node',
                        properties=dict(n)
                    )
                
                r = record['r']
                m = record['m']
                if r and m:
                    edge_key = f"{r.start_node.id}-{r.end_node.id}-{r.type}"
                    if edge_key not in edges_dict:
                        edges_dict[edge_key] = Edge(
                            source=str(r.start_node.id),
                            target=str(r.end_node.id),
                            relationship_type=r.type,
                            properties=dict(r)
                        )
            
            return GraphData(nodes=list(nodes_dict.values()), edges=list(edges_dict.values()))
    
    def get_all_relationship_types(self) -> List[str]:
        with self._driver.session() as session:
            result = session.run("""
                MATCH ()-[r]->()
                RETURN DISTINCT type(r) AS rel_type
                ORDER BY rel_type
            """)
            
            return [record['rel_type'] for record in result]
