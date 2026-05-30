from neo4j import GraphDatabase, Driver
from typing import List, Dict, Any, Optional
import json

from app.models.lineage_models import (
    ColumnNode,
    TableNode,
    ColumnLineage,
    TableLineage,
    LineageResult,
    MappingChain,
    AggregatedLineage,
)
from app.services.analytics_service import (
    ImpactAnalysisService,
    DocumentGenerationService,
    AnomalyDetectionService,
)


class Neo4jService:
    def __init__(self, uri: str, user: str, password: str):
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def save_lineage(self, lineage_result: LineageResult):
        with self.driver.session() as session:
            session.execute_write(self._save_lineage_tx, lineage_result)

    @staticmethod
    def _save_lineage_tx(tx, lineage_result: LineageResult):
        for table in lineage_result.tables:
            Neo4jService._merge_table(tx, table)
        
        for column in lineage_result.columns:
            Neo4jService._merge_column(tx, column)
        
        for table_lineage in lineage_result.table_lineage:
            Neo4jService._merge_table_lineage(tx, table_lineage)
        
        for column_lineage in lineage_result.column_lineage:
            Neo4jService._merge_column_lineage(tx, column_lineage)
        
        for mapping_chain in lineage_result.mapping_chains:
            Neo4jService._merge_mapping_chain(tx, mapping_chain)
        
        for aggregated in lineage_result.aggregated_lineage:
            Neo4jService._merge_aggregated_lineage(tx, aggregated)

    @staticmethod
    def _merge_table(tx, table: TableNode):
        query = """
        MERGE (t:Table {full_name: $full_name})
        SET t.name = $name,
            t.schema = $schema,
            t.database = $database,
            t.node_type = $node_type,
            t.is_intermediate = $is_intermediate,
            t.alias_chain = $alias_chain
        RETURN t
        """
        tx.run(
            query,
            full_name=table.full_name,
            name=table.name,
            schema=table.table_schema,
            database=table.database,
            node_type=table.node_type.value if hasattr(table.node_type, 'value') else table.node_type,
            is_intermediate=table.is_intermediate,
            alias_chain=table.alias_chain,
        )

    @staticmethod
    def _merge_column(tx, column: ColumnNode):
        table_full_name = column.table_full_name
        query = """
        MATCH (t:Table {full_name: $table_full_name})
        MERGE (c:Column {full_name: $full_name})
        SET c.name = $name,
            c.table = $table,
            c.node_type = $node_type,
            c.is_intermediate = $is_intermediate
        MERGE (t)-[:HAS_COLUMN]->(c)
        RETURN c
        """
        tx.run(
            query,
            table_full_name=table_full_name,
            full_name=column.full_name,
            name=column.name,
            table=column.table,
            node_type=column.node_type.value if hasattr(column.node_type, 'value') else column.node_type,
            is_intermediate=column.is_intermediate,
        )

    @staticmethod
    def _merge_table_lineage(tx, lineage: TableLineage):
        query = """
        MATCH (source:Table {full_name: $source_full_name})
        MATCH (target:Table {full_name: $target_full_name})
        MERGE (source)-[r:TRANSFORMS_TO]->(target)
        SET r.query_type = $query_type,
            r.is_direct = $is_direct,
            r.intermediate_tables = $intermediate_tables
        RETURN r
        """
        tx.run(
            query,
            source_full_name=lineage.source.full_name,
            target_full_name=lineage.target.full_name,
            query_type=lineage.query_type,
            is_direct=lineage.is_direct,
            intermediate_tables=lineage.intermediate_tables,
        )

    @staticmethod
    def _merge_column_lineage(tx, lineage: ColumnLineage):
        mapping_chain_json = None
        if lineage.mapping_chain:
            mapping_chain_json = json.dumps(lineage.mapping_chain.model_dump())
        
        query = """
        MATCH (source:Column {full_name: $source_full_name})
        MATCH (target:Column {full_name: $target_full_name})
        MERGE (source)-[r:FLOWS_TO]->(target)
        SET r.expression = $expression,
            r.is_direct = $is_direct,
            r.intermediate_nodes = $intermediate_nodes,
            r.mapping_chain = $mapping_chain
        RETURN r
        """
        tx.run(
            query,
            source_full_name=lineage.source.full_name,
            target_full_name=lineage.target.full_name,
            expression=lineage.expression,
            is_direct=lineage.is_direct,
            intermediate_nodes=lineage.intermediate_nodes,
            mapping_chain=mapping_chain_json,
        )

    @staticmethod
    def _merge_mapping_chain(tx, mapping_chain: MappingChain):
        query = """
        MATCH (target:Column {full_name: $target_full_name})
        MERGE (mc:MappingChain {id: $chain_id})
        SET mc.target_column = $target_column,
            mc.target_table = $target_table,
            mc.full_chain = $full_chain,
            mc.chain_depth = $chain_depth,
            mc.source_columns = $source_columns,
            mc.source_tables = $source_tables,
            mc.links = $links
        MERGE (target)-[:HAS_MAPPING_CHAIN]->(mc)
        """
        chain_id = f"{mapping_chain.target_table}.{mapping_chain.target_column}"
        links_json = [link.model_dump() for link in mapping_chain.links]
        
        tx.run(
            query,
            target_full_name=f"{mapping_chain.target_table}.{mapping_chain.target_column}",
            chain_id=chain_id,
            target_column=mapping_chain.target_column,
            target_table=mapping_chain.target_table,
            full_chain=mapping_chain.full_chain,
            chain_depth=mapping_chain.chain_depth,
            source_columns=mapping_chain.source_columns,
            source_tables=mapping_chain.source_tables,
            links=links_json,
        )

    @staticmethod
    def _merge_aggregated_lineage(tx, aggregated: AggregatedLineage):
        query = """
        MATCH (source {full_name: $source_full_name})
        MATCH (target {full_name: $target_full_name})
        MERGE (source)-[r:AGGREGATED_FLOWS_TO]->(target)
        SET r.intermediate_count = $intermediate_count,
            r.intermediate_nodes = $intermediate_nodes,
            r.expression = $expression,
            r.is_collapsed = $is_collapsed
        RETURN r
        """
        tx.run(
            query,
            source_full_name=aggregated.source,
            target_full_name=aggregated.target,
            intermediate_count=aggregated.intermediate_count,
            intermediate_nodes=aggregated.intermediate_nodes,
            expression=aggregated.expression,
            is_collapsed=aggregated.is_collapsed,
        )

    def get_table_lineage(
        self,
        table_name: str,
        depth: int = 3,
        collapse_intermediate: bool = True,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_table_lineage_tx,
                table_name,
                depth,
                collapse_intermediate,
            )

    @staticmethod
    def _get_table_lineage_tx(
        tx,
        table_name: str,
        depth: int,
        collapse_intermediate: bool,
    ) -> Dict[str, Any]:
        nodes = []
        relationships = []
        node_ids = set()

        if collapse_intermediate:
            query = f"""
            MATCH (start:Table {{full_name: $table_name}})
            OPTIONAL MATCH up_path = (start)<-[:TRANSFORMS_TO*1..{depth}]-(source:Table)
                WHERE ALL(n IN nodes(up_path)[1..-1] WHERE n.is_intermediate = true)
            OPTIONAL MATCH down_path = (start)-[:TRANSFORMS_TO*1..{depth}]->(target:Table)
                WHERE ALL(n IN nodes(down_path)[1..-1] WHERE n.is_intermediate = true)
            
            WITH COLLECT(DISTINCT source) + COLLECT(DISTINCT target) + [start] AS all_nodes,
                 COLLECT(DISTINCT relationships(up_path)) + COLLECT(DISTINCT relationships(down_path)) AS all_rels
            
            UNWIND all_nodes AS node
            WITH DISTINCT node, all_rels
            WHERE node IS NOT NULL
            
            RETURN COLLECT(DISTINCT node) AS nodes,
                   [rel IN all_rels WHERE rel IS NOT NULL | rel] AS rels
            """
        else:
            query = f"""
            MATCH path = (t:Table {{full_name: $table_name}})
                  -[:TRANSFORMS_TO*0..{depth}]-
                  (related:Table)
            RETURN DISTINCT nodes(path) AS path_nodes, relationships(path) AS path_rels
            """
        
        result = tx.run(query, table_name=table_name)
        
        if collapse_intermediate:
            for record in result:
                for node in record["nodes"]:
                    node_id = node["full_name"]
                    if node_id not in node_ids:
                        node_ids.add(node_id)
                        is_intermediate = node.get("is_intermediate", False)
                        node_type = node.get("node_type", "intermediate")
                        nodes.append({
                            "id": node_id,
                            "label": node["name"],
                            "type": "table",
                            "node_type": node_type,
                            "is_intermediate": is_intermediate,
                            "data": dict(node),
                        })
                
                for rel_list in record["rels"]:
                    for rel in rel_list:
                        if rel:
                            source_id = rel.nodes[0]["full_name"]
                            target_id = rel.nodes[1]["full_name"]
                            
                            is_direct = rel.get("is_direct", True)
                            
                            if not is_direct and rel.get("intermediate_tables"):
                                if source_id in node_ids and target_id in node_ids:
                                    relationships.append({
                                        "source": source_id,
                                        "target": target_id,
                                        "type": "AGGREGATED_TRANSFORMS_TO",
                                        "is_collapsed": True,
                                        "intermediate_count": len(rel.get("intermediate_tables", [])),
                                        "intermediate_nodes": rel.get("intermediate_tables", []),
                                        "data": dict(rel),
                                    })
                            else:
                                if source_id in node_ids and target_id in node_ids:
                                    relationships.append({
                                        "source": source_id,
                                        "target": target_id,
                                        "type": rel.type,
                                        "is_collapsed": False,
                                        "data": dict(rel),
                                    })
        else:
            for record in result:
                for node in record["path_nodes"]:
                    node_id = node["full_name"]
                    if node_id not in node_ids:
                        node_ids.add(node_id)
                        is_intermediate = node.get("is_intermediate", False)
                        node_type = node.get("node_type", "intermediate")
                        nodes.append({
                            "id": node_id,
                            "label": node["name"],
                            "type": "table",
                            "node_type": node_type,
                            "is_intermediate": is_intermediate,
                            "data": dict(node),
                        })
                
                for rel in record["path_rels"]:
                    relationships.append({
                        "source": rel.nodes[0]["full_name"],
                        "target": rel.nodes[1]["full_name"],
                        "type": rel.type,
                        "is_collapsed": False,
                        "data": dict(rel),
                    })
        
        unique_edges = []
        seen_edges = set()
        for edge in relationships:
            edge_key = f"{edge['source']}-{edge['target']}-{edge['type']}"
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                unique_edges.append(edge)
        
        return {"nodes": nodes, "edges": unique_edges}

    def get_column_lineage(
        self,
        column_name: str,
        depth: int = 3,
        collapse_intermediate: bool = True,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(
                self._get_column_lineage_tx,
                column_name,
                depth,
                collapse_intermediate,
            )

    @staticmethod
    def _get_column_lineage_tx(
        tx,
        column_name: str,
        depth: int,
        collapse_intermediate: bool,
    ) -> Dict[str, Any]:
        nodes = []
        relationships = []
        node_ids = set()

        if collapse_intermediate:
            query = f"""
            MATCH (start:Column {{full_name: $column_name}})
            OPTIONAL MATCH up_path = (start)<-[:FLOWS_TO*1..{depth}]-(source:Column)
                WHERE ALL(n IN nodes(up_path)[1..-1] WHERE n.is_intermediate = true)
            OPTIONAL MATCH down_path = (start)-[:FLOWS_TO*1..{depth}]->(target:Column)
                WHERE ALL(n IN nodes(down_path)[1..-1] WHERE n.is_intermediate = true)
            
            WITH COLLECT(DISTINCT source) + COLLECT(DISTINCT target) + [start] AS all_nodes,
                 COLLECT(DISTINCT relationships(up_path)) + COLLECT(DISTINCT relationships(down_path)) AS all_rels
            
            UNWIND all_nodes AS node
            WITH DISTINCT node, all_rels
            WHERE node IS NOT NULL
            
            RETURN COLLECT(DISTINCT node) AS nodes,
                   [rel IN all_rels WHERE rel IS NOT NULL | rel] AS rels
            """
        else:
            query = f"""
            MATCH path = (c:Column {{full_name: $column_name}})
                  -[:FLOWS_TO*0..{depth}]-
                  (related:Column)
            RETURN DISTINCT nodes(path) AS path_nodes, relationships(path) AS path_rels
            """
        
        result = tx.run(query, column_name=column_name)
        
        if collapse_intermediate:
            for record in result:
                for node in record["nodes"]:
                    node_id = node["full_name"]
                    if node_id not in node_ids:
                        node_ids.add(node_id)
                        is_intermediate = node.get("is_intermediate", False)
                        node_type = node.get("node_type", "intermediate")
                        nodes.append({
                            "id": node_id,
                            "label": node["name"],
                            "type": "column",
                            "node_type": node_type,
                            "is_intermediate": is_intermediate,
                            "data": dict(node),
                        })
                
                for rel_list in record["rels"]:
                    for rel in rel_list:
                        if rel:
                            source_id = rel.nodes[0]["full_name"]
                            target_id = rel.nodes[1]["full_name"]
                            
                            is_direct = rel.get("is_direct", True)
                            
                            if not is_direct and rel.get("intermediate_nodes"):
                                if source_id in node_ids and target_id in node_ids:
                                    relationships.append({
                                        "source": source_id,
                                        "target": target_id,
                                        "type": "AGGREGATED_FLOWS_TO",
                                        "is_collapsed": True,
                                        "intermediate_count": len(rel.get("intermediate_nodes", [])),
                                        "intermediate_nodes": rel.get("intermediate_nodes", []),
                                        "expression": rel.get("expression"),
                                        "data": dict(rel),
                                    })
                            else:
                                if source_id in node_ids and target_id in node_ids:
                                    relationships.append({
                                        "source": source_id,
                                        "target": target_id,
                                        "type": rel.type,
                                        "is_collapsed": False,
                                        "expression": rel.get("expression"),
                                        "data": dict(rel),
                                    })
        else:
            for record in result:
                for node in record["path_nodes"]:
                    node_id = node["full_name"]
                    if node_id not in node_ids:
                        node_ids.add(node_id)
                        is_intermediate = node.get("is_intermediate", False)
                        node_type = node.get("node_type", "intermediate")
                        nodes.append({
                            "id": node_id,
                            "label": node["name"],
                            "type": "column",
                            "node_type": node_type,
                            "is_intermediate": is_intermediate,
                            "data": dict(node),
                        })
                
                for rel in record["path_rels"]:
                    relationships.append({
                        "source": rel.nodes[0]["full_name"],
                        "target": rel.nodes[1]["full_name"],
                        "type": rel.type,
                        "is_collapsed": False,
                        "expression": rel.get("expression"),
                        "data": dict(rel),
                    })
        
        unique_edges = []
        seen_edges = set()
        for edge in relationships:
            edge_key = f"{edge['source']}-{edge['target']}-{edge['type']}"
            if edge_key not in seen_edges:
                seen_edges.add(edge_key)
                unique_edges.append(edge)
        
        return {"nodes": nodes, "edges": unique_edges}

    def get_mapping_chains(self, column_name: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            return session.execute_read(self._get_mapping_chains_tx, column_name)

    @staticmethod
    def _get_mapping_chains_tx(tx, column_name: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (c:Column {full_name: $column_name})-[:HAS_MAPPING_CHAIN]->(mc:MappingChain)
        RETURN mc
        """
        result = tx.run(query, column_name=column_name)
        return [dict(record["mc"]) for record in result]

    def get_all_tables(self) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            return session.execute_read(self._get_all_tables_tx)

    @staticmethod
    def _get_all_tables_tx(tx) -> List[Dict[str, Any]]:
        query = "MATCH (t:Table) RETURN t ORDER BY t.full_name"
        result = tx.run(query)
        return [dict(record["t"]) for record in result]

    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        with self.driver.session() as session:
            return session.execute_read(self._get_table_columns_tx, table_name)

    @staticmethod
    def _get_table_columns_tx(tx, table_name: str) -> List[Dict[str, Any]]:
        query = """
        MATCH (t:Table {full_name: $table_name})-[:HAS_COLUMN]->(c:Column)
        RETURN c ORDER BY c.name
        """
        result = tx.run(query, table_name=table_name)
        return [dict(record["c"]) for record in result]

    def clear_database(self):
        with self.driver.session() as session:
            session.execute_write(self._clear_database_tx)

    @staticmethod
    def _clear_database_tx(tx):
        tx.run("MATCH (n) DETACH DELETE n")

    def get_full_graph(
        self,
        collapse_intermediate: bool = True,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(self._get_full_graph_tx, collapse_intermediate)

    @staticmethod
    def _get_full_graph_tx(tx, collapse_intermediate: bool) -> Dict[str, Any]:
        nodes = []
        relationships = []

        if collapse_intermediate:
            table_query = """
            MATCH (t:Table)
            WHERE t.is_intermediate = false
            RETURN t
            """
            column_query = """
            MATCH (c:Column)
            WHERE c.is_intermediate = false
            RETURN c
            """
            
            table_lineage_query = """
            MATCH (source:Table {is_intermediate: false})
            MATCH (target:Table {is_intermediate: false})
            MATCH path = (source)-[:TRANSFORMS_TO*1..10]->(target)
            WHERE ALL(n IN nodes(path)[1..-1] WHERE n.is_intermediate = true)
            WITH source, target, relationships(path) AS rels, nodes(path) AS path_nodes
            RETURN source, target, rels, path_nodes
            """
            
            column_lineage_query = """
            MATCH (source:Column {is_intermediate: false})
            MATCH (target:Column {is_intermediate: false})
            MATCH path = (source)-[:FLOWS_TO*1..10]->(target)
            WHERE ALL(n IN nodes(path)[1..-1] WHERE n.is_intermediate = true)
            WITH source, target, relationships(path) AS rels, nodes(path) AS path_nodes
            RETURN source, target, rels, path_nodes
            """
        else:
            table_query = "MATCH (t:Table) RETURN t"
            column_query = "MATCH (c:Column) RETURN c"
            table_lineage_query = "MATCH ()-[r:TRANSFORMS_TO]->() RETURN r"
            column_lineage_query = "MATCH ()-[r:FLOWS_TO]->() RETURN r"

        table_result = tx.run(table_query)
        for record in table_result:
            node = record["t"]
            is_intermediate = node.get("is_intermediate", False)
            node_type = node.get("node_type", "intermediate")
            nodes.append({
                "id": node["full_name"],
                "label": node["name"],
                "type": "table",
                "node_type": node_type,
                "is_intermediate": is_intermediate,
                "data": dict(node),
            })

        column_result = tx.run(column_query)
        for record in column_result:
            node = record["c"]
            is_intermediate = node.get("is_intermediate", False)
            node_type = node.get("node_type", "intermediate")
            nodes.append({
                "id": node["full_name"],
                "label": node["name"],
                "type": "column",
                "node_type": node_type,
                "is_intermediate": is_intermediate,
                "data": dict(node),
            })

        if collapse_intermediate:
            table_lineage_result = tx.run(table_lineage_query)
            seen_table_edges = set()
            
            for record in table_lineage_result:
                source = record["source"]
                target = record["target"]
                path_nodes = record["path_nodes"]
                
                intermediate_tables = [
                    n["full_name"] for n in path_nodes[1:-1]
                ]
                
                edge_key = f"{source['full_name']}-{target['full_name']}-aggregated"
                if edge_key not in seen_table_edges:
                    seen_table_edges.add(edge_key)
                    relationships.append({
                        "source": source["full_name"],
                        "target": target["full_name"],
                        "type": "AGGREGATED_TRANSFORMS_TO",
                        "is_collapsed": True,
                        "intermediate_count": len(intermediate_tables),
                        "intermediate_nodes": intermediate_tables,
                        "data": {"intermediate_tables": intermediate_tables},
                    })
            
            column_lineage_result = tx.run(column_lineage_query)
            seen_column_edges = set()
            
            for record in column_lineage_result:
                source = record["source"]
                target = record["target"]
                path_nodes = record["path_nodes"]
                rels = record["rels"]
                
                intermediate_columns = [
                    n["full_name"] for n in path_nodes[1:-1]
                ]
                
                expression = None
                for rel in rels:
                    if rel.get("expression"):
                        expression = rel.get("expression")
                        break
                
                edge_key = f"{source['full_name']}-{target['full_name']}-aggregated"
                if edge_key not in seen_column_edges:
                    seen_column_edges.add(edge_key)
                    relationships.append({
                        "source": source["full_name"],
                        "target": target["full_name"],
                        "type": "AGGREGATED_FLOWS_TO",
                        "is_collapsed": True,
                        "intermediate_count": len(intermediate_columns),
                        "intermediate_nodes": intermediate_columns,
                        "expression": expression,
                        "data": {"intermediate_columns": intermediate_columns},
                    })
        else:
            table_lineage_result = tx.run(table_lineage_query)
            for record in table_lineage_result:
                rel = record["r"]
                relationships.append({
                    "source": rel.nodes[0]["full_name"],
                    "target": rel.nodes[1]["full_name"],
                    "type": "TRANSFORMS_TO",
                    "is_collapsed": False,
                    "data": dict(rel),
                })

            column_lineage_result = tx.run(column_lineage_query)
            for record in column_lineage_result:
                rel = record["r"]
                relationships.append({
                    "source": rel.nodes[0]["full_name"],
                    "target": rel.nodes[1]["full_name"],
                    "type": "FLOWS_TO",
                    "is_collapsed": False,
                    "expression": rel.get("expression"),
                    "data": dict(rel),
                })

        return {"nodes": nodes, "edges": relationships}

    def expand_aggregated_edge(
        self,
        source_name: str,
        target_name: str,
    ) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(
                self._expand_aggregated_edge_tx,
                source_name,
                target_name,
            )

    @staticmethod
    def _expand_aggregated_edge_tx(tx, source_name: str, target_name: str) -> Dict[str, Any]:
        nodes = []
        relationships = []
        node_ids = set()

        query = """
        MATCH (source {full_name: $source_name})
        MATCH (target {full_name: $target_name})
        MATCH path = (source)-[*1..10]->(target)
        WHERE ALL(n IN nodes(path)[1..-1] WHERE n.is_intermediate = true)
        RETURN nodes(path) AS path_nodes, relationships(path) AS path_rels
        LIMIT 1
        """
        
        result = tx.run(query, source_name=source_name, target_name=target_name)
        
        for record in result:
            for node in record["path_nodes"]:
                node_id = node["full_name"]
                if node_id not in node_ids:
                    node_ids.add(node_id)
                    is_intermediate = node.get("is_intermediate", False)
                    node_type = node.get("node_type", "intermediate")
                    nodes.append({
                        "id": node_id,
                        "label": node["name"],
                        "type": "table" if "Table" in list(node.labels) else "column",
                        "node_type": node_type,
                        "is_intermediate": is_intermediate,
                        "data": dict(node),
                    })
            
            for rel in record["path_rels"]:
                relationships.append({
                    "source": rel.nodes[0]["full_name"],
                    "target": rel.nodes[1]["full_name"],
                    "type": rel.type,
                    "is_collapsed": False,
                    "expression": rel.get("expression"),
                    "data": dict(rel),
                })
        
        return {"nodes": nodes, "edges": relationships}
    
    def _load_all_data(self) -> Dict[str, Any]:
        with self.driver.session() as session:
            return session.execute_read(self._load_all_data_tx)
    
    @staticmethod
    def _load_all_data_tx(tx) -> Dict[str, Any]:
        tables = []
        columns = []
        table_lineages = []
        column_lineages = []
        mapping_chains = []
        
        table_query = "MATCH (t:Table) RETURN t"
        for record in tx.run(table_query):
            node = record["t"]
            tables.append(TableNode(
                name=node["name"],
                schema=node.get("schema"),
                database=node.get("database"),
                node_type=node.get("node_type", "intermediate"),
                is_intermediate=node.get("is_intermediate", False),
                alias_chain=node.get("alias_chain", []),
            ))
        
        column_query = "MATCH (c:Column) RETURN c"
        for record in tx.run(column_query):
            node = record["c"]
            columns.append(ColumnNode(
                name=node["name"],
                table=node.get("table"),
                schema=node.get("schema"),
                database=node.get("database"),
                node_type=node.get("node_type", "intermediate"),
                is_intermediate=node.get("is_intermediate", False),
                alias_chain=node.get("alias_chain", []),
            ))
        
        table_lineage_query = "MATCH (s:Table)-[r:TRANSFORMS_TO]->(t:Table) RETURN s, r, t"
        for record in tx.run(table_lineage_query):
            s = record["s"]
            t = record["t"]
            r = record["r"]
            source_node = TableNode(
                name=s["name"],
                schema=s.get("schema"),
                database=s.get("database"),
                node_type=s.get("node_type", "intermediate"),
            )
            target_node = TableNode(
                name=t["name"],
                schema=t.get("schema"),
                database=t.get("database"),
                node_type=t.get("node_type", "intermediate"),
            )
            table_lineages.append(TableLineage(
                source=source_node,
                target=target_node,
                query_type=r.get("query_type", "UNKNOWN"),
                is_direct=r.get("is_direct", True),
                intermediate_tables=r.get("intermediate_tables", []),
            ))
        
        column_lineage_query = "MATCH (s:Column)-[r:FLOWS_TO]->(t:Column) RETURN s, r, t"
        for record in tx.run(column_lineage_query):
            s = record["s"]
            t = record["t"]
            r = record["r"]
            source_node = ColumnNode(
                name=s["name"],
                table=s.get("table"),
                node_type=s.get("node_type", "intermediate"),
            )
            target_node = ColumnNode(
                name=t["name"],
                table=t.get("table"),
                node_type=t.get("node_type", "intermediate"),
            )
            column_lineages.append(ColumnLineage(
                source=source_node,
                target=target_node,
                expression=r.get("expression"),
                is_direct=r.get("is_direct", True),
                intermediate_nodes=r.get("intermediate_nodes", []),
            ))
        
        return {
            "tables": tables,
            "columns": columns,
            "table_lineages": table_lineages,
            "column_lineages": column_lineages,
            "mapping_chains": mapping_chains,
        }
    
    def analyze_impact(self, source_table: str, max_depth: int = 10) -> Dict[str, Any]:
        data = self._load_all_data()
        result = ImpactAnalysisService.analyze_impact(
            source_table,
            data["tables"],
            data["columns"],
            data["table_lineages"],
            data["column_lineages"],
            max_depth,
        )
        return result.model_dump()
    
    def generate_data_dictionary(self) -> Dict[str, Any]:
        data = self._load_all_data()
        result = DocumentGenerationService.generate_data_dictionary(
            data["tables"],
            data["columns"],
            data["table_lineages"],
            data["column_lineages"],
            data["mapping_chains"],
        )
        return result.model_dump()
    
    def generate_lineage_document(self, title: str = "数据血缘文档") -> Dict[str, Any]:
        data = self._load_all_data()
        result = DocumentGenerationService.generate_lineage_document(
            title,
            data["tables"],
            data["columns"],
            data["table_lineages"],
            data["column_lineages"],
            data["mapping_chains"],
        )
        return result.model_dump()
    
    def generate_markdown_document(self, title: str = "数据血缘文档") -> str:
        data = self._load_all_data()
        doc = DocumentGenerationService.generate_lineage_document(
            title,
            data["tables"],
            data["columns"],
            data["table_lineages"],
            data["column_lineages"],
            data["mapping_chains"],
        )
        return DocumentGenerationService.export_markdown(doc)
    
    def detect_anomalies(self) -> Dict[str, Any]:
        data = self._load_all_data()
        result = AnomalyDetectionService.detect_anomalies(
            data["tables"],
            data["columns"],
            data["table_lineages"],
            data["column_lineages"],
        )
        return result.model_dump()
