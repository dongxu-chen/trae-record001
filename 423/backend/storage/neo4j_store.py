from neo4j import GraphDatabase
from datetime import datetime
from config import Config


class Neo4jStore:
    def __init__(self):
        config = Config()
        uri = config.get("neo4j.uri", "bolt://localhost:7687")
        user = config.get("neo4j.user", "neo4j")
        password = config.get("neo4j.password", "topology123")
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        self._init_schema()

    def _init_schema(self):
        with self.driver.session() as session:
            session.run("""
                CREATE CONSTRAINT service_name IF NOT EXISTS
                FOR (s:Service) REQUIRE s.name IS UNIQUE
            """)
            session.run("""
                CREATE INDEX service_timestamp IF NOT EXISTS
                FOR (s:Service) ON (s.last_seen)
            """)
            session.run("""
                CREATE INDEX api_version IF NOT EXISTS
                FOR (a:API) ON (a.version)
            """)
            session.run("""
                CREATE INDEX queue_name IF NOT EXISTS
                FOR (q:MessageQueue) REQUIRE q.name IS UNIQUE
            """)

    def close(self):
        self.driver.close()

    def upsert_service(self, name, service_type="unknown", layer=None):
        with self.driver.session() as session:
            result = session.run("""
                MERGE (s:Service {name: $name})
                ON CREATE SET
                    s.service_type = $service_type,
                    s.layer = $layer,
                    s.first_seen = datetime(),
                    s.last_seen = datetime(),
                    s.call_count = 0,
                    s.error_count = 0,
                    s.total_latency = 0
                ON MATCH SET
                    s.last_seen = datetime(),
                    s.service_type = COALESCE($service_type, s.service_type),
                    s.layer = COALESCE($layer, s.layer)
                RETURN s.name AS name, s.layer AS layer
            """, name=name, service_type=service_type, layer=layer)
            return result.single()

    def upsert_call_edge(self, source, target, call_count=1, error_count=0,
                         total_latency=0, max_latency=0, min_latency=0,
                         call_type="sync", api_version=None,
                         operation_name=None):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Service {name: $source})
                MATCH (t:Service {name: $target})
                MERGE (s)-[r:CALLS {
                    source: $source,
                    target: $target,
                    operation: COALESCE($operation_name, r.operation, 'unknown')
                }]->(t)
                ON CREATE SET
                    r.call_count = $call_count,
                    r.error_count = $error_count,
                    r.total_latency = $total_latency,
                    r.max_latency = $max_latency,
                    r.min_latency = $min_latency,
                    r.call_type = $call_type,
                    r.api_version = $api_version,
                    r.last_updated = datetime(),
                    r.first_seen = datetime()
                ON MATCH SET
                    r.call_count = r.call_count + $call_count,
                    r.error_count = r.error_count + $error_count,
                    r.total_latency = r.total_latency + $total_latency,
                    r.max_latency = CASE WHEN $max_latency > r.max_latency
                                        THEN $max_latency ELSE r.max_latency END,
                    r.min_latency = CASE WHEN $min_latency < r.min_latency OR r.min_latency = 0
                                        THEN $min_latency ELSE r.min_latency END,
                    r.api_version = COALESCE($api_version, r.api_version),
                    r.call_type = COALESCE($call_type, r.call_type, 'sync'),
                    r.last_updated = datetime()
                RETURN r.call_count AS call_count, r.error_count AS error_count
            """, source=source, target=target, call_count=call_count,
                error_count=error_count, total_latency=total_latency,
                max_latency=max_latency, min_latency=min_latency,
                call_type=call_type, api_version=api_version,
                operation_name=operation_name)
            return result.single()

    def upsert_message_queue(self, queue_name, queue_type="kafka"):
        with self.driver.session() as session:
            result = session.run("""
                MERGE (q:MessageQueue {name: $name})
                ON CREATE SET
                    q.queue_type = $queue_type,
                    q.first_seen = datetime(),
                    q.last_seen = datetime(),
                    q.produce_count = 0,
                    q.consume_count = 0
                ON MATCH SET
                    q.last_seen = datetime()
                RETURN q.name AS name, q.queue_type AS queue_type
            """, name=queue_name, queue_type=queue_type)
            return result.single()

    def upsert_produce_edge(self, service_name, queue_name, count=1,
                            error_count=0, api_version=None,
                            operation_name=None):
        with self.driver.session() as session:
            self.upsert_service(service_name)
            self.upsert_message_queue(queue_name)

            result = session.run("""
                MATCH (s:Service {name: $service})
                MATCH (q:MessageQueue {name: $queue})
                MERGE (s)-[r:PRODUCES {
                    source: $service,
                    target: $queue,
                    operation: COALESCE($operation_name, r.operation, 'produce')
                }]->(q)
                ON CREATE SET
                    r.call_count = $count,
                    r.error_count = $error_count,
                    r.api_version = $api_version,
                    r.last_updated = datetime(),
                    r.first_seen = datetime()
                ON MATCH SET
                    r.call_count = r.call_count + $count,
                    r.error_count = r.error_count + $error_count,
                    r.api_version = COALESCE($api_version, r.api_version),
                    r.last_updated = datetime()
                SET q.produce_count = q.produce_count + $count
                RETURN r.call_count AS call_count
            """, service=service_name, queue=queue_name, count=count,
                error_count=error_count, api_version=api_version,
                operation_name=operation_name)
            return result.single()

    def upsert_consume_edge(self, queue_name, service_name, count=1,
                            error_count=0, api_version=None,
                            operation_name=None, latency=0):
        with self.driver.session() as session:
            self.upsert_service(service_name)
            self.upsert_message_queue(queue_name)

            result = session.run("""
                MATCH (q:MessageQueue {name: $queue})
                MATCH (s:Service {name: $service})
                MERGE (q)-[r:CONSUMES {
                    source: $queue,
                    target: $service,
                    operation: COALESCE($operation_name, r.operation, 'consume')
                }]->(s)
                ON CREATE SET
                    r.call_count = $count,
                    r.error_count = $error_count,
                    r.avg_latency = $latency,
                    r.api_version = $api_version,
                    r.last_updated = datetime(),
                    r.first_seen = datetime()
                ON MATCH SET
                    r.call_count = r.call_count + $count,
                    r.error_count = r.error_count + $error_count,
                    r.avg_latency = (r.avg_latency * (r.call_count - $count) + $latency * $count) / r.call_count,
                    r.api_version = COALESCE($api_version, r.api_version),
                    r.last_updated = datetime()
                SET q.consume_count = q.consume_count + $count
                RETURN r.call_count AS call_count
            """, queue=queue_name, service=service_name, count=count,
                error_count=error_count, api_version=api_version,
                operation_name=operation_name, latency=latency)
            return result.single()

    def upsert_api_endpoint(self, service_name, path, method, version,
                           deprecated=False, breaking_change=False,
                           change_description=None):
        with self.driver.session() as session:
            api_id = f"{service_name}:{method}:{path}:{version}"
            result = session.run("""
                MATCH (s:Service {name: $service})
                MERGE (a:API {id: $api_id})
                ON CREATE SET
                    a.path = $path,
                    a.method = $method,
                    a.version = $version,
                    a.deprecated = $deprecated,
                    a.breaking_change = $breaking_change,
                    a.change_description = $change_description,
                    a.first_seen = datetime(),
                    a.last_seen = datetime()
                ON MATCH SET
                    a.deprecated = COALESCE($deprecated, a.deprecated),
                    a.breaking_change = COALESCE($breaking_change, a.breaking_change),
                    a.change_description = COALESCE($change_description, a.change_description),
                    a.last_seen = datetime()
                MERGE (s)-[r:EXPOSES]->(a)
                RETURN a.id AS api_id
            """, service=service_name, api_id=api_id, path=path,
                method=method, version=version, deprecated=deprecated,
                breaking_change=breaking_change,
                change_description=change_description)
            return result.single()

    def get_api_dependencies(self, api_id):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (a:API {id: $api_id})<-[:EXPOSES]-(s:Service)
                MATCH path = (s)-[r:CALLS*1..5]->(downstream:Service)
                WHERE ALL(rel IN relationships(path) WHERE rel.call_count > 0)
                WITH DISTINCT downstream, length(path) AS hop_count
                RETURN
                    downstream.name AS name,
                    downstream.layer AS layer,
                    hop_count
                ORDER BY hop_count ASC
            """, api_id=api_id)

            return [{
                "name": record["name"],
                "layer": record["layer"],
                "hop_count": record["hop_count"]
            } for record in result]

    def get_version_impact_analysis(self, service_name, old_version, new_version):
        with self.driver.session() as session:
            changed_apis = session.run("""
                MATCH (s:Service {name: $service})-[:EXPOSES]->(a:API)
                WHERE a.version = $new_version
                   OR a.breaking_change = true
                RETURN
                    a.id AS api_id,
                    a.path AS path,
                    a.method AS method,
                    a.version AS version,
                    a.breaking_change AS breaking_change,
                    a.change_description AS change_description
            """, service=service_name, new_version=new_version)

            apis = []
            for record in changed_apis:
                api_id = record["api_id"]
                impacted = self.get_api_dependencies(api_id)
                apis.append({
                    "api_id": api_id,
                    "path": record["path"],
                    "method": record["method"],
                    "version": record["version"],
                    "breaking_change": record["breaking_change"],
                    "change_description": record["change_description"],
                    "impacted_downstream": impacted,
                    "impact_count": len(impacted)
                })

            return {
                "service": service_name,
                "old_version": old_version,
                "new_version": new_version,
                "changed_apis": apis,
                "total_impacted": sum(len(api["impacted_downstream"]) for api in apis)
            }

    def snapshot_topology(self, snapshot_id=None):
        if snapshot_id is None:
            snapshot_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        with self.driver.session() as session:
            session.run("""
                MATCH (s:Service)
                SET s.snapshot = $snapshot_id
            """, snapshot_id=snapshot_id)

            session.run("""
                MATCH (s:Service)-[r:CALLS]->(t:Service)
                SET r.snapshot = $snapshot_id
            """, snapshot_id=snapshot_id)

            return snapshot_id

    def get_topology(self, time_window_minutes=60, include_async=True):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Service)-[r:CALLS]->(t:Service)
                WHERE r.last_updated >= datetime() - duration({minutes: $window})
                   OR s.last_seen >= datetime() - duration({minutes: $window})
                RETURN
                    s.name AS source,
                    t.name AS target,
                    s.layer AS source_layer,
                    t.layer AS target_layer,
                    r.call_count AS call_count,
                    r.error_count AS error_count,
                    r.total_latency AS total_latency,
                    r.max_latency AS max_latency,
                    r.min_latency AS min_latency,
                    r.call_type AS call_type,
                    r.api_version AS api_version,
                    r.operation AS operation,
                    s.call_count AS source_call_count,
                    s.error_count AS source_error_count,
                    t.call_count AS target_call_count,
                    t.error_count AS target_error_count
            """, window=time_window_minutes)

            edges = []
            services = set()
            for record in result:
                edges.append({
                    "id": f"call:{record['source']}->{record['target']}",
                    "source": record["source"],
                    "target": record["target"],
                    "type": "call",
                    "call_type": record["call_type"] or "sync",
                    "source_layer": record["source_layer"],
                    "target_layer": record["target_layer"],
                    "call_count": record["call_count"],
                    "error_count": record["error_count"],
                    "total_latency": record["total_latency"],
                    "max_latency": record["max_latency"],
                    "min_latency": record["min_latency"],
                    "api_version": record["api_version"],
                    "operation": record["operation"],
                    "error_rate": (
                        record["error_count"] / record["call_count"]
                        if record["call_count"] > 0 else 0
                    ),
                    "avg_latency": (
                        record["total_latency"] / record["call_count"]
                        if record["call_count"] > 0 else 0
                    ),
                })
                services.add(record["source"])
                services.add(record["target"])

            service_records = session.run("""
                MATCH (s:Service)
                WHERE s.last_seen >= datetime() - duration({minutes: $window})
                RETURN s.name AS name, s.layer AS layer,
                       s.service_type AS service_type,
                       s.call_count AS call_count, s.error_count AS error_count,
                       s.avg_latency AS avg_latency
            """, window=time_window_minutes)

            nodes = []
            for record in service_records:
                nodes.append({
                    "id": record["name"],
                    "name": record["name"],
                    "type": "service",
                    "layer": record["layer"],
                    "service_type": record["service_type"],
                    "call_count": record["call_count"],
                    "error_count": record["error_count"],
                    "avg_latency": record["avg_latency"] or 0,
                })
                services.add(record["name"])

            if include_async:
                queue_records = session.run("""
                    MATCH (q:MessageQueue)
                    RETURN q.name AS name, q.queue_type AS queue_type,
                           q.produce_count AS produce_count,
                           q.consume_count AS consume_count
                """)
                for record in queue_records:
                    nodes.append({
                        "id": record["name"],
                        "name": record["name"],
                        "type": "message_queue",
                        "queue_type": record["queue_type"],
                        "produce_count": record["produce_count"] or 0,
                        "consume_count": record["consume_count"] or 0,
                    })

                produce_records = session.run("""
                    MATCH (s:Service)-[r:PRODUCES]->(q:MessageQueue)
                    WHERE r.last_updated >= datetime() - duration({minutes: $window})
                    RETURN s.name AS source, q.name AS target,
                           r.call_count AS call_count,
                           r.error_count AS error_count,
                           r.api_version AS api_version,
                           r.operation AS operation
                """, window=time_window_minutes)
                for record in produce_records:
                    edges.append({
                        "id": f"produce:{record['source']}->{record['target']}",
                        "source": record["source"],
                        "target": record["target"],
                        "type": "produce",
                        "call_count": record["call_count"],
                        "error_count": record["error_count"],
                        "error_rate": (record["error_count"] or 0) / max(record["call_count"] or 1, 1),
                        "api_version": record["api_version"],
                        "operation": record["operation"]
                    })
                    services.add(record["source"])

                consume_records = session.run("""
                    MATCH (q:MessageQueue)-[r:CONSUMES]->(s:Service)
                    WHERE r.last_updated >= datetime() - duration({minutes: $window})
                    RETURN q.name AS source, s.name AS target,
                           r.call_count AS call_count,
                           r.error_count AS error_count,
                           r.avg_latency AS avg_latency,
                           r.api_version AS api_version,
                           r.operation AS operation
                """, window=time_window_minutes)
                for record in consume_records:
                    edges.append({
                        "id": f"consume:{record['source']}->{record['target']}",
                        "source": record["source"],
                        "target": record["target"],
                        "type": "consume",
                        "call_count": record["call_count"],
                        "error_count": record["error_count"],
                        "avg_latency": record["avg_latency"] or 0,
                        "error_rate": (record["error_count"] or 0) / max(record["call_count"] or 1, 1),
                        "api_version": record["api_version"],
                        "operation": record["operation"]
                    })
                    services.add(record["target"])

            return {
                "nodes": nodes,
                "edges": edges,
                "services": list(services),
            }

    def get_fault_impact(self, service_name, depth=5):
        with self.driver.session() as session:
            downstream = session.run("""
                MATCH (start:Service {name: $name})
                CALL {
                    WITH start
                    MATCH path = (start)-[r:CALLS*1..$depth]->(affected:Service)
                    WHERE ALL(rel IN relationships(path) WHERE rel.call_count > 0)
                    WITH DISTINCT affected,
                         length(path) AS hop_count,
                         [rel IN relationships(path) | rel.call_count] AS call_counts,
                         [rel IN relationships(path) | rel.error_count] AS error_counts,
                         [rel IN relationships(path) | rel.total_latency] AS latency_list
                    RETURN
                        affected.name AS name,
                        affected.layer AS layer,
                        affected.service_type AS service_type,
                        affected.call_count AS svc_call_count,
                        affected.error_count AS svc_error_count,
                        hop_count,
                        reduce(s = 0, c IN call_counts | s + c) AS total_calls,
                        reduce(s = 0, e IN error_counts | s + e) AS total_errors,
                        reduce(s = 0, l IN latency_list | s + l) AS total_latency
                    ORDER BY hop_count ASC, total_calls DESC
                }
                RETURN name, layer, service_type, svc_call_count, svc_error_count,
                       hop_count, total_calls, total_errors, total_latency
            """, name=service_name, depth=depth)

            impacted = []
            seen = set()
            for record in downstream:
                if record["name"] not in seen:
                    seen.add(record["name"])
                    impacted.append({
                        "name": record["name"],
                        "layer": record["layer"],
                        "service_type": record["service_type"],
                        "svc_call_count": record["svc_call_count"],
                        "svc_error_count": record["svc_error_count"],
                        "hop_count": record["hop_count"],
                        "total_calls": record["total_calls"],
                        "total_errors": record["total_errors"],
                        "total_latency": record["total_latency"],
                        "error_rate": (
                            record["total_errors"] / record["total_calls"]
                            if record["total_calls"] > 0 else 0
                        ),
                        "avg_latency": (
                            record["total_latency"] / record["total_calls"]
                            if record["total_calls"] > 0 else 0
                        ),
                        "impact_score": (
                            record["total_calls"] * max(1, 6 - record["hop_count"])
                        ),
                    })

            upstream = session.run("""
                MATCH (end:Service {name: $name})
                CALL {
                    WITH end
                    MATCH path = (upstream:Service)-[r:CALLS*1..$depth]->(end)
                    WHERE ALL(rel IN relationships(path) WHERE rel.call_count > 0)
                    WITH DISTINCT upstream, length(path) AS hop_count
                    RETURN upstream.name AS name, upstream.layer AS layer,
                           upstream.service_type AS service_type, hop_count
                    ORDER BY hop_count ASC
                }
                RETURN name, layer, service_type, hop_count
            """, name=service_name, depth=depth)

            upstream_list = []
            seen_up = set()
            for record in upstream:
                if record["name"] not in seen_up:
                    seen_up.add(record["name"])
                    upstream_list.append({
                        "name": record["name"],
                        "layer": record["layer"],
                        "service_type": record["service_type"],
                        "hop_count": record["hop_count"],
                    })

            return {
                "fault_service": service_name,
                "downstream_impact": impacted,
                "upstream_dependencies": upstream_list,
                "total_downstream": len(impacted),
                "total_upstream": len(upstream_list),
            }

    def get_topology_diff(self, snapshot_a, snapshot_b):
        with self.driver.session() as session:
            new_services = session.run("""
                MATCH (s:Service)
                WHERE s.snapshot = $snapshot_b
                AND NOT EXISTS {
                    MATCH (s2:Service {name: s.name})
                    WHERE s2.snapshot = $snapshot_a
                }
                RETURN s.name AS name, s.layer AS layer
            """, snapshot_a=snapshot_a, snapshot_b=snapshot_b)

            removed_services = session.run("""
                MATCH (s:Service)
                WHERE s.snapshot = $snapshot_a
                AND NOT EXISTS {
                    MATCH (s2:Service {name: s.name})
                    WHERE s2.snapshot = $snapshot_b
                }
                RETURN s.name AS name, s.layer AS layer
            """, snapshot_a=snapshot_a, snapshot_b=snapshot_b)

            new_edges = session.run("""
                MATCH (s:Service)-[r:CALLS]->(t:Service)
                WHERE r.snapshot = $snapshot_b
                AND NOT EXISTS {
                    MATCH (s2:Service {name: s.name})-[r2:CALLS]->(t2:Service {name: t.name})
                    WHERE r2.snapshot = $snapshot_a
                }
                RETURN s.name AS source, t.name AS target
            """, snapshot_a=snapshot_a, snapshot_b=snapshot_b)

            removed_edges = session.run("""
                MATCH (s:Service)-[r:CALLS]->(t:Service)
                WHERE r.snapshot = $snapshot_a
                AND NOT EXISTS {
                    MATCH (s2:Service {name: s.name})-[r2:CALLS]->(t2:Service {name: t.name})
                    WHERE r2.snapshot = $snapshot_b
                }
                RETURN s.name AS source, t.name AS target
            """, snapshot_a=snapshot_a, snapshot_b=snapshot_b)

            changed_edges = session.run("""
                MATCH (s1:Service {snapshot: $snapshot_a})-[r1:CALLS]->(t1:Service {snapshot: $snapshot_a})
                MATCH (s2:Service {snapshot: $snapshot_b, name: s1.name})-[r2:CALLS]->(t2:Service {snapshot: $snapshot_b, name: t1.name})
                WHERE r1.call_count <> r2.call_count
                   OR r1.error_count <> r2.error_count
                RETURN
                    s1.name AS source, t1.name AS target,
                    r1.call_count AS old_count, r2.call_count AS new_count,
                    r1.error_count AS old_errors, r2.error_count AS new_errors
            """, snapshot_a=snapshot_a, snapshot_b=snapshot_b)

            return {
                "new_services": [{"name": r["name"], "layer": r["layer"]}
                                 for r in new_services],
                "removed_services": [{"name": r["name"], "layer": r["layer"]}
                                     for r in removed_services],
                "new_edges": [{"source": r["source"], "target": r["target"]}
                              for r in new_edges],
                "removed_edges": [{"source": r["source"], "target": r["target"]}
                                  for r in removed_edges],
                "changed_edges": [{
                    "source": r["source"], "target": r["target"],
                    "old_count": r["old_count"], "new_count": r["new_count"],
                    "old_errors": r["old_errors"], "new_errors": r["new_errors"],
                } for r in changed_edges],
            }

    def get_snapshots(self, limit=10):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Service)
                WHERE s.snapshot IS NOT NULL
                WITH DISTINCT s.snapshot AS snapshot_id,
                     min(s.last_seen) AS timestamp
                RETURN snapshot_id, timestamp
                ORDER BY timestamp DESC
                LIMIT $limit
            """, limit=limit)

            return [{"snapshot_id": r["snapshot_id"],
                     "timestamp": str(r["timestamp"])}
                    for r in result]

    def get_service_layers(self):
        with self.driver.session() as session:
            result = session.run("""
                MATCH (s:Service)
                RETURN DISTINCT s.layer AS layer, count(s) AS count
                ORDER BY count DESC
            """)
            return [{"layer": r["layer"], "count": r["count"]}
                    for r in result]

    def get_request_paths(self, source_service, target_service=None,
                           max_paths=5, max_depth=6):
        with self.driver.session() as session:
            if target_service:
                result = session.run("""
                    MATCH (start:Service {name: $source})
                    MATCH (end:Service {name: $target})
                    MATCH path = (start)-[r:CALLS*1..$depth]->(end)
                    WHERE ALL(rel IN relationships(path) WHERE rel.call_count > 0)
                    WITH path,
                         [rel IN relationships(path) | rel.call_count] AS call_counts,
                         [rel IN relationships(path) | rel.error_count] AS error_counts,
                         [rel IN relationships(path) | rel.total_latency] AS latencies
                    WITH path,
                         reduce(total = 0, c IN call_counts | total + c) AS total_calls,
                         reduce(total = 0, e IN error_counts | total + e) AS total_errors,
                         reduce(total = 0, l IN latencies | total + l) AS total_latency
                    ORDER BY total_calls DESC
                    LIMIT $max_paths
                    RETURN
                        [node IN nodes(path) | node.name] AS nodes,
                        [rel IN relationships(path) | {
                            source: startNode(rel).name,
                            target: endNode(rel).name,
                            call_count: rel.call_count,
                            error_count: rel.error_count,
                            avg_latency: rel.total_latency / rel.call_count,
                            call_type: COALESCE(rel.call_type, 'sync')
                        }] AS edges,
                        total_calls,
                        total_errors,
                        total_latency / total_calls AS avg_latency
                """, source=source_service, target=target_service,
                    depth=max_depth, max_paths=max_paths)
            else:
                result = session.run("""
                    MATCH (start:Service {name: $source})
                    MATCH path = (start)-[r:CALLS*1..$depth]->(end:Service)
                    WHERE ALL(rel IN relationships(path) WHERE rel.call_count > 0)
                      AND NOT (end)-[:CALLS]->()
                    WITH path, start, end,
                         [rel IN relationships(path) | rel.call_count] AS call_counts,
                         [rel IN relationships(path) | rel.error_count] AS error_counts,
                         [rel IN relationships(path) | rel.total_latency] AS latencies
                    WITH path, start, end,
                         reduce(total = 0, c IN call_counts | total + c) AS total_calls,
                         reduce(total = 0, e IN error_counts | total + e) AS total_errors,
                         reduce(total = 0, l IN latencies | total + l) AS total_latency
                    ORDER BY total_calls DESC
                    LIMIT $max_paths
                    RETURN
                        [node IN nodes(path) | node.name] AS nodes,
                        [rel IN relationships(path) | {
                            source: startNode(rel).name,
                            target: endNode(rel).name,
                            call_count: rel.call_count,
                            error_count: rel.error_count,
                            avg_latency: rel.total_latency / rel.call_count,
                            call_type: COALESCE(rel.call_type, 'sync')
                        }] AS edges,
                        total_calls,
                        total_errors,
                        total_latency / total_calls AS avg_latency
                """, source=source_service, depth=max_depth, max_paths=max_paths)

            return [{
                "nodes": record["nodes"],
                "edges": record["edges"],
                "total_calls": record["total_calls"],
                "total_errors": record["total_errors"],
                "avg_latency": record["avg_latency"]
            } for record in result]

    def clear_all(self):
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
