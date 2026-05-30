from neo4j import GraphDatabase
from typing import List, Dict, Any
from config.settings import settings


class Neo4jClient:
    def __init__(self):
        self.driver = GraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )
        self.database = settings.NEO4J_DATABASE

    def close(self):
        self.driver.close()

    def execute_query(self, query: str, parameters: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        with self.driver.session(database=self.database) as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def create_node(self, label: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        query = f"""
        CREATE (n:{label} $properties)
        RETURN n
        """
        result = self.execute_query(query, {"properties": properties})
        return result[0]["n"] if result else None

    def create_relationship(
        self,
        start_label: str,
        start_property: str,
        start_value: str,
        end_label: str,
        end_property: str,
        end_value: str,
        relation_type: str,
        properties: Dict[str, Any] = None
    ):
        query = f"""
        MATCH (a:{start_label} {{{start_property}: $start_value}})
        MATCH (b:{end_label} {{{end_property}: $end_value}})
        MERGE (a)-[r:{relation_type} $relation_props]->(b)
        RETURN r
        """
        result = self.execute_query(
            query,
            {
                "start_value": start_value,
                "end_value": end_value,
                "relation_props": properties or {}
            }
        )
        return result[0]["r"] if result else None

    def find_entity_by_name(self, name: str, fuzzy: bool = False) -> List[Dict[str, Any]]:
        if fuzzy:
            query = """
            MATCH (n)
            WHERE toLower(n.name) CONTAINS toLower($name)
            RETURN n, labels(n) as labels
            LIMIT 10
            """
        else:
            query = """
            MATCH (n)
            WHERE n.name = $name
            RETURN n, labels(n) as labels
            LIMIT 10
            """
        return self.execute_query(query, {"name": name})

    def get_entity_relations(self, entity_name: str, max_depth: int = 3) -> List[Dict[str, Any]]:
        query = f"""
        MATCH path = (n {{name: $name}})-[*1..{max_depth}]-()
        RETURN path
        LIMIT 50
        """
        return self.execute_query(query, {"name": entity_name})

    def multi_hop_query(
        self,
        start_entity: str,
        relations: List[str],
        direction: str = "out"
    ) -> List[Dict[str, Any]]:
        relation_str = "->".join([f"[:{r}]" for r in relations])
        if direction == "in":
            relation_str = "<-" + relation_str[1:]
        elif direction == "both":
            relation_str = "-" + relation_str[1:-1] + "-"

        query = f"""
        MATCH (n {{name: $start_entity}}){relation_str}(m)
        RETURN n, m, [r IN relationships(path) | type(r)] as relations
        LIMIT 20
        """
        return self.execute_query(query, {"start_entity": start_entity})


neo4j_client = Neo4jClient()
