package com.servicetopology.neo4j;

import com.servicetopology.model.ServiceNode;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ServiceNodeRepository extends Neo4jRepository<ServiceNode, String> {

    Optional<ServiceNode> findByNameAndNamespace(String name, String namespace);

    List<ServiceNode> findByNamespace(String namespace);

    List<ServiceNode> findByType(String type);

    @Query("MATCH (s:Service) RETURN s")
    List<ServiceNode> findAllServices();

    @Query("MATCH (s:Service {namespace: $namespace}) RETURN s")
    List<ServiceNode> findAllByNamespace(@Param("namespace") String namespace);

    @Query("MATCH (source:Service)-[c:CALLS]->(target:Service) " +
           "WHERE source.id = $serviceId " +
           "RETURN source, collect(c), collect(target)")
    Optional<ServiceNode> findServiceWithOutgoingCalls(@Param("serviceId") String serviceId);

    @Query("MATCH (source:Service)-[c:CALLS]->(target:Service) " +
           "WHERE target.id = $serviceId " +
           "RETURN target, collect(c), collect(source)")
    Optional<ServiceNode> findServiceWithIncomingCalls(@Param("serviceId") String serviceId);

    @Query("MATCH (s:Service) DETACH DELETE s")
    void deleteAllServices();

    @Query("MATCH (source:Service {id: $sourceId}) " +
           "MATCH (target:Service {id: $targetId}) " +
           "MERGE (source)-[c:CALLS {id: $callId}]->(target) " +
           "SET c.callType = $callType, " +
           "    c.protocol = $protocol, " +
           "    c.isAsync = $isAsync, " +
           "    c.messageQueue = $messageQueue, " +
           "    c.httpMethod = $httpMethod, " +
           "    c.path = $path, " +
           "    c.callCount = coalesce(c.callCount, 0) + $callCount, " +
           "    c.errorCount = coalesce(c.errorCount, 0) + $errorCount, " +
           "    c.avgLatencyMs = $avgLatencyMs, " +
           "    c.firstSeen = CASE WHEN c.firstSeen IS NULL THEN $firstSeen ELSE c.firstSeen END, " +
           "    c.lastSeen = $lastSeen " +
           "RETURN c")
    void mergeServiceCall(
        @Param("sourceId") String sourceId,
        @Param("targetId") String targetId,
        @Param("callId") String callId,
        @Param("callType") String callType,
        @Param("protocol") String protocol,
        @Param("isAsync") boolean isAsync,
        @Param("messageQueue") String messageQueue,
        @Param("httpMethod") String httpMethod,
        @Param("path") String path,
        @Param("callCount") long callCount,
        @Param("errorCount") long errorCount,
        @Param("avgLatencyMs") double avgLatencyMs,
        @Param("firstSeen") String firstSeen,
        @Param("lastSeen") String lastSeen
    );

    @Query("MATCH (s:Service {name: $name, namespace: $namespace}) RETURN s")
    Optional<ServiceNode> findByServiceName(@Param("name") String name, @Param("namespace") String namespace);

    @Query("MATCH (source:Service {id: $sourceId}) " +
           "MATCH (target:Service {id: $targetId}) " +
           "MERGE (source)-[c:CALLS {id: $callId}]->(target) " +
           "WITH c, datetime($lastSeen) as currentTime, $windowSeconds as windowSecs " +
           "WHERE duration.between(CASE WHEN c.lastSeen IS NOT NULL THEN datetime(c.lastSeen) ELSE datetime($lastSeen) END, currentTime).seconds <= windowSecs " +
           "SET c.callType = $callType, " +
           "    c.protocol = $protocol, " +
           "    c.isAsync = $isAsync, " +
           "    c.messageQueue = $messageQueue, " +
           "    c.httpMethod = $httpMethod, " +
           "    c.path = $path, " +
           "    c.callCount = coalesce(c.callCount, 0) + $callCount, " +
           "    c.errorCount = coalesce(c.errorCount, 0) + $errorCount, " +
           "    c.successCount = coalesce(c.successCount, 0) + $successCount, " +
           "    c.avgLatencyMs = CASE WHEN c.avgLatencyMs IS NULL THEN $avgLatencyMs ELSE (c.avgLatencyMs * 0.9 + $avgLatencyMs * 0.1) END, " +
           "    c.windowSeconds = $windowSeconds, " +
           "    c.qps = CASE WHEN c.callCount > 0 THEN round(c.callCount / $windowSeconds * 100) / 100 ELSE $qps END, " +
           "    c.peakQps = CASE WHEN c.peakQps IS NULL OR $qps > c.peakQps THEN $qps ELSE c.peakQps END, " +
           "    c.firstSeen = CASE WHEN c.firstSeen IS NULL THEN $firstSeen ELSE c.firstSeen END, " +
           "    c.lastSeen = $lastSeen, " +
           "    c.traceId = CASE WHEN c.traceId IS NULL THEN $traceId ELSE c.traceId END, " +
           "    c.spanId = CASE WHEN c.spanId IS NULL THEN $spanId ELSE c.spanId END, " +
           "    c.parentSpanId = CASE WHEN c.parentSpanId IS NULL THEN $parentSpanId ELSE c.parentSpanId END, " +
           "    c.correlationId = CASE WHEN c.correlationId IS NULL THEN $correlationId ELSE c.correlationId END, " +
           "    c.consumerGroup = CASE WHEN c.consumerGroup IS NULL THEN $consumerGroup ELSE c.consumerGroup END, " +
           "    c.messageTopic = CASE WHEN c.messageTopic IS NULL THEN $messageTopic ELSE c.messageTopic END " +
           "RETURN c")
    void mergeServiceCallWithTrace(
        @Param("sourceId") String sourceId,
        @Param("targetId") String targetId,
        @Param("callId") String callId,
        @Param("callType") String callType,
        @Param("protocol") String protocol,
        @Param("isAsync") boolean isAsync,
        @Param("messageQueue") String messageQueue,
        @Param("httpMethod") String httpMethod,
        @Param("path") String path,
        @Param("callCount") long callCount,
        @Param("errorCount") long errorCount,
        @Param("successCount") long successCount,
        @Param("avgLatencyMs") double avgLatencyMs,
        @Param("firstSeen") String firstSeen,
        @Param("lastSeen") String lastSeen,
        @Param("traceId") String traceId,
        @Param("spanId") String spanId,
        @Param("parentSpanId") String parentSpanId,
        @Param("correlationId") String correlationId,
        @Param("consumerGroup") String consumerGroup,
        @Param("messageTopic") String messageTopic,
        @Param("qps") double qps,
        @Param("windowSeconds") long windowSeconds
    );

    @Query("MATCH (s:Service)-[:MEMBER_OF]->(g:ServiceGroup) " +
           "WHERE s.id = $serviceId " +
           "RETURN g")
    Optional<com.servicetopology.model.ServiceGroup> findServiceGroup(@Param("serviceId") String serviceId);

    @Query("MATCH (cg:ConsumerGroup)<-[:PRODUCES_TO]-(s:Service) " +
           "WHERE s.id = $serviceId " +
           "RETURN DISTINCT cg")
    List<com.servicetopology.model.ConsumerGroup> findProducedConsumerGroups(@Param("serviceId") String serviceId);

    @Query("MATCH (cg:ConsumerGroup)-[:HAS_CONSUMER]->(s:Service) " +
           "WHERE s.id = $serviceId " +
           "RETURN DISTINCT cg")
    List<com.servicetopology.model.ConsumerGroup> findConsumedConsumerGroups(@Param("serviceId") String serviceId);
}
