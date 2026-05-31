package com.servicetopology.neo4j;

import com.servicetopology.model.TraceContext;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface TraceContextRepository extends Neo4jRepository<TraceContext, String> {

    List<TraceContext> findByStatus(String status);

    @Query("MATCH (t:Trace) ORDER BY t.startTime DESC LIMIT $limit RETURN t")
    List<TraceContext> findRecentTraces(@Param("limit") int limit);

    @Query("MATCH (t:Trace {traceId: $traceId}) " +
           "MATCH (s:Service)-[:PART_OF_TRACE]->(t) " +
           "RETURN s")
    List<com.servicetopology.model.ServiceNode> findTraceServices(@Param("traceId") String traceId);

    @Query("MATCH (t:Trace {traceId: $traceId}) " +
           "MATCH (source:Service)-[c:CALLS]->(target:Service) " +
           "WHERE c.traceId = $traceId " +
           "RETURN source, c, target")
    org.neo4j.driver.Result getTraceCalls(@Param("traceId") String traceId);

    @Query("MATCH (t:Trace {traceId: $traceId}) " +
           "MATCH (s:Service {id: $serviceId}) " +
           "MERGE (s)-[:PART_OF_TRACE]->(t)")
    void linkServiceToTrace(
        @Param("traceId") String traceId,
        @Param("serviceId") String serviceId
    );

    @Query("MATCH (source:Service)-[c:CALLS]->(target:Service) " +
           "WHERE c.traceId = $traceId " +
           "MATCH (t:Trace {traceId: $traceId}) " +
           "RETURN COUNT(c) AS callCount, " +
           "SUM(c.callCount) AS totalCalls, " +
           "SUM(c.errorCount) AS totalErrors, " +
           "AVG(c.avgLatencyMs) AS avgLatency")
    org.neo4j.driver.Record getTraceStats(@Param("traceId") String traceId);

    @Query("MATCH (c:CALLS) " +
           "WHERE c.traceId = $traceId " +
           "RETURN DISTINCT c.correlationId AS correlationId " +
           "LIMIT 1")
    String findCorrelationIdByTrace(@Param("traceId") String traceId);
}
