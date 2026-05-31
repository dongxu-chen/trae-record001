package com.servicetopology.neo4j;

import com.servicetopology.model.ServiceGroup;
import org.springframework.data.neo4j.repository.Neo4jRepository;
import org.springframework.data.neo4j.repository.query.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface ServiceGroupRepository extends Neo4jRepository<ServiceGroup, String> {

    Optional<ServiceGroup> findByNameAndNamespace(String name, String namespace);

    List<ServiceGroup> findByNamespace(String namespace);

    List<ServiceGroup> findByGroupType(String groupType);

    @Query("MATCH (sg:ServiceGroup) WHERE sg.parent IS NULL RETURN sg")
    List<ServiceGroup> findRootGroups();

    @Query("MATCH (sg:ServiceGroup {namespace: $namespace}) " +
           "WHERE sg.parent IS NULL " +
           "RETURN sg")
    List<ServiceGroup> findRootGroupsByNamespace(@Param("namespace") String namespace);

    @Query("MATCH (parent:ServiceGroup {id: $parentId}) " +
           "MATCH (child:ServiceGroup {id: $childId}) " +
           "MERGE (parent)-[:CONTAINS_GROUP]->(child) " +
           "MERGE (child)-[:PARENT_GROUP]->(parent)")
    void linkParentGroup(
        @Param("parentId") String parentId,
        @Param("childId") String childId
    );

    @Query("MATCH (sg:ServiceGroup {id: $groupId}) " +
           "MATCH (s:Service {id: $serviceId}) " +
           "MERGE (sg)-[:CONTAINS]->(s) " +
           "MERGE (s)-[:MEMBER_OF]->(sg)")
    void addServiceToGroup(
        @Param("groupId") String groupId,
        @Param("serviceId") String serviceId
    );

    @Query("MATCH (sg:ServiceGroup {id: $groupId}) " +
           "SET sg.collapsed = $collapsed")
    void updateGroupCollapsed(
        @Param("groupId") String groupId,
        @Param("collapsed") boolean collapsed
    );

    @Query("MATCH (sg:ServiceGroup {id: $groupId})-[:CONTAINS]->(s:Service) " +
           "RETURN s")
    List<com.servicetopology.model.ServiceNode> findGroupServices(@Param("groupId") String groupId);

    @Query("MATCH (sg:ServiceGroup {id: $groupId})-[:CONTAINS_GROUP]->(child:ServiceGroup) " +
           "RETURN child")
    List<ServiceGroup> findSubgroups(@Param("groupId") String groupId);

    @Query("MATCH (sg:ServiceGroup {id: $groupId}) " +
           "OPTIONAL MATCH (sg)-[:CONTAINS]->(s:Service) " +
           "WITH sg, COUNT(s) AS serviceCount " +
           "OPTIONAL MATCH (sg)-[:CONTAINS_GROUP]->(child:ServiceGroup) " +
           "RETURN sg, serviceCount, COUNT(child) AS subgroupCount")
    org.neo4j.driver.Record getGroupStats(@Param("groupId") String groupId);
}
