package com.servicetopology.neo4j;

import com.servicetopology.model.ConsumerGroup;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ConsumerGroupRepository extends Neo4jRepository<ConsumerGroup, String> {

    Optional<ConsumerGroup> findByNameAndNamespace(String name, String namespace);

    List<ConsumerGroup> findByNamespace(String namespace);

    List<ConsumerGroup> findByMessageQueue(String messageQueue);

    @Query("MATCH (cg:ConsumerGroup {namespace: $namespace}) RETURN cg")
    List<ConsumerGroup> findAllByNamespace(@Param("namespace") String namespace);

    @Query("MATCH (cg:ConsumerGroup)<-[:PRODUCES_TO]-(s:Service) " +
           "WHERE s.id = $serviceId " +
           "RETURN cg")
    List<ConsumerGroup> findProducerGroupsByService(@Param("serviceId") String serviceId);

    @Query("MATCH (cg:ConsumerGroup)-[:HAS_CONSUMER]->(s:Service) " +
           "WHERE s.id = $serviceId " +
           "RETURN cg")
    List<ConsumerGroup> findConsumerGroupsByService(@Param("serviceId") String serviceId);

    @Query("MATCH (producer:Service {id: $producerId}) " +
           "MATCH (cg:ConsumerGroup {id: $groupId}) " +
           "MATCH (consumer:Service {id: $consumerId}) " +
           "MERGE (producer)-[:PRODUCES_TO]->(cg) " +
           "MERGE (cg)-[:HAS_CONSUMER]->(consumer)")
    void linkProducerConsumerGroup(
        @Param("producerId") String producerId,
        @Param("groupId") String groupId,
        @Param("consumerId") String consumerId
    );

    @Query("MATCH (cg:ConsumerGroup {id: $groupId}) " +
           "SET cg.consumerCount = $count, " +
           "    cg.lastUpdated = $lastUpdated")
    void updateConsumerCount(
        @Param("groupId") String groupId,
        @Param("count") int count,
        @Param("lastUpdated") String lastUpdated
    );
}
